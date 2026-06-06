from django.urls import path
from . import views

app_name = 'administrativo'

urlpatterns = [
    path('painel_nutricionista/', views.painel_nutricionista, name='painel_nutricionista'),
    path('painel_refeitorio/', views.painel_refeitorio, name='painel_refeitorio'),
    path('alunos/', views.lista_alunos, name='lista_alunos'),
    path('alunos/<uuid:aluno_id>/desbloquear/', views.desbloquear_aluno, name='desbloquear_aluno'),
    
]