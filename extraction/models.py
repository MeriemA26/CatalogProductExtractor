# extraction/models.py
from django.db import models
from django.utils import timezone

class CatalogueUpload(models.Model):
    """Modèle pour regrouper un upload de catalogue et ses métadonnées"""
    
    ENSEIGNE_CHOICES = [
        ('MG', 'MG'),
        ('Carrefour', 'Carrefour'),
        ('Carrefour Market', 'Carrefour Market'),
        ('Carrefour Express', 'Carrefour Express'),
        ('Aziza', 'Aziza'),
        ('Anouar', 'Anouar'),
        ('Géant', 'Géant'),
        ('Monoprix', 'Monoprix'),
        ('autre', 'Autre'),
    ]
    
    enseigne = models.CharField(max_length=100, choices=ENSEIGNE_CHOICES)
    enseigne_autre = models.CharField(max_length=100, blank=True, null=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    date_upload = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='catalogues/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_enseigne_display()} - {self.date_debut} → {self.date_fin}"
    
    def get_enseigne_display_name(self):
        if self.enseigne == 'autre' and self.enseigne_autre:
            return self.enseigne_autre
        return dict(self.ENSEIGNE_CHOICES).get(self.enseigne, self.enseigne)


class Product(models.Model):
    """Modèle pour les produits liés à un upload"""
    
    # Relation vers l'upload
    catalogue = models.ForeignKey(
        CatalogueUpload, 
        on_delete=models.CASCADE, 
        related_name='products',
        null=True, 
        blank=True
    )
    
    # Champs du produit
    nom_fr = models.CharField(max_length=500, blank=True)
    nom_ar = models.CharField(max_length=500, blank=True)
    marque = models.CharField(max_length=200, blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    prix_avant = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    remise = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom_fr or f"Produit {self.id}"