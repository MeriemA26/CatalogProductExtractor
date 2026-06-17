# extraction/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib import messages
from .forms import CatalogueUploadForm
from .pipeline import process_catalogue_image
from .models import CatalogueUpload, Product
import os
import json
import base64
from datetime import datetime

def upload_catalogue(request):
    """Upload une image et affiche les résultats"""
    products_data = None
    uploaded_image_base64 = None
    metadata = None
    
    if request.method == 'POST':
        form = CatalogueUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Récupérer les métadonnées
            enseigne = form.cleaned_data['enseigne']
            enseigne_autre = form.cleaned_data.get('enseigne_autre', '')
            if enseigne == 'autre':
                enseigne = enseigne_autre
            
            date_debut = form.cleaned_data['date_debut']
            date_fin = form.cleaned_data['date_fin']
            
            # CRÉER LE CATALOGUE DANS LA BASE
            catalogue = CatalogueUpload.objects.create(
                enseigne=enseigne,
                enseigne_autre=enseigne_autre,
                date_debut=date_debut,
                date_fin=date_fin,
            )
            
            metadata = {
                'id': catalogue.id,
                'enseigne': enseigne,
                'date_debut': date_debut.strftime('%d/%m/%Y'),
                'date_fin': date_fin.strftime('%d/%m/%Y'),
                'traite_le': datetime.now().strftime('%d/%m/%Y %H:%M'),
            }
            
            # === SAUVEGARDER catalogue_id DANS LA SESSION ===
            request.session['catalogue_id'] = catalogue.id  # ← AJOUTE CETTE LIGNE
            request.session['catalogue_metadata'] = metadata
            
            image_file = request.FILES['image']
            
            # Lire l'image et la convertir en base64
            image_data = image_file.read()
            uploaded_image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Sauvegarder l'image
            image_path = f'catalogues/{image_file.name}'
            default_storage.save(image_path, ContentFile(image_data))
            catalogue.image = image_path
            catalogue.save()
            
            # Traitement
            full_path = default_storage.path(image_path)
            products_data = process_catalogue_image(full_path, debug=False)
            
            # Ajouter un ID
            for idx, product in enumerate(products_data):
                product['id'] = idx
                product['selected'] = True
            
            # Stocker dans la session
            request.session['products_data'] = products_data
            request.session['uploaded_image_base64'] = uploaded_image_base64
            
            messages.success(request, f"✅ {len(products_data)} produit(s) détecté(s) pour {enseigne}")
    else:
        form = CatalogueUploadForm()
        products_data = request.session.get('products_data', None)
        uploaded_image_base64 = request.session.get('uploaded_image_base64', None)
        metadata = request.session.get('catalogue_metadata', None)
    
    return render(request, 'extraction/upload.html', {
        'form': form,
        'products': products_data,
        'uploaded_image_base64': uploaded_image_base64,
        'metadata': metadata,
    })

def edit_product(request, product_id):
    """Page d'édition d'un produit"""
    products_data = request.session.get('products_data', [])
    
    if not products_data:
        messages.error(request, "❌ Aucun produit à modifier.")
        return redirect('extraction:upload_catalogue')
    
    # Trouver le produit correspondant
    product = None
    product_index = None
    for idx, p in enumerate(products_data):
        if str(p.get('id')) == str(product_id):
            product = p
            product_index = idx
            break
    
    if not product:
        messages.error(request, "❌ Produit non trouvé.")
        return redirect('extraction:upload_catalogue')
    
    if request.method == 'POST':
        # Mettre à jour les champs
        product['nom_fr'] = request.POST.get('nom_fr', '')
        product['nom_ar'] = request.POST.get('nom_ar', '')
        product['marque'] = request.POST.get('marque', '')
        product['prix'] = request.POST.get('prix', '')
        product['prix_avant'] = request.POST.get('prix_avant', '')
        product['description'] = request.POST.get('description', '')
        
        # Recalculer la remise
        if product['prix'] and product['prix_avant']:
            try:
                prix = float(product['prix'])
                prix_avant = float(product['prix_avant'])
                if prix_avant > 0:
                    pct = round((1 - prix / prix_avant) * 100)
                    product['remise'] = f"{pct}%"
            except:
                pass
        
        # Sauvegarder dans la session
        products_data[product_index] = product
        request.session['products_data'] = products_data
        
        messages.success(request, "✅ Produit modifié avec succès !")
        return redirect('extraction:upload_catalogue')
    
    return render(request, 'extraction/edit_product.html', {
        'product': product,
        'product_id': product_id,
    })


def delete_product(request, product_id):
    """Supprime un produit de la session"""
    products_data = request.session.get('products_data', [])
    
    if not products_data:
        return redirect('extraction:upload_catalogue')
    
    # Filtrer pour enlever le produit
    products_data = [p for p in products_data if str(p.get('id')) != str(product_id)]
    
    # Ré-indexer les IDs
    for idx, product in enumerate(products_data):
        product['id'] = idx
    
    # Sauvegarder dans la session
    request.session['products_data'] = products_data
    
    messages.success(request, "🗑️ Produit supprimé.")
    return redirect('extraction:upload_catalogue')


