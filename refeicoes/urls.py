from django.urls import path
from . import views

app_name = 'refeicoes'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('nutricionista/', views.nutricionista_lista, name='nutricionista_lista'),
    path('nutricionista/nova/', views.nutricionista_nova, name='nutricionista_nova'),
    path('nutricionista/<int:pk>/deletar/', views.nutricionista_deletar, name='nutricionista_deletar'),
]