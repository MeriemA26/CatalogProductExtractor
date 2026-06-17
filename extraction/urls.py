# extraction/urls.py
from django.urls import path
from . import views

app_name = 'extraction'

urlpatterns = [
    path('', views.upload_catalogue, name='upload_catalogue'),
    path('edit/<str:product_id>/', views.edit_product, name='edit_product'),
    path('delete/<str:product_id>/', views.delete_product, name='delete_product'),
    path('delete-all/', views.delete_all_products, name='delete_all_products'),
    path('delete-selected/', views.delete_selected_products, name='delete_selected_products'),
    path('save-all/', views.save_all_products, name='save_all_products'),
    path('save-selected/', views.save_selected_products, name='save_selected_products'),
    path('products/', views.product_list, name='product_list'),
    path('add-product/', views.add_product, name='add_product'),
    path('catalogue/<int:catalogue_id>/', views.catalogue_detail, name='catalogue_detail'),
]