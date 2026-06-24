import json
from datetime import datetime, timedelta, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import ProtectedError, Q, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import perfil_required
from accounts.models import Usuario
from refeicoes.views import _preparar_contexto_semana
from refeicoes.models import Refeicao
from reservas.models import Reserva
from .forms import TurmaForm, label_tipo_refeicao
from .models import Turma, JanelaReserva, TipoRefeicao, Presenca, Strike, ConfigReserva
from .services.chamada import (
    ChamadaError,
    abrir_chamada,
    encerrar_chamada,
    marcar_presenca,
    reabrir_chamada,
    status_chamada_refeicao,
)


@login_required
@perfil_required('nutricionista')
def painel_nutricionista(request):
    """Painel principal da nutricionista com navegação de semanas unificada."""
    ctx = _preparar_contexto_semana(request, request.GET.get('data'))
    
    # Filtramos apenas as 5 primeiras para o resumo do painel, se desejado
    ctx['refeicoes'] = ctx['refeicoes_raw'][:5]
    return render(request, 'administrativo/painel_nutricionista.html', ctx)

@login_required
@perfil_required('refeitorio')
def painel_refeitorio(request):
    """Painel operacional do refeitório com refeições do dia e status da chamada."""
    hoje = timezone.localdate()
    tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}

    refeicoes_hoje = (
        Refeicao.objects.filter(data=hoje, exige_reserva=True)
        .annotate(
            total_reservas=Count(
                'reservas',
                filter=Q(reservas__status__in=['ativa', 'concluida']),
            ),
            presentes=Count('reservas', filter=Q(reservas__status='concluida')),
        )
        .order_by('tipo')
    )

    refeicoes_painel = []
    presencas_confirmadas = 0
    total_reservas_ativas = 0

    for refeicao in refeicoes_hoje:
        tipo_cfg = tipos_por_nome.get(refeicao.tipo)
        horario = tipo_cfg.horario_inicio_consumo if tipo_cfg else None
        refeicoes_painel.append({
            'refeicao': refeicao,
            'horario': horario,
            'status': status_chamada_refeicao(refeicao),
            'total_reservas': refeicao.total_reservas,
            'presentes': refeicao.presentes,
            'tem_strikes': Strike.objects.filter(
                presenca__reserva__refeicao=refeicao,
            ).exists(),
        })
        presencas_confirmadas += refeicao.presentes
        total_reservas_ativas += refeicao.total_reservas

    return render(request, 'administrativo/painel_refeitorio.html', {
        'refeicoes_painel': refeicoes_painel,
        'presencas_confirmadas': presencas_confirmadas,
        'total_reservas_ativas': total_reservas_ativas,
        'aguardando_confirmacao': total_reservas_ativas - presencas_confirmadas,
        'hoje': hoje,
    })

@login_required
@perfil_required('nutricionista')
def alunos_turmas(request):
    """Nível 1 — grid de cards de turma (/administrativo/alunos/)."""
    return render(request, 'administrativo/alunos_turma.html', {'arquivadas': False})


@login_required
@perfil_required('nutricionista')
def alunos_turmas_arquivadas(request):
    """Grid de turmas desativadas."""
    return render(request, 'administrativo/alunos_turma.html', {'arquivadas': True})


def _serialize_turmas_grid(arquivadas=False):
    turmas = Turma.objects.filter(ativo=not arquivadas).order_by('nome')
    nomes_curtos = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    lista = []
    for t in turmas:
        total_alunos = t.alunos.count()
        total_bloqueados = t.alunos.filter(bloqueado=True).count()
        dias = [nomes_curtos[d] for d in sorted(t.dias_contraturno or []) if d in nomes_curtos]
        lista.append({
            'id': str(t.id),
            'nome': t.nome,
            'turno': t.turno,
            'turno_display': t.get_turno_display(),
            'dias_contraturno': dias,
            'total_alunos': total_alunos,
            'total_bloqueados': total_bloqueados,
            'ativo': t.ativo,
        })
    return lista


