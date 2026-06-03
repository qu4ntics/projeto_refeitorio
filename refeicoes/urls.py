from django.urls import path
from . import views

app_name = 'refeicoes'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('lista-presenca/', views.lista_presenca, name='lista-presenca'),
]