def delete_selected_products(request):
    """Supprime les produits sélectionnés"""
    products_data = request.session.get('products_data', [])
    
    if not products_data:
        return redirect('extraction:upload_catalogue')
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_products')
        
        if not selected_ids:
            messages.warning(request, "⚠️ Aucun produit sélectionné.")
            return redirect('extraction:upload_catalogue')
        
        # Filtrer pour garder seulement les non sélectionnés
        products_data = [p for p in products_data if str(p.get('id')) not in selected_ids]
        
        # Ré-indexer les IDs
        for idx, product in enumerate(products_data):
            product['id'] = idx
        
        # Sauvegarder dans la session
        request.session['products_data'] = products_data
        
        messages.success(request, f"🗑️ {len(selected_ids)} produit(s) supprimé(s).")
    
    return redirect('extraction:upload_catalogue')


def delete_all_products(request):
    """Supprime TOUS les produits de la session"""
    request.session.pop('products_data', None)
    messages.success(request, "🗑️ Tous les produits ont été supprimés.")
    return redirect('extraction:upload_catalogue')


def save_selected_products(request):
    """Sauvegarde les produits sélectionnés en SQL"""
    products_data = request.session.get('products_data', [])
    catalogue_id = request.session.get('catalogue_id')  # ← Récupère de la session
    
    if not products_data:
        messages.warning(request, "⚠️ Aucun produit à sauvegarder.")
        return redirect('extraction:upload_catalogue')
    
    if not catalogue_id:
        messages.error(request, "❌ Aucun catalogue trouvé. Veuillez réimporter l'image.")
        return redirect('extraction:upload_catalogue')
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_products')
        
        if not selected_ids:
            messages.warning(request, "⚠️ Aucun produit sélectionné.")
            return redirect('extraction:upload_catalogue')
        
        try:
            catalogue = CatalogueUpload.objects.get(id=catalogue_id)
        except CatalogueUpload.DoesNotExist:
            messages.error(request, "❌ Catalogue non trouvé.")
            return redirect('extraction:upload_catalogue')
        
        saved_count = 0
        existing_count = 0
        
        for p in products_data:
            if str(p.get('id')) in selected_ids:
                try:
                    existing = Product.objects.filter(
                        catalogue=catalogue,
                        nom_fr=p.get('nom_fr', ''),
                        prix=float(p['prix']) if p.get('prix') else None
                    ).first()
                    
                    if not existing:
                        Product.objects.create(
                            catalogue=catalogue,
                            nom_fr=p.get('nom_fr', ''),
                            nom_ar=p.get('nom_ar', ''),
                            marque=p.get('marque', ''),
                            prix=float(p['prix']) if p.get('prix') else None,
                            prix_avant=float(p['prix_avant']) if p.get('prix_avant') else None,
                            description=p.get('description', ''),
                            remise=p.get('remise', ''),
                        )
                        saved_count += 1
                    else:
                        existing_count += 1
                except Exception as e:
                    print(f"Erreur sauvegarde: {e}")
        
        if saved_count == 0 and existing_count > 0:
            messages.warning(request, f"⚠️ Les {existing_count} produits sont déjà en base.")
        elif saved_count > 0:
            messages.success(request, f"✅ {saved_count} nouveau(x) produit(s) sauvegardé(s).")
        else:
            messages.warning(request, "⚠️ Aucun produit à sauvegarder.")
        
        return redirect('extraction:upload_catalogue')
    
    return redirect('extraction:upload_catalogue')

