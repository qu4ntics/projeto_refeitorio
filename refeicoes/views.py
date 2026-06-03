from django.shortcuts import render
from accounts.decorators import perfil_required
from datetime import date, timedelta


@perfil_required('aluno')
def homepage(request):
    return render(request, 'refeicoes/homepage.html')

def cardapio_semana(request):
    hoje = date.today()
    segunda = hoje - timedelta(days=hoje.weekday())

    dias_semana = [
        {'nome': 'Segunda-feira', 'id': 'seg', 'data': segunda, 'hoje': hoje == segunda, 'refeicoes': []},
        {'nome': 'Terça-feira', 'id': 'ter', 'data': segunda + timedelta(1), 'hoje': hoje == segunda + timedelta(1), 'refeicoes': []},
        {'nome': 'Quarta-feira', 'id': 'qua', 'data': segunda + timedelta(2), 'hoje': hoje == segunda + timedelta(2), 'refeicoes': []},
        {'nome': 'Quinta-feira', 'id': 'qui', 'data': segunda + timedelta(3), 'hoje': hoje == segunda + timedelta(3), 'refeicoes': []},
        {'nome': 'Sexta-feira', 'id': 'sex', 'data': segunda + timedelta(4), 'hoje': hoje == segunda + timedelta(4), 'refeicoes': []},
    ]

    context = {
        'semana_inicio': segunda,
        'semana_fim': segunda + timedelta(days=4),
        'dias_semana': dias_semana,
        'dia_extra': {'nome': 'Dia Extra', 'data': None, 'hoje': False, 'refeicoes': []},
    }
    return render(request, 'administrativo/cardapio_semana.html', context)

def criar_refeicao(request):
    return render(request, 'refeicoes/nova-refeicao.html')