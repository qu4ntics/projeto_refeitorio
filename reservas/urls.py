from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    path('criar/<uuid:refeicao_id>/', views.criar_reserva, name='criar_reserva'),
    path('cancelar/<uuid:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('lista-presenca/', views.lista_presenca, name='lista_presenca'),
]