def save_all_products(request):
    """Sauvegarde TOUS les produits en SQL"""
    products_data = request.session.get('products_data', [])
    catalogue_id = request.session.get('catalogue_id')
    
    if not products_data:
        messages.warning(request, "⚠️ Aucun produit à sauvegarder.")
        return redirect('extraction:upload_catalogue')
    
    if not catalogue_id:
        messages.error(request, "❌ Aucun catalogue trouvé.")
        return redirect('extraction:upload_catalogue')
    
    try:
        catalogue = CatalogueUpload.objects.get(id=catalogue_id)
    except CatalogueUpload.DoesNotExist:
        messages.error(request, "❌ Catalogue non trouvé.")
        return redirect('extraction:upload_catalogue')
    
    saved_count = 0
    existing_count = 0
    
    for p in products_data:
        try:
            existing = Product.objects.filter(
                catalogue=catalogue,
                nom_fr=p.get('nom_fr', ''),
                prix=float(p['prix']) if p.get('prix') else None
            ).first()
            
            if not existing:
                Product.objects.create(
                    catalogue=catalogue,
                    nom_fr=p.get('nom_fr', ''),
                    nom_ar=p.get('nom_ar', ''),
                    marque=p.get('marque', ''),
                    prix=float(p['prix']) if p.get('prix') else None,
                    prix_avant=float(p['prix_avant']) if p.get('prix_avant') else None,
                    description=p.get('description', ''),
                    remise=p.get('remise', ''),
                )
                saved_count += 1
            else:
                existing_count += 1
        except Exception as e:
            print(f"Erreur sauvegarde: {e}")
    
    # Sauvegarde JSON (backup)
    save_path = os.path.join(settings.MEDIA_ROOT, 'extracted_products.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump({
            'catalogue_id': catalogue_id,
            'products': products_data
        }, f, ensure_ascii=False, indent=2)
    
    # Messages
    if saved_count > 0:
        messages.success(request, f"✅ {saved_count} nouveau(x) produit(s) sauvegardé(s).")
    elif existing_count > 0:
        messages.warning(request, f"⚠️ {existing_count} produits étaient déjà en base.")
    else:
        messages.info(request, "ℹ️ Aucun produit à sauvegarder.")
    
    # ⭐ REDIRIGER VERS LA LISTE DES PRODUITS EN BASE
    return redirect('extraction:product_list')


def product_list(request):
    """Liste des produits groupés par catalogue unique (fusion des doublons)"""
    from django.db.models import Count, Sum
    
    # Récupérer tous les catalogues
    all_catalogues = CatalogueUpload.objects.all().order_by('-date_upload')
    
    # Grouper les catalogues par (enseigne, date_debut, date_fin)
    grouped_catalogues = {}
    
    for cat in all_catalogues:
        # Créer une clé unique pour chaque groupe
        key = f"{cat.enseigne}_{cat.date_debut}_{cat.date_fin}"
        
        if key not in grouped_catalogues:
            grouped_catalogues[key] = {
                'enseigne': cat.get_enseigne_display_name(),
                'date_debut': cat.date_debut,
                'date_fin': cat.date_fin,
                'catalogues_ids': [],
                'total_products': 0,
            }
        
        grouped_catalogues[key]['catalogues_ids'].append(cat.id)
        grouped_catalogues[key]['total_products'] += cat.products.count()
    
    # Récupérer tous les produits de ces catalogues
    all_ids = []
    for group in grouped_catalogues.values():
        all_ids.extend(group['catalogues_ids'])
    
    products = Product.objects.filter(catalogue__id__in=all_ids).select_related('catalogue').order_by('-created_at')
    
    # Compter les catalogues uniques
    total_catalogues = len(grouped_catalogues)
    total_products = products.count()
    
    context = {
        'grouped_catalogues': grouped_catalogues.values(),
        'products': products,
        'total_products': total_products,
        'total_catalogues': total_catalogues,
    }
    return render(request, 'extraction/product_list.html', context)


def add_product(request):
    """Ajouter un produit manuellement"""
    if request.method == 'POST':
        new_product = {
            'id': None,
            'nom_fr': request.POST.get('nom_fr', ''),
            'nom_ar': request.POST.get('nom_ar', ''),
            'marque': request.POST.get('marque', ''),
            'prix': request.POST.get('prix', ''),
            'prix_avant': request.POST.get('prix_avant', ''),
            'description': request.POST.get('description', ''),
            'remise': '',
            'product_image_b64': None,
            'fields': [],
        }
        
        # Gérer l'image uploadée
        if request.FILES.get('product_image'):
            image_file = request.FILES['product_image']
            image_data = image_file.read()
            new_product['product_image_b64'] = base64.b64encode(image_data).decode('utf-8')
        
        # Calculer la remise
        if new_product['prix'] and new_product['prix_avant']:
            try:
                prix = float(new_product['prix'])
                prix_avant = float(new_product['prix_avant'])
                if prix_avant > 0:
                    pct = round((1 - prix / prix_avant) * 100)
                    new_product['remise'] = f"{pct}%"
            except:
                pass
        
        # Récupérer les produits existants
        products_data = request.session.get('products_data', [])
        
        # Ajouter le nouveau produit avec un ID
        new_id = len(products_data)
        new_product['id'] = new_id
        
        products_data.append(new_product)
        
        # Sauvegarder dans la session
        request.session['products_data'] = products_data
        
        messages.success(request, "✅ Produit ajouté avec succès !")
        return redirect('extraction:upload_catalogue')
    
    return render(request, 'extraction/add_product.html')


def catalogue_detail(request, catalogue_id):
    """Voir les détails d'un catalogue et ses produits"""
    catalogue = get_object_or_404(CatalogueUpload, id=catalogue_id)
    products = catalogue.products.all().order_by('id')
    
    context = {
        'catalogue': catalogue,
        'products': products,
        'total': products.count(),
    }
    return render(request, 'extraction/catalogue_detail.html', context)