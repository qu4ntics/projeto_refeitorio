from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import perfil_required
from accounts.views import REDIRECT_POR_PERFIL
from administrativo.models import ConfigReserva, TipoRefeicao

from .forms import PratoForm, RefeicaoForm, pratos_agrupados_por_categoria, pratos_catalogo_por_categoria
from .models import Prato, Refeicao


def _semana_atual():
    hoje = timezone.localdate()
    segunda = hoje - timedelta(days=hoje.weekday())
    return hoje, segunda, segunda + timedelta(days=6)


def _queryset_refeicoes_periodo(inicio, fim):
    return (
        Refeicao.objects.filter(data__range=(inicio, fim))
        .prefetch_related('itens_prato__prato')
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


@login_required
def homepage(request):
    if request.user.perfil != 'aluno':
        url_name = REDIRECT_POR_PERFIL.get(request.user.perfil, 'refeicoes:homepage')
        return redirect(url_name)

    hoje, segunda, _ = _semana_atual()
    semana_fim = segunda + timedelta(days=4)

    refeicoes = _queryset_refeicoes_periodo(segunda, semana_fim)

    from reservas.models import Reserva
    reservas_ativas = {
        res.refeicao_id: res.id
        for res in Reserva.objects.filter(aluno=request.user, status='ativa', refeicao__in=refeicoes)
    }

    dias_semana = _montar_dias_semana(refeicoes)
    tab_inicial = next((d['id'] for d in dias_semana if d['hoje']), dias_semana[0]['id'])

    for dia in dias_semana:
        for refeicao in dia['refeicoes']:
            refeicao.reserva_id = reservas_ativas.get(refeicao.id)

    return render(request, 'refeicoes/homepage.html', {
        'dias_semana': dias_semana,
        'semana_inicio': segunda,
        'semana_fim': semana_fim,
        'tab_inicial': tab_inicial,
    })

@login_required
@perfil_required('refeitorio')
def lista_presenca(request):
    from django.db.models import Q
    from reservas.models import Reserva

    pesquisa = request.GET.get('search', '').strip()
    reservas = (
        Reserva.objects.filter(refeicao__data=timezone.localdate())
        .select_related('aluno', 'aluno__turma', 'refeicao')
        .prefetch_related('refeicao__itens_prato__prato')
    )
    if pesquisa:
        reservas = reservas.filter(
            Q(aluno__first_name__icontains=pesquisa)
            | Q(aluno__last_name__icontains=pesquisa)
            | Q(aluno__turma__nome__icontains=pesquisa)
        )

    return render(request, 'refeicoes/lista-presenca.html', {'reservas': reservas, 'pesquisa': pesquisa})
 
@perfil_required('nutricionista')
def cardapio_semana(request):
    hoje = timezone.localdate()
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
    pratos_selecionados = set()
    if request.method == 'POST':
        pratos_selecionados = set(request.POST.getlist('pratos'))

    return render(request, 'refeicoes/nova-refeicao.html', {
        'form': form,
        'config_reserva': ConfigReserva.get_config_ativa(),
        'pratos_por_categoria': pratos_agrupados_por_categoria(),
        'pratos_selecionados': pratos_selecionados,
        'nenhum_tipo_habilitado': not TipoRefeicao.codigos_habilitados(),
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


@perfil_required('nutricionista')
def pratos_lista(request):
    grupos = pratos_catalogo_por_categoria()
    total_pratos = sum(len(g['pratos']) for g in grupos)
    return render(request, 'refeicoes/pratos_lista.html', {
        'grupos': grupos,
        'total_pratos': total_pratos,
    })


@perfil_required('nutricionista')
def prato_criar(request):
    if request.method == 'POST':
        form = PratoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Prato cadastrado com sucesso.')
            return redirect('refeicoes:pratos_lista')
    else:
        form = PratoForm()
    return render(request, 'refeicoes/prato_form.html', {
        'form': form,
        'titulo': 'Novo prato',
        'subtitulo': 'Cadastre um prato para usar nas refeições do cardápio.',
    })


@perfil_required('nutricionista')
def prato_editar(request, pk):
    prato = get_object_or_404(Prato, pk=pk, ativo=True)
    if request.method == 'POST':
        form = PratoForm(request.POST, instance=prato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Prato atualizado com sucesso.')
            return redirect('refeicoes:pratos_lista')
    else:
        form = PratoForm(instance=prato)
    return render(request, 'refeicoes/prato_form.html', {
        'form': form,
        'prato': prato,
        'titulo': 'Editar prato',
        'subtitulo': 'Altere os dados do prato no catálogo.',
    })


@perfil_required('nutricionista')
def prato_excluir(request, pk):
    prato = get_object_or_404(Prato, pk=pk, ativo=True)
    if request.method == 'POST':
        prato.excluir_logicamente()
        messages.success(request, 'Prato removido do catálogo.')
        return redirect('refeicoes:pratos_lista')
    return redirect('refeicoes:pratos_lista')
