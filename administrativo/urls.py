from django.urls import path
from . import views

app_name = 'administrativo'

urlpatterns = [
    path('painel_nutricionista/', views.painel_nutricionista, name='painel_nutricionista'),
    path('painel_refeitorio/', views.painel_refeitorio, name='painel_refeitorio'),
    path('alunos/', views.alunos_turmas, name='alunos_turmas'),
    path('alunos/arquivadas/', views.alunos_turmas_arquivadas, name='alunos_turmas_arquivadas'),
    path('alunos/turmas/json/', views.lista_turmas_json, name='lista_turmas_json'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('alunos/json/', views.lista_alunos, name='lista_alunos'),
    path('alunos/<uuid:turma_id>/', views.alunos_turma, name='alunos_turma'),
    path('alunos/<uuid:turma_id>/json/', views.lista_alunos_turma, name='lista_alunos_turma'),
    path('alunos/<uuid:turma_id>/contraturno/', views.turma_atualizar_contraturno, name='turma_atualizar_contraturno'),
    path('alunos/<uuid:aluno_id>/desbloquear/', views.desbloquear_aluno, name='desbloquear_aluno'),
    path('turmas/', views.turmas_lista, name='turmas_lista'),
    path('turmas/nova/', views.turma_criar, name='turma_criar'),
    path('turmas/<uuid:pk>/editar/', views.turma_editar, name='turma_editar'),
    path('turmas/<uuid:pk>/excluir/', views.turma_excluir, name='turma_excluir'),

    # Janela Horarios
    path('configuracoes/janela-horarios/', views.janela_horarios_api, name='janela_horarios_lista'),
    path('configuracoes/janela-horarios/<uuid:tipo_refeicao_id>/', views.janela_horarios_api, name='janela_horarios_detalhe'),
]