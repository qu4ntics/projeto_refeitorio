from django.urls import path
from . import views

app_name = 'refeicoes'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('cardapio/', views.cardapio_semana, name='cardapio_semana'),
    path('criar/', views.criar_refeicao, name='criar'),
]