@login_required
@perfil_required('nutricionista')
def alunos_turma(request, turma_id):
    """Nível 2 — tabela de alunos de uma turma (/administrativo/alunos/<turma_id>/)."""
    turma = get_object_or_404(Turma, pk=turma_id)
    total_alunos = turma.alunos.filter(perfil='aluno').count()
    nomes_curtos = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    dias_semana = [
        {'valor': d, 'label': label, 'curto': nomes_curtos[d]}
        for d, label in Turma.DIAS_SEMANA
    ]
    return render(request, 'administrativo/alunos.html', {
        'turma': turma,
        'turma_id': turma_id,
        'total_alunos': total_alunos,
        'dias_semana': dias_semana,
        'dias_contraturno_set': set(turma.dias_contraturno or []),
        'turma_arquivada': not turma.ativo,
    })


@login_required
@perfil_required('nutricionista')
def lista_turmas_json(request):
    """JSON com lista de turmas para o grid do nível 1."""
    arquivadas = request.GET.get('arquivadas') == '1'
    return JsonResponse({
        'turmas': _serialize_turmas_grid(arquivadas=arquivadas),
        'arquivadas': arquivadas,
    })

@login_required
@perfil_required('nutricionista')
def lista_alunos_turma(request, turma_id):
    """JSON com dados da turma + alunos dela para o nível 2."""
    agora = timezone.now()
    turma = get_object_or_404(Turma, pk=turma_id)
    alunos_qs = Usuario.objects.filter(perfil='aluno', turma=turma)

    lista = []
    for aluno in alunos_qs:
        strikes_ativos = aluno.strikes.filter(expira_em__gt=agora)
        proximo_expira = strikes_ativos.order_by('expira_em').first()
        lista.append({
            'id': str(aluno.id),
            'nome_completo': aluno.get_full_name() or aluno.username,
            'email': aluno.email,
            'strikes_ativos': strikes_ativos.count(),
            'bloqueado': aluno.bloqueado,
            'proximo_strike_expira_em': (
                proximo_expira.expira_em.isoformat() if proximo_expira else None
            ),
        })

    NOMES_CURTOS = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}

    return JsonResponse({
        'turma': {
            'id': str(turma.id),
            'nome': turma.nome,
            'turno': turma.turno,
            'turno_display': turma.get_turno_display(),
            'dias_contraturno': turma.dias_contraturno or [],
            'ativo': turma.ativo,
            'total_alunos': alunos_qs.count(),
        },
        'dias_semana': [
            {'valor': d, 'label': label, 'curto': NOMES_CURTOS[d]}
            for d, label in Turma.DIAS_SEMANA
        ],
        'alunos': lista,
    })


@login_required
@perfil_required('nutricionista')
@require_POST
def turma_atualizar_contraturno(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id)
    try:
        payload = json.loads(request.body)
        dias = payload.get('dias_contraturno', [])
        dias = sorted({int(d) for d in dias if 0 <= int(d) <= 6})
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'erro': 'Dados inválidos.'}, status=400)

    turma.dias_contraturno = dias
    turma.save(update_fields=['dias_contraturno'])
    return JsonResponse({'sucesso': True, 'dias_contraturno': dias})

def _dados_janelas_configuracao():
    tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}
    dados_janelas = []
    for codigo, label in Refeicao.TIPOS:
        tipo = tipos_por_nome.get(codigo)
        if not tipo:
            continue
        janela = JanelaReserva.objects.filter(tipo_refeicao=tipo).first()
        dados_janelas.append({
            'id': tipo.id,
            'nome': tipo.nome,
            'label': label,
            'ativo': tipo.ativo,
            'abertura': janela.horario_abertura.strftime('%H:%M') if janela else '15:00',
            'encerramento': janela.horario_fechamento.strftime('%H:%M') if janela else '07:00',
            'horario_consumo': (
                tipo.horario_inicio_consumo.strftime('%H:%M')
                if tipo.horario_inicio_consumo else '12:00'
            ),
        })
    return dados_janelas


