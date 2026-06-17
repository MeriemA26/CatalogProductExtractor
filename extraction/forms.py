# extraction/forms.py
from django import forms

class CatalogueUploadForm(forms.Form):
    # Enseigne
    ENSEIGNE_CHOICES = [
        ('', 'Sélectionnez une enseigne...'),
        ('MG', 'MG'),
        ('Carrefour', 'Carrefour'),
        ('Carrefour Market', 'Carrefour Market'),
        ('Carrefour Express', 'Carrefour Express'),
        ('Aziza', 'Aziza'),
        ('Anouar', 'Anouar'),
        ('Géant', 'Géant'),
        ('Monoprix', 'Monoprix'),
        ('autre', 'Autre (à préciser)'),
    ]
    
    enseigne = forms.ChoiceField(  # ← forms.ChoiceField, pas models.ChoiceField
        choices=ENSEIGNE_CHOICES,
        label="Enseigne",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    enseigne_autre = forms.CharField(
        label="Précisez l'enseigne",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom de l\'enseigne...',
        })
    )
    
    date_debut = forms.DateField(
        label="Date début",
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_fin = forms.DateField(
        label="Date fin",
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    image = forms.ImageField(
        label="Image du catalogue",
        help_text="Sélectionnez une image (JPG, PNG)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )