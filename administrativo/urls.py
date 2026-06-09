from django.urls import path
from . import views

app_name = 'administrativo'

urlpatterns = [
    path('painel_nutricionista/', views.painel_nutricionista, name='painel_nutricionista'),
    path('painel_refeitorio/', views.painel_refeitorio, name='painel_refeitorio'),
    path('alunos/', views.alunos, name='alunos'),
    path('alunos/json/', views.lista_alunos, name='lista_alunos'),
    path('alunos/<uuid:aluno_id>/desbloquear/', views.desbloquear_aluno, name='desbloquear_aluno'),
    path('turmas/', views.turmas_lista, name='turmas_lista'),
    path('turmas/nova/', views.turma_criar, name='turma_criar'),
    path('turmas/<uuid:pk>/editar/', views.turma_editar, name='turma_editar'),
    path('turmas/<uuid:pk>/excluir/', views.turma_excluir, name='turma_excluir'),
]
