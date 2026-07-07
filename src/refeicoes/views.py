from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import perfil_required
from accounts.views import REDIRECT_POR_PERFIL
from administrativo.models import ConfigReserva, Notificacao, TipoRefeicao, Presenca, Strike
from administrativo.services.chamada import estado_aluno_chamada, status_chamada_refeicao
from administrativo.services.horarios_refeicao import pode_acessar_lista_chamada
from reservas.models import Reserva

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


def _anexar_status_reserva_aluno(refeicao, reservas_ativas, pre_reservas):
    refeicao.reserva_id = reservas_ativas.get(refeicao.id)
    refeicao.pre_reserva = pre_reservas.get(refeicao.id)


def _horario_inicio_almoco():
    tipo = TipoRefeicao.objects.filter(nome='almoco').first()
    if tipo and tipo.horario_inicio_consumo:
        return tipo.horario_inicio_consumo
    return time(12, 0)


def _almoco_passou(hoje):
    agora = timezone.localtime()
    if agora.date() != hoje:
        return agora.date() > hoje
    return agora.time() >= _horario_inicio_almoco()


def _obter_almoco_em(data):
    return (
        Refeicao.objects.filter(data=data, tipo='almoco')
        .prefetch_related('itens_prato__prato')
        .annotate(reservas_ativas=Count('reservas', filter=Q(reservas__status='ativa')))
        .first()
    )


def _resolver_almoco_destaque(hoje):
    if _almoco_passou(hoje):
        data_alvo = hoje + timedelta(days=1)
        titulo = 'Almoço de amanhã'
    else:
        data_alvo = hoje
        titulo = 'Almoço de hoje'

    refeicao = _obter_almoco_em(data_alvo)
    if not refeicao and data_alvo == hoje:
        amanha = hoje + timedelta(days=1)
        refeicao_amanha = _obter_almoco_em(amanha)
        if refeicao_amanha:
            data_alvo = amanha
            titulo = 'Almoço de amanhã'
            refeicao = refeicao_amanha

    if not refeicao:
        return None

    return {
        'refeicao': refeicao,
        'titulo': titulo,
        'data': data_alvo,
    }


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

    from reservas.models import Reserva, PreReserva
    from reservas.services.pre_reserva import sincronizar_pre_reservas

    hoje = ctx['hoje']
    almoco_destaque = _resolver_almoco_destaque(hoje)

    refeicoes_semana = list(ctx['refeicoes_raw'])
    refeicao_ids_set = {r.id for r in refeicoes_semana}
    if almoco_destaque:
        refeicao_destaque = almoco_destaque['refeicao']
        if refeicao_destaque.id not in refeicao_ids_set:
            refeicoes_semana.append(refeicao_destaque)

    sincronizar_pre_reservas(refeicoes_semana)

    refeicao_ids = [r.id for r in refeicoes_semana]

    reservas_ativas = {
        res.refeicao_id: res.id
        for res in Reserva.objects.filter(
            aluno=request.user,
            status='ativa',
            refeicao_id__in=refeicao_ids,
        )
    }

    pre_reservas = {
        pr.refeicao_id: pr
        for pr in PreReserva.objects.filter(
            aluno=request.user,
            status='pendente',
            expira_em__gt=timezone.now(),
        ).select_related('refeicao')
    }

    if almoco_destaque:
        _anexar_status_reserva_aluno(
            almoco_destaque['refeicao'], reservas_ativas, pre_reservas,
        )

    dias_semana = ctx['dias_semana']
    tab_inicial = next((d['id'] for d in dias_semana if d['hoje']), dias_semana[0]['id'])

    for dia in dias_semana:
        for refeicao in dia['refeicoes']:
            _anexar_status_reserva_aluno(refeicao, reservas_ativas, pre_reservas)

    ctx.update({
        'tab_inicial': tab_inicial,
        'almoco_destaque': almoco_destaque,
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
    })
    return render(request, 'administrativo/cardapio_semana.html', ctx)


@login_required
@perfil_required('refeitorio')
def lista_presenca(request):
    """Redireciona para o painel do refeitório (chamada agora é por refeição)."""
    return redirect('administrativo:painel_refeitorio')


@login_required
@perfil_required('refeitorio')
def chamada(request, refeicao_id):
    refeicao = get_object_or_404(Refeicao, pk=refeicao_id, exige_reserva=True)

    if not pode_acessar_lista_chamada(refeicao):
        messages.warning(
            request,
            'A lista de chamada não está disponível fora do horário da refeição.',
        )
        return redirect('administrativo:painel_refeitorio')

    reservas_qs = (
        Reserva.objects.filter(refeicao=refeicao)
        .select_related('aluno', 'aluno__turma')
        .order_by('aluno__first_name', 'aluno__last_name')
    )

    pesquisa = request.GET.get('search', '').strip()
    if pesquisa:
        reservas_qs = reservas_qs.annotate(
            full_name=Concat('aluno__first_name', Value(' '), 'aluno__last_name')
        ).filter(
            Q(aluno__first_name__icontains=pesquisa)
            | Q(aluno__last_name__icontains=pesquisa)
            | Q(full_name__icontains=pesquisa)
            | Q(aluno__username__icontains=pesquisa)
            | Q(aluno__turma__nome__icontains=pesquisa)
        )

    reservas = []
    presentes = 0
    total_elegiveis = 0
    pendentes_encerrar = 0

    for reserva in reservas_qs:
        estado = estado_aluno_chamada(reserva, refeicao)
        reservas.append({'reserva': reserva, 'estado': estado})
        if reserva.status != 'cancelada':
            total_elegiveis += 1
            if estado == 'presente':
                presentes += 1
            elif estado == 'pendente':
                pendentes_encerrar += 1

    tipo_cfg = TipoRefeicao.objects.filter(nome=refeicao.tipo).first()
    horario_inicio = tipo_cfg.horario_inicio_consumo if tipo_cfg else None
    horario_fim = tipo_cfg.horario_fim_consumo if tipo_cfg else None
    tem_strikes = Strike.objects.filter(presenca__reserva__refeicao=refeicao).exists()

    return render(request, 'refeicoes/lista-presenca.html', {
        'refeicao': refeicao,
        'reservas': reservas,
        'pesquisa': pesquisa,
        'presentes': presentes,
        'total_elegiveis': total_elegiveis,
        'pendentes_encerrar': pendentes_encerrar,
        'status_chamada': status_chamada_refeicao(refeicao),
        'horario_inicio': horario_inicio,
        'horario_fim': horario_fim,
        'tem_strikes': tem_strikes,
    })


