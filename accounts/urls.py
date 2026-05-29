from django.urls import path
from .views import cadastro_view

urlpatterns = [
    path('cadastro/', cadastro_view, name='cadastro')
    
]