from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import perfil_required
from refeicoes.forms import RefeicaoForm
from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual

from .models import ConfigReserva


@perfil_required('nutricionista')
def painel_nutricionista(request):
    _, start, end = _semana_atual()
    refeicoes = _queryset_refeicoes_periodo(start, end)[:5]
    return render(request, 'administrativo/painel_nutricionista.html', {'refeicoes': refeicoes})


@perfil_required('refeitorio')
def painel_refeitorio(request):
    return render(request, 'administrativo/painel_refeitorio.html')


@perfil_required('nutricionista')
def configuracoes(request):
    form = RefeicaoForm()
    return render(request, 'administrativo/configuracoes.html', {
        'form': form,
        'config_reserva': ConfigReserva.get_config_ativa(),
    })
