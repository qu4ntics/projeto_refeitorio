from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import perfil_required
from accounts.views import REDIRECT_POR_PERFIL
from administrativo.models import ConfigReserva

from .forms import PratoForm, RefeicaoForm, pratos_agrupados_por_categoria, pratos_catalogo_por_categoria
from .models import Prato, Refeicao


def _obter_semana(data_ref_str=None):
    """
    Retorna a data de hoje e o intervalo da semana (Segunda a Domingo)
    baseado em uma data de referência.
    """
    hoje = timezone.localdate()
    if data_ref_str:
        try:
            ref = datetime.strptime(data_ref_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            ref = hoje
    else:
        ref = hoje
    segunda = ref - timedelta(days=ref.weekday())
    return hoje, segunda, segunda + timedelta(days=6)


def _queryset_refeicoes_periodo(inicio, fim):
    return (
        Refeicao.objects.filter(data__range=(inicio, fim))
        .prefetch_related('itens_prato__prato')
        .annotate(reservas_ativas=Count('reservas', filter=Q(reservas__status='ativa')))
        .order_by('data', 'tipo')
    )


def _montar_dias_semana(refeicoes, segunda):
    hoje = timezone.localdate()
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

def _preparar_contexto_semana(request, data_ref_str):
    """Centraliza a lógica de geração de dados da semana para evitar inconsistências entre views."""
    hoje, segunda, semana_fim = _obter_semana(data_ref_str)
    refeicoes = _queryset_refeicoes_periodo(segunda, semana_fim)
    dias_semana = _montar_dias_semana(refeicoes, segunda)
    
    return {
        'hoje': hoje,
        'semana_inicio': segunda,
        'semana_fim': semana_fim,
        'dias_semana': dias_semana,
        'proxima_semana': (segunda + timedelta(days=7)).strftime('%Y-%m-%d'),
        'semana_anterior': (segunda - timedelta(days=7)).strftime('%Y-%m-%d'),
        'refeicoes_raw': refeicoes,
        'data_selecionada': data_ref_str # Flag para mostrar o botão 'Voltar para Hoje'
    }

@login_required
def homepage(request):
    perfil = getattr(request.user, 'perfil', 'aluno')
    if perfil != 'aluno':
        # Se for nutricionista, redireciona para a gestão de cardápio; senão usa o padrão do perfil
        if perfil == 'nutricionista':
            return redirect('refeicoes:cardapio_semana')
        return redirect(REDIRECT_POR_PERFIL.get(perfil, 'refeicoes:homepage'))

    ctx = _preparar_contexto_semana(request, request.GET.get('data'))
    
    from reservas.models import Reserva
    reservas_ativas = {
        res.refeicao_id: res.id
        for res in Reserva.objects.filter(aluno=request.user, status='ativa', refeicao__in=ctx['refeicoes_raw'])
    }

    dias_semana = ctx['dias_semana']
    tab_inicial = next((d['id'] for d in dias_semana if d['hoje']), dias_semana[0]['id'])

    for dia in dias_semana:
        for refeicao in dia['refeicoes']:
            refeicao.reserva_id = reservas_ativas.get(refeicao.id)

    ctx.update({
        'tab_inicial': tab_inicial,
    })
    return render(request, 'refeicoes/homepage.html', ctx)

 
@perfil_required('nutricionista')
def cardapio_semana(request):
    ctx = _preparar_contexto_semana(request, request.GET.get('data'))
    dias_semana = ctx['dias_semana']
    # No painel da nutri, se não for a semana atual, foca na segunda-feira
    tab_inicial = next((d['id'] for d in dias_semana if d['hoje']), 'seg')

    ctx.update({
        'tab_inicial': tab_inicial,
        'dia_extra': {'nome': 'Dia Extra', 'data': None, 'hoje': False, 'refeicoes': []},
    })
    return render(request, 'administrativo/cardapio_semana.html', ctx)


@login_required
@perfil_required('refeitorio')
def lista_presenca(request):
    # Filtro de data: padrão é hoje se não for especificado
    data_param = request.GET.get('data')
    if data_param:
        try:
            data_filtro = datetime.strptime(data_param, '%Y-%m-%d').date()
        except ValueError:
            data_filtro = timezone.localdate()
    else:
        data_filtro = timezone.localdate()

    from reservas.models import Reserva

    # Busca todas as reservas da data (inclusive canceladas) ordenadas por nome
    reservas = (
        Reserva.objects.filter(refeicao__data=data_filtro)
        .select_related('aluno', 'aluno__turma', 'refeicao')
        .order_by('aluno__first_name', 'aluno__last_name')
    )

    pesquisa = request.GET.get('search', '').strip()
    if pesquisa:
        tipos_correspondentes = [k for k, v in Refeicao.TIPOS if pesquisa.lower() in v.lower()]

        reservas = reservas.annotate(
            full_name=Concat('aluno__first_name', Value(' '), 'aluno__last_name')
        ).filter(
            Q(aluno__first_name__icontains=pesquisa)
            | Q(aluno__last_name__icontains=pesquisa)
            | Q(full_name__icontains=pesquisa)
            | Q(aluno__username__icontains=pesquisa)
            | Q(aluno__turma__nome__icontains=pesquisa)
            | Q(refeicao__tipo__in=tipos_correspondentes)
        )

    # Performance: Verifica se o dia está finalizado em uma única query
    refeicoes_info = Refeicao.objects.filter(data=data_filtro).values_list('chamada_finalizada', flat=True)
    dia_finalizado = len(refeicoes_info) > 0 and all(refeicoes_info)

    return render(request, 'refeicoes/lista-presenca.html', {
        'reservas': reservas, 
        'pesquisa': pesquisa,
        'data_filtro': data_filtro,
        'dia_finalizado': dia_finalizado
    })


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