@login_required
@perfil_required('refeitorio')
def chamada_resumo(request, refeicao_id):
    refeicao = get_object_or_404(Refeicao, pk=refeicao_id, exige_reserva=True)
    if not refeicao.chamada_finalizada:
        return redirect('refeicoes:chamada', refeicao_id=refeicao.id)

    presencas = Presenca.objects.filter(reserva__refeicao=refeicao).select_related(
        'reserva__aluno', 'reserva__aluno__turma',
    )
    presentes_lista = [p for p in presencas if p.compareceu]
    ausentes_lista = [p for p in presencas if not p.compareceu]
    strikes = Strike.objects.filter(presenca__reserva__refeicao=refeicao).select_related(
        'aluno', 'presenca__reserva__aluno',
    )

    resumo_sessao = request.session.pop(f'chamada_resumo_{refeicao_id}', None)

    return render(request, 'refeicoes/chamada_resumo.html', {
        'refeicao': refeicao,
        'presentes_lista': presentes_lista,
        'ausentes_lista': ausentes_lista,
        'strikes': strikes,
        'bloqueios': resumo_sessao.get('bloqueios', []) if resumo_sessao else [],
        'total_presentes': len(presentes_lista),
        'total_ausentes': len(ausentes_lista),
        'total_strikes': strikes.count(),
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
            refeicao = form.save()
            from reservas.services.pre_reserva import ativar_pre_reservas
            ativar_pre_reservas(refeicao)
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

@perfil_required('nutricionista')
def refeicao_editar(request, pk):
    refeicao = get_object_or_404(Refeicao, pk=pk)

    # Bloqueio 1: Verificação Inicial
    if refeicao.refeicao_iniciada:
        messages.error(request, 'Erro! Não é possível editar porque a refeição já foi iniciada.')
        return redirect('refeicoes:cardapio_semana')

    if request.method == 'POST':
        # Bloqueio 2: Nova verificação no POST (race condition)
        refeicao.refresh_from_db()
        if refeicao.refeicao_iniciada:
            messages.error(request, 'A refeição foi iniciada enquanto você editava. Alterações não salvas.')
            return redirect('refeicoes:cardapio_semana')

        form = RefeicaoForm(request.POST, instance=refeicao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Refeição atualizada com sucesso.')
            return redirect('refeicoes:cardapio_semana')
        else:
            messages.error(request, 'Corrija os erros abaixo para salvar.')
            pratos_selecionados = set(request.POST.getlist('pratos'))
    else:
        form = RefeicaoForm(instance=refeicao)
        pratos_selecionados = set(str(pk) for pk in refeicao.pratos.values_list('pk', flat=True))

    
    return render(request, 'refeicoes/nova-refeicao.html', {
        'form': form,
        'refeicao': refeicao,
        'titulo': 'Editar refeição',
        'subtitulo': 'Altere os dados da refeição e salve suas alterações.',
        'config_reserva': ConfigReserva.get_config_ativa(),
        'pratos_por_categoria': pratos_agrupados_por_categoria(),
        'pratos_selecionados': pratos_selecionados,
    })


@perfil_required('aluno')
def strikes_aluno(request):
    agora = timezone.now()
    strikes = (
        Strike.objects.filter(aluno=request.user)
        .select_related('presenca__reserva__refeicao')
        .order_by('-aplicado_em')
    )
    return render(request, 'refeicoes/strikes_aluno.html', {
        'strikes': strikes,
        'agora': agora,
    })


def _formulario_senha(usuario):
    form = PasswordChangeForm(user=usuario)
    form.fields['old_password'].label = 'Senha atual'
    form.fields['new_password1'].label = 'Nova senha'
    form.fields['new_password2'].label = 'Confirmar nova senha'
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'config-input')
    return form


@perfil_required('aluno', 'nutricionista')
def notificacoes_aluno(request):
    if request.method == 'POST' and request.POST.get('acao') == 'marcar_lidas':
        Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
        messages.success(request, 'Todas as notificações foram marcadas como lidas.')
        return redirect('refeicoes:notificacoes_aluno')

    notificacoes = Notificacao.objects.filter(usuario=request.user)[:30]
    return render(request, 'refeicoes/notificacoes_aluno.html', {
        'notificacoes': notificacoes,
    })


@perfil_required('aluno')
def configuracoes_aluno(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'senha':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            form.fields['old_password'].label = 'Senha atual'
            form.fields['new_password1'].label = 'Nova senha'
            form.fields['new_password2'].label = 'Confirmar nova senha'
            for field in form.fields.values():
                field.widget.attrs.setdefault('class', 'config-input')
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso.')
                return redirect('refeicoes:configuracoes_aluno')
        else:
            form = _formulario_senha(request.user)
    else:
        form = _formulario_senha(request.user)

    return render(request, 'accounts/configuracoes_aluno.html', {
        'form_senha': form,
    })