ABAS_CONFIGURACOES = frozenset({'refeicoes', 'reservas', 'strikes', 'conta'})
MINUTOS_CANCELAMENTO_MIN = 15
MINUTOS_CANCELAMENTO_MAX = 240


def _redirect_configuracoes(aba='refeicoes'):
    if aba not in ABAS_CONFIGURACOES:
        aba = 'refeicoes'
    return redirect(f'{reverse("administrativo:configuracoes")}?aba={aba}')


def _aba_configuracoes(request):
    aba = request.GET.get('aba', 'refeicoes')
    return aba if aba in ABAS_CONFIGURACOES else 'refeicoes'


def _formulario_senha_nutri(usuario):
    form = PasswordChangeForm(user=usuario)
    form.fields['old_password'].label = 'Senha atual'
    form.fields['new_password1'].label = 'Nova senha'
    form.fields['new_password2'].label = 'Confirmar nova senha'
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'config-input')
    return form


def _minutos_cancelamento_atual():
    config = ConfigReserva.get_config_ativa()
    return config.minutos_cancelamento if config else 60


def _salvar_minutos_cancelamento(usuario, minutos):
    config = ConfigReserva.get_config_ativa()
    if config:
        ConfigReserva.objects.create(
            abertura=config.abertura,
            encerramento=config.encerramento,
            minutos_cancelamento=minutos,
            criado_por=usuario,
        )
    else:
        ConfigReserva.objects.create(
            abertura=time(15, 0),
            encerramento=time(7, 0),
            minutos_cancelamento=minutos,
            criado_por=usuario,
        )


def _contexto_configuracoes(request, form_senha=None):
    return {
        'janelas': _dados_janelas_configuracao(),
        'minutos_cancelamento': _minutos_cancelamento_atual(),
        'form_senha': form_senha or _formulario_senha_nutri(request.user),
        'regras_strikes': {'limite': 2, 'dias_expiracao': 30},
        'aba_ativa': _aba_configuracoes(request),
    }


def _salvar_config_refeicoes(request):
    tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}
    erros_detectados = False

    for codigo, _ in Refeicao.TIPOS:
        tipo = tipos_por_nome.get(codigo)
        if not tipo:
            continue

        ativo = request.POST.get(f'ativo_{tipo.id}') == 'on'
        tipo.ativo = ativo

        horario_consumo_str = request.POST.get(f'horario_consumo_{tipo.id}')
        if horario_consumo_str:
            try:
                tipo.horario_inicio_consumo = datetime.strptime(
                    horario_consumo_str, '%H:%M'
                ).time()
            except ValueError:
                erros_detectados = True
                messages.error(
                    request,
                    f'Horário de consumo inválido para {label_tipo_refeicao(tipo.nome)}.',
                )

        tipo.save(update_fields=['ativo', 'horario_inicio_consumo'])

        if not ativo:
            continue

        abertura_str = request.POST.get(f'abertura_{tipo.id}')
        encerramento_str = request.POST.get(f'encerramento_{tipo.id}')

        if abertura_str and encerramento_str:
            try:
                abertura_time = datetime.strptime(abertura_str, '%H:%M').time()
                encerramento_time = datetime.strptime(encerramento_str, '%H:%M').time()

                if abertura_time == encerramento_time:
                    raise ValidationError(
                        'O horário de fechamento não pode ser idêntico ao de abertura.'
                    )

                janela, created = JanelaReserva.objects.get_or_create(
                    tipo_refeicao=tipo,
                    defaults={
                        'horario_abertura': abertura_time,
                        'horario_fechamento': encerramento_time,
                    },
                )

                if not created:
                    janela.horario_abertura = abertura_time
                    janela.horario_fechamento = encerramento_time
                    janela.save()

            except ValidationError as e:
                erros_detectados = True
                messages.error(
                    request,
                    f'Erro em {label_tipo_refeicao(tipo.nome)}: {e}',
                )
            except Exception as e:
                erros_detectados = True
                messages.error(
                    request,
                    f'Erro ao salvar {label_tipo_refeicao(tipo.nome)}: {e}',
                )
        else:
            erros_detectados = True
            messages.error(
                request,
                f'Os horários para {label_tipo_refeicao(tipo.nome)} são obrigatórios.',
            )

    if not erros_detectados:
        messages.success(request, 'Configurações de refeições salvas com sucesso!')
        return _redirect_configuracoes('refeicoes')
    return None


