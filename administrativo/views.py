import json
from datetime import datetime
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import ProtectedError
from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from accounts.decorators import perfil_required
from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual

from accounts.models import Usuario

from refeicoes.models import Refeicao

from .forms import TurmaForm, label_tipo_refeicao
from .models import Turma, JanelaReserva, TipoRefeicao


@login_required
@perfil_required('nutricionista')
def painel_nutricionista(request):
    _, start, end = _semana_atual()
    refeicoes = _queryset_refeicoes_periodo(start, end)[:5]
    return render(request, 'administrativo/painel_nutricionista.html', {'refeicoes': refeicoes})

@login_required
@perfil_required('refeitorio')
def painel_refeitorio(request):
    return render(request, 'administrativo/painel_refeitorio.html')

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
        })
    return dados_janelas


@login_required
@perfil_required('nutricionista')
def configuracoes(request):
    if request.method == 'POST' and request.POST.get('acao') == 'salvar_refeicoes':
        tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}
        erros_detectados = False

        for codigo, _ in Refeicao.TIPOS:
            tipo = tipos_por_nome.get(codigo)
            if not tipo:
                continue

            ativo = request.POST.get(f'ativo_{tipo.id}') == 'on'
            tipo.ativo = ativo
            tipo.save(update_fields=['ativo'])

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
            return redirect('administrativo:configuracoes')

    return render(request, 'administrativo/configuracoes.html', {
        'janelas': _dados_janelas_configuracao(),
    })
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
    return render(request, 'administrativo/turma_form.html', {
        'form': form,
        'titulo': 'Nova turma',
        'subtitulo': 'Cadastre uma turma para que os alunos possam selecioná-la no registro.',
    })

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
    return render(request, 'administrativo/turma_form.html', {
        'form': form,
        'titulo': 'Editar turma',
        'subtitulo': f'Atualize os dados de {turma.nome}.',
        'turma': turma,
        'origem': origem,
    })

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
        except KeyError as e:
            return JsonResponse({'erro': f'Campo obrigatório ausente: {str(e)}'}, status=400)
        except ValidationError as e:
            return JsonResponse({'erro': e.message_dict}, status=400)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=400)