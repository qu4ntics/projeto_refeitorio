from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    path('criar/<uuid:refeicao_id>/', views.criar_reserva, name='criar_reserva'),
    path('cancelar/<uuid:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('pre-reserva/<uuid:pre_reserva_id>/confirmar/', views.confirmar_pre_reserva_view, name='confirmar_pre_reserva'),
    path('pre-reserva/<uuid:pre_reserva_id>/rejeitar/', views.rejeitar_pre_reserva_view, name='rejeitar_pre_reserva'),
    path('lista-presenca/', views.lista_presenca, name='lista_presenca'),
]