@login_required
@perfil_required('nutricionista')
def configuracoes(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'salvar_refeicoes':
            redirect_response = _salvar_config_refeicoes(request)
            if redirect_response:
                return redirect_response

        elif acao == 'salvar_reservas':
            try:
                minutos = int(request.POST.get('minutos_cancelamento', ''))
            except (TypeError, ValueError):
                minutos = None

            if minutos is None or not (MINUTOS_CANCELAMENTO_MIN <= minutos <= MINUTOS_CANCELAMENTO_MAX):
                messages.error(
                    request,
                    f'Informe um prazo entre {MINUTOS_CANCELAMENTO_MIN} e '
                    f'{MINUTOS_CANCELAMENTO_MAX} minutos.',
                )
            else:
                _salvar_minutos_cancelamento(request.user, minutos)
                messages.success(request, 'Prazo de cancelamento salvo com sucesso!')
                return _redirect_configuracoes('reservas')

        elif acao == 'senha':
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
                return _redirect_configuracoes('conta')
            return render(request, 'administrativo/configuracoes.html', {
                **_contexto_configuracoes(request, form_senha=form),
            })

    return render(request, 'administrativo/configuracoes.html', _contexto_configuracoes(request))


@login_required
@perfil_required('nutricionista')
def alunos_bloqueados(request):
    return render(request, 'administrativo/alunos_bloqueados.html')


@login_required
@perfil_required('nutricionista')
def lista_alunos(request):
    """JSON global de alunos com filtros opcionais via query string."""
    agora = timezone.now()
    alunos = Usuario.objects.filter(perfil='aluno').select_related('turma')

    turma_id = request.GET.get('turma')
    if turma_id:
        alunos = alunos.filter(turma_id=turma_id)

    search = request.GET.get('search')
    if search:
        alunos = alunos.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    bloqueados = request.GET.get('bloqueados')
    if bloqueados == 'true':
        alunos = alunos.filter(bloqueado=True)

    lista = []
    for aluno in alunos:
        strikes_ativos = aluno.strikes.filter(expira_em__gt=agora)
        proximo_expira = strikes_ativos.order_by('expira_em').first()
        ultimo_strike = strikes_ativos.order_by('-aplicado_em').first() if aluno.bloqueado else None
        lista.append({
            'id': str(aluno.id),
            'nome_completo': aluno.get_full_name() or aluno.username,
            'email': aluno.email,
            'turma': aluno.turma.nome if aluno.turma else '',
            'turma_id': str(aluno.turma_id) if aluno.turma_id else '',
            'bloqueado': aluno.bloqueado,
            'strikes_ativos': strikes_ativos.count(),
            'proximo_strike_expira_em': (
                proximo_expira.expira_em.isoformat() if proximo_expira else None
            ),
            'bloqueado_em': (
                ultimo_strike.aplicado_em.isoformat() if ultimo_strike else None
            ),
        })

    return JsonResponse({'alunos': lista})

@login_required
@perfil_required('nutricionista')
@require_POST
def desbloquear_aluno(request, aluno_id):
    aluno = get_object_or_404(Usuario, pk=aluno_id, perfil='aluno')
    if not aluno.bloqueado:
        return JsonResponse({'erro': 'Aluno não está bloqueado.'}, status=400)

    agora = timezone.now()
    aluno.bloqueado = False
    aluno.save()
    aluno.strikes.filter(expira_em__gt=agora).update(expira_em=agora)
    return JsonResponse({'sucesso': True, 'id': str(aluno.id), 'bloqueado': aluno.bloqueado})

@login_required
@perfil_required('nutricionista')
def turmas_lista(request):
    return redirect('administrativo:alunos_turmas')

def _context_turma_form(form, **extra):
    nomes_curtos = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
    dias_semana = [
        {'valor': d, 'label': label, 'curto': nomes_curtos[d]}
        for d, label in Turma.DIAS_SEMANA
    ]
    raw = form['dias_contraturno'].value() or []
    dias_contraturno_set = {int(d) for d in raw}
    return {
        'form': form,
        'dias_semana': dias_semana,
        'dias_contraturno_set': dias_contraturno_set,
        **extra,
    }


@login_required
@perfil_required('nutricionista')
def turma_criar(request):
    if request.method == 'POST':
        form = TurmaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turma cadastrada com sucesso.')
            return redirect('administrativo:alunos_turmas')
    else:
        form = TurmaForm()
    return render(request, 'administrativo/turma_form.html', _context_turma_form(
        form,
        titulo='Nova turma',
        subtitulo='Cadastre uma turma para que os alunos possam selecioná-la no registro.',
    ))

@login_required
@perfil_required('nutricionista')
def turma_editar(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    origem = request.GET.get('origem') or request.POST.get('origem')
    if request.method == 'POST':
        form = TurmaForm(request.POST, instance=turma)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turma atualizada com sucesso.')
            if origem in ('alunos', 'arquivadas'):
                return redirect('administrativo:alunos_turma', turma_id=pk)
            return redirect('administrativo:alunos_turmas')
    else:
        form = TurmaForm(instance=turma)
    return render(request, 'administrativo/turma_form.html', _context_turma_form(
        form,
        titulo='Editar turma',
        subtitulo=f'Atualize os dados de {turma.nome}.',
        turma=turma,
        origem=origem,
    ))

@login_required
@perfil_required('nutricionista')
@require_POST
def turma_excluir(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    origem = request.POST.get('origem')
    if origem == 'arquivadas':
        redirect_name = 'administrativo:alunos_turmas_arquivadas'
    else:
        redirect_name = 'administrativo:alunos_turmas'
    if turma.alunos.exists():
        messages.error(
            request,
            'Esta turma não pode ser excluída porque possui alunos vinculados.',
        )
    else:
        try:
            turma.delete()
            messages.success(request, 'Turma excluída com sucesso.')
        except ProtectedError:
            messages.error(
                request,
                'Esta turma não pode ser excluída porque possui alunos vinculados.',
            )
    return redirect(redirect_name)

@login_required
@perfil_required('nutricionista')
def janela_horarios_api(request, tipo_refeicao_id=None):
    """
    Endpoint para listar ou atualizar janelas de horários.
    GET: Lista todas as configurações.
    POST/PUT: Atualiza a configuração de um tipo específico.
    """
    if request.method == 'GET':
        janelas = JanelaReserva.objects.select_related('tipo_refeicao').all()
        data = [
            {
                "tipo_refeicao_id": str(j.tipo_refeicao.id),
                "tipo_refeicao_nome": j.tipo_refeicao.nome,
                "horario_abertura": j.horario_abertura.strftime('%H:%M'),
                "horario_fechamento": j.horario_fechamento.strftime('%H:%M')
            } for j in janelas
        ]
        return JsonResponse(data, safe=False)

    if request.method in ['POST', 'PUT']:
        if not tipo_refeicao_id:
            return JsonResponse({'erro': 'ID do tipo de refeição é obrigatório.'}, status=400)

        try:
            payload = json.loads(request.body)
            if not payload.get('horario_abertura') or not payload.get('horario_fechamento'):
                return JsonResponse({'erro': 'Horários de abertura e fechamento são obrigatórios.'}, status=400)

            tipo = get_object_or_404(TipoRefeicao, pk=tipo_refeicao_id)

            janela, _ = JanelaReserva.objects.get_or_create(tipo_refeicao=tipo)

            janela.horario_abertura = datetime.strptime(payload['horario_abertura'], '%H:%M').time()
            janela.horario_fechamento = datetime.strptime(payload['horario_fechamento'], '%H:%M').time()

            janela.full_clean()
            janela.save()

            return JsonResponse({
                'sucesso': True,
                'tipo_refeicao': tipo.nome,
                'horario_abertura': janela.horario_abertura.strftime('%H:%M'),
                'horario_fechamento': janela.horario_fechamento.strftime('%H:%M')
            })
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON malformado.'}, status=400)
        except KeyError as e:
            return JsonResponse({'erro': f'Campo obrigatório ausente: {str(e)}'}, status=400)
        except ValidationError as e:
            return JsonResponse({'erro': e.message_dict}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=400)

@login_required
@perfil_required('refeitorio')
@require_POST
def abrir_chamada_view(request, refeicao_id):
    refeicao = get_object_or_404(Refeicao, pk=refeicao_id, exige_reserva=True)
    try:
        abrir_chamada(refeicao)
        messages.success(request, f'Chamada aberta para {refeicao.get_tipo_display()}.')
    except ChamadaError as e:
        messages.error(request, str(e))
        return redirect('administrativo:painel_refeitorio')
    return redirect('refeicoes:chamada', refeicao_id=refeicao.id)


@login_required
@perfil_required('refeitorio')
@require_POST
def atualizar_status_reserva(request, reserva_id):
    """
    Endpoint AJAX para o refeitório confirmar presença (marcar como concluída)
    ou desfazer a marcação (voltar para ativa).
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'Dados da requisição inválidos.'}, status=400)

    try:
        checked = data.get('checked')
        if not isinstance(checked, bool):
            return JsonResponse({'erro': 'Valor de presença inválido.'}, status=400)

        with transaction.atomic():
            reserva = get_object_or_404(
                Reserva.objects.select_related('refeicao').select_for_update(),
                pk=reserva_id,
            )
            novo_status = marcar_presenca(reserva, request.user, checked)
        return JsonResponse({'sucesso': True, 'novo_status': novo_status})
    except ChamadaError as e:
        return JsonResponse({'erro': str(e)}, status=403)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)


@login_required
@perfil_required('refeitorio')
@require_POST
def encerrar_chamada_view(request, refeicao_id):
    """Encerra a chamada de uma refeição e aplica strikes nos ausentes."""
    refeicao = get_object_or_404(Refeicao, pk=refeicao_id, exige_reserva=True)
    try:
        resumo = encerrar_chamada(refeicao, request.user)
        request.session[f'chamada_resumo_{refeicao_id}'] = resumo
        messages.success(request, 'Chamada encerrada com sucesso.')
        return redirect('refeicoes:chamada_resumo', refeicao_id=refeicao.id)
    except ChamadaError as e:
        messages.error(request, str(e))
        return redirect('refeicoes:chamada', refeicao_id=refeicao.id)


@login_required
@perfil_required('refeitorio')
@require_POST
def reabrir_chamada_view(request, refeicao_id):
    """Permite reabrir a chamada para correções (não reverte strikes)."""
    refeicao = get_object_or_404(Refeicao, pk=refeicao_id, exige_reserva=True)
    try:
        reabrir_chamada(refeicao)
        messages.info(
            request,
            f'Chamada de {refeicao.get_tipo_display()} reaberta. '
            'Strikes já aplicados não serão removidos.',
        )
        return redirect('refeicoes:chamada', refeicao_id=refeicao.id)
    except ChamadaError as e:
        messages.error(request, str(e))
        return redirect('administrativo:painel_refeitorio')
