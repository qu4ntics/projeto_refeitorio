from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import perfil_required

from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual


@perfil_required('nutricionista')
def painel_nutricionista(request):
    _, start, end = _semana_atual()
    refeicoes = _queryset_refeicoes_periodo(start, end)[:5]
    return render(request, 'administrativo/painel_nutricionista.html', {'refeicoes': refeicoes})


@perfil_required('refeitorio')
def painel_refeitorio(request):
    return render(request, 'administrativo/painel_refeitorio.html')
