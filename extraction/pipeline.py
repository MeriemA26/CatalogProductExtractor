import os
import re
import cv2
from ultralytics import YOLO
import easyocr
import numpy as np
import torch
from django.core.files.base import ContentFile
import base64

# Chemins
ML_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCT_MODEL_PATH = os.path.join(ML_DIR, 'best_prod.pt')
FIELD_MODEL_PATH = os.path.join(ML_DIR, 'best_details.pt')

# --- Singletons ---
_product_model = None
_field_model = None
_reader_latin = None
_reader_ar = None


def get_product_model():
    global _product_model
    if _product_model is None:
        if os.path.exists(PRODUCT_MODEL_PATH):
            _product_model = YOLO(PRODUCT_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Modèle non trouvé: {PRODUCT_MODEL_PATH}")
    return _product_model


def get_field_model():
    global _field_model
    if _field_model is None:
        if os.path.exists(FIELD_MODEL_PATH):
            _field_model = YOLO(FIELD_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Modèle non trouvé: {FIELD_MODEL_PATH}")
    return _field_model


def get_ocr_readers():
    global _reader_latin, _reader_ar
    if _reader_latin is None:
        use_gpu = torch.cuda.is_available()
        print(f"[INFO] Using GPU for OCR: {use_gpu}")
        _reader_latin = easyocr.Reader(['fr', 'en'], gpu=use_gpu)
    if _reader_ar is None:
        use_gpu = torch.cuda.is_available()
        _reader_ar = easyocr.Reader(['ar'], gpu=use_gpu)
    return _reader_latin, _reader_ar


FIELD_CLASS_MAP = {
    'product_name': 'nom_fr',
    'product_AR': 'nom_ar',
    'brand': 'marque',
    'price': 'prix',
    'price_before': 'prix_avant',
    'description': 'description',
}


def extract_price_final(roi, debug=False):
    """Extraction de prix avec correction tunisienne"""
    reader_latin, _ = get_ocr_readers()
    
    roi_big = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    results = reader_latin.readtext(thresh, paragraph=False, width_ths=0.3, height_ths=0.3)
    
    if not results:
        return ""
    
    results_sorted = sorted(results, key=lambda x: x[0][0][1])
    
    # Récupérer tous les chiffres
    all_digits = ""
    for bbox, text, conf in results_sorted:
        if conf > 0.3:
            text_clean = text.strip().upper()
            if text_clean in ['DT', 'D1', '0T', 'D7', '0I', 'D', 'T', 'DI', 'D.T', 'D,T']:
                continue
            digits = re.sub(r'[^0-9]', '', text_clean)
            all_digits += digits
    
    if not all_digits:
        return ""
    
    # Règle tunisienne: les 3 derniers chiffres sont les millimes
    if len(all_digits) >= 4:
        millimes = all_digits[-3:]
        dinars = all_digits[:-3]
        dinars = str(int(dinars)) if dinars else "0"
        if len(dinars) > 2:
            dinars = dinars[:2]
        return f"{dinars}.{millimes}"
    elif len(all_digits) == 3:
        if int(all_digits) >= 100:
            return f"{all_digits}.000"
        return f"0.{all_digits}"
    elif len(all_digits) == 2:
        return f"0.0{all_digits}"
    elif len(all_digits) == 1:
        return f"{all_digits}.000"
    
    return ""


def image_to_base64(image):
    """Convertit une image OpenCV en base64 pour l'affichage HTML"""
    _, buffer = cv2.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')


def process_catalogue_image(image_path, conf_product=0.25, conf_field=0.25, debug=False):
    """
    Traite une image catalogue et retourne les produits avec leurs images
    pour vérification humaine
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"[INFO] Using device for YOLO: {device}")
    
    product_model = get_product_model()
    field_model = get_field_model()
    reader_latin, reader_ar = get_ocr_readers()

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")

    products = []
    product_results = product_model(image_path, conf=conf_product, verbose=False, device=device)[0]

    for idx, box in enumerate(product_results.boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        # Image du produit en base64
        product_image_b64 = image_to_base64(crop)

        data = {
            'id': idx,
            'bbox': [x1, y1, x2, y2],
            'nom_fr': '',
            'nom_ar': '',
            'marque': '',
            'prix': None,
            'prix_avant': None,
            'remise': '',
            'description': '',
            'product_image_b64': product_image_b64,
            'fields': [],  # Stocker les images des champs pour vérification
        }

        field_results = field_model.predict(crop, conf=conf_field, device=device, verbose=False)[0]
        field_names = field_results.names

        for fbox, fcls in zip(field_results.boxes.xyxy.cpu().numpy(),
                               field_results.boxes.cls.cpu().numpy()):
            fx1, fy1, fx2, fy2 = map(int, fbox)
            class_name = field_names[int(fcls)]
            roi = crop[fy1:fy2, fx1:fx2]
            if roi.size == 0:
                continue

            target = FIELD_CLASS_MAP.get(class_name)
            if target is None:
                continue

            # Extraire le texte ou le prix
            extracted_value = ""
            field_image_b64 = image_to_base64(roi)

            if class_name == 'product_AR':
                ocr_results = reader_ar.readtext(roi)
                text = " ".join(t for _, t, conf in ocr_results if conf > 0.2)
                extracted_value = text
                data[target] = text

            elif class_name in ('price', 'price_before'):
                price_str = extract_price_final(roi, debug=debug)
                extracted_value = price_str
                if price_str:
                    data[target] = float(price_str)

            else:
                ocr_results = reader_latin.readtext(roi)
                text = " ".join(t for _, t, conf in ocr_results if conf > 0.2)
                extracted_value = text
                data[target] = text

            # Stocker les infos du champ pour vérification
            data['fields'].append({
                'class_name': class_name,
                'target': target,
                'extracted_value': extracted_value,
                'image_b64': field_image_b64,
            })

        if data['prix'] and data['prix_avant'] and data['prix_avant'] > 0:
            pct = round((1 - data['prix'] / data['prix_avant']) * 100)
            data['remise'] = f"{pct}%"

        products.append(data)

    return products


def validate_and_correct_product(product_data, corrections):
    """
    Applique les corrections manuelles de l'utilisateur
    corrections: dict avec les champs corrigés
    """
    for field, value in corrections.items():
        if field in product_data:
            if field in ['prix', 'prix_avant']:
                try:
                    product_data[field] = float(value) if value else None
                except:
                    product_data[field] = None
            else:
                product_data[field] = value
    
    # Recalculer la remise si nécessaire
    if product_data['prix'] and product_data['prix_avant'] and product_data['prix_avant'] > 0:
        pct = round((1 - product_data['prix'] / product_data['prix_avant']) * 100)
        product_data['remise'] = f"{pct}%"
    
    return product_data