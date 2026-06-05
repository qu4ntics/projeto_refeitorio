from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import perfil_required
from administrativo.models import ConfigReserva

from .forms import RefeicaoForm
from .models import Refeicao


def _semana_atual():
    hoje = timezone.localdate()
    segunda = hoje - timedelta(days=hoje.weekday())
    return hoje, segunda, segunda + timedelta(days=6)


def _queryset_refeicoes_periodo(inicio, fim):
    return (
        Refeicao.objects.filter(data__range=(inicio, fim))
        .prefetch_related('pratos')
        .annotate(reservas_ativas=Count('reservas', filter=Q(reservas__status='ativa')))
        .order_by('data', 'tipo')
    )


def _montar_dias_semana(refeicoes):
    hoje = timezone.localdate()
    segunda = hoje - timedelta(days=hoje.weekday())
    dias = [
        ('Segunda-feira', 'seg', segunda),
        ('Terça-feira', 'ter', segunda + timedelta(1)),
        ('Quarta-feira', 'qua', segunda + timedelta(2)),
        ('Quinta-feira', 'qui', segunda + timedelta(3)),
        ('Sexta-feira', 'sex', segunda + timedelta(4)),
    ]
    refeicoes_por_data = {}
    for refeicao in refeicoes:
        refeicoes_por_data.setdefault(refeicao.data, []).append(refeicao)

    return [
        {
            'nome': nome,
            'id': id_dia,
            'data': data_dia,
            'hoje': hoje == data_dia,
            'refeicoes': refeicoes_por_data.get(data_dia, []),
        }
        for nome, id_dia, data_dia in dias
    ]


@perfil_required('aluno')
def homepage(request):
    hoje = timezone.localdate()
    # Buscamos as refeições de hoje até os próximos 3 dias para popular as abas
    refeicoes = _queryset_refeicoes_periodo(hoje, hoje + timedelta(days=3))
    
    # Mapeamos as reservas ativas do aluno para essas refeições (refeicao_id -> reserva_id)
    from reservas.models import Reserva
    reservas_ativas = {
        res.refeicao_id: res.id 
        for res in Reserva.objects.filter(aluno=request.user, status='ativa', refeicao__in=refeicoes)
    }

    dias_semana = _montar_dias_semana(refeicoes)
    
    # Vinculamos o ID da reserva à refeição para uso no template
    for dia in dias_semana:
        for refeicao in dia['refeicoes']:
            refeicao.reserva_id = reservas_ativas.get(refeicao.id)

    return render(request, 'refeicoes/homepage.html', {
        'dias_semana': dias_semana,
        'hoje': hoje
    })

@login_required
@perfil_required('refeitorio')
def lista_presenca(request):
    from datetime import date
    from django.db.models import Q
    from reservas.models import Reserva

    pesquisa = request.GET.get('search', '').strip()
    reservas = Reserva.objects.filter(refeicao__data=date.today())
    if pesquisa:
        reservas = reservas.filter(
            Q(aluno__first_name__icontains=pesquisa)
            | Q(aluno__last_name__icontains=pesquisa)
            | Q(aluno__turma__icontains=pesquisa)
        )

    return render(request, 'refeicoes/lista-presenca.html', {'reservas': reservas, 'pesquisa': pesquisa})
 
@perfil_required('nutricionista')
def cardapio_semana(request):
    hoje = date.today()
    segunda = hoje - timedelta(days=hoje.weekday())
    semana_fim = segunda + timedelta(days=4)

    refeicoes = _queryset_refeicoes_periodo(segunda, semana_fim)

    dias_semana = _montar_dias_semana(refeicoes)
    tab_inicial = next((d['id'] for d in dias_semana if d['hoje']), dias_semana[0]['id'] if dias_semana else 'seg')

    context = {
        'semana_inicio': segunda,
        'semana_fim': semana_fim,
        'dias_semana': dias_semana,
        'tab_inicial': tab_inicial,
        'dia_extra': {'nome': 'Dia Extra', 'data': None, 'hoje': False, 'refeicoes': []},
    }
    return render(request, 'administrativo/cardapio_semana.html', context)


@perfil_required('nutricionista')
def nutricionista_lista(request):
    return redirect('refeicoes:cardapio_semana')


def _redirect_apos_criar(request):
    return redirect('refeicoes:cardapio_semana')


@perfil_required('nutricionista')
def nutricionista_nova(request):
    if request.method == 'POST':
        form = RefeicaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Refeição cadastrada com sucesso.')
            return _redirect_apos_criar(request)
    else:
        form = RefeicaoForm()
    return render(request, 'refeicoes/nova-refeicao.html', {
        'form': form,
        'config_reserva': ConfigReserva.get_config_ativa(),
    })


@perfil_required('nutricionista')
def criar_refeicao(request):
    return nutricionista_nova(request)


@perfil_required('nutricionista')
def nutricionista_deletar(request, pk):
    refeicao = get_object_or_404(Refeicao, pk=pk)
    if request.method == 'POST':
        if refeicao.reservas.exists():
            messages.error(
                request,
                'Esta refeição não pode ser excluída porque já possui reservas vinculadas.',
            )
        else:
            refeicao.delete()
            messages.success(request, 'Refeição excluída com sucesso.')
        return redirect('refeicoes:cardapio_semana')
    return redirect('refeicoes:cardapio_semana')
