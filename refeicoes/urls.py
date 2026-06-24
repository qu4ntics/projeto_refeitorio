from django.urls import path

from . import views

app_name = 'refeicoes'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('strikes/', views.strikes_aluno, name='strikes_aluno'),
    path('lista-presenca/', views.lista_presenca, name='lista-presenca'),
    path('chamada/<uuid:refeicao_id>/', views.chamada, name='chamada'),
    path('chamada/<uuid:refeicao_id>/resumo/', views.chamada_resumo, name='chamada_resumo'),
    path('cardapio/', views.cardapio_semana, name='cardapio_semana'),
    path('criar/', views.criar_refeicao, name='criar'),
    path('nutricionista/', views.nutricionista_lista, name='nutricionista_lista'),
    path('nutricionista/nova/', views.criar_refeicao, name='nutricionista_nova'),
    path('nutricionista/<uuid:pk>/deletar/', views.nutricionista_deletar, name='nutricionista_deletar'),
    path('pratos/', views.pratos_lista, name='pratos_lista'),
    path('pratos/novo/', views.prato_criar, name='prato_criar'),
    path('pratos/<uuid:pk>/editar/', views.prato_editar, name='prato_editar'),
    path('pratos/<uuid:pk>/excluir/', views.prato_excluir, name='prato_excluir'),
    path('nutricionista/<uuid:pk>/editar/', views.refeicao_editar, name= 'nutricionista_editar'),
]
