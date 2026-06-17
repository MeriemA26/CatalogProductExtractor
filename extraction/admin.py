# extraction/admin.py
from django.contrib import admin
from .models import CatalogueUpload, Product

@admin.register(CatalogueUpload)
class CatalogueUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_enseigne_display_name', 'date_debut', 'date_fin', 'date_upload', 'products_count')
    list_filter = ('enseigne', 'date_debut', 'date_fin')
    search_fields = ('enseigne', 'enseigne_autre')
    date_hierarchy = 'date_upload'
    
    def get_enseigne_display_name(self, obj):
        return obj.get_enseigne_display_name()
    get_enseigne_display_name.short_description = 'Enseigne'
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Nb produits'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom_fr', 'nom_ar', 'marque', 'prix', 'created_at', 'catalogue')
    list_filter = ('catalogue', 'created_at')
    search_fields = ('nom_fr', 'nom_ar', 'marque', 'description')
    date_hierarchy = 'created_at'