from django.urls import path

from . import views

app_name = 'refeicoes'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('cardapio/', views.cardapio_semana, name='cardapio_semana'),
    path('criar/', views.criar_refeicao, name='criar'),
    path('nutricionista/', views.nutricionista_lista, name='nutricionista_lista'),
    path('nutricionista/nova/', views.criar_refeicao, name='nutricionista_nova'),
    path('nutricionista/<uuid:pk>/deletar/', views.nutricionista_deletar, name='nutricionista_deletar'),
]
