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
from refeicoes.forms import RefeicaoForm
from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual

from .models import ConfigReserva

from accounts.models import Usuario

from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual

from .forms import TurmaForm
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
def configuracoes(request):
    # Traz todos os tipos de refeições cadastrados no banco (Ex: Almoço, Café)
    tipos_refeicao = TipoRefeicao.objects.all().order_by('nome')
    
    if request.method == 'POST':
        erros_detectados = False
        
        for tipo in tipos_refeicao:
            # Captura os dados do POST baseando-se no ID do TipoRefeicao
            abertura_str = request.POST.get(f'abertura_{tipo.id}')
            encerramento_str = request.POST.get(f'encerramento_{tipo.id}')
            
            # Só processa se o usuário enviou ambos os horários
            if abertura_str and encerramento_str:
                try:
                    abertura_time = datetime.strptime(abertura_str, '%H:%M').time()
                    encerramento_time = datetime.strptime(encerramento_str, '%H:%M').time()
                    
                    if abertura_time == encerramento_time:
                        raise ValidationError("O horário de fechamento não pode ser idêntico ao de abertura.")
                    
                    # BUSCA OU CRIA A JANELA: Se não existir no banco, o Django cria o registro associado
                    janela, created = JanelaReserva.objects.get_or_create(
                        tipo_refeicao=tipo,
                        defaults={
                            'horario_abertura': abertura_time,
                            'horario_fechamento': encerramento_time
                        }
                    )
                    
                    # Se ela já existia antes, apenas atualizamos os valores recebidos
                    if not created:
                        janela.horario_abertura = abertura_time
                        janela.horario_fechamento = encerramento_time
                        janela.save()
                        
                except ValidationError as e:
                    erros_detectados = True
                    messages.error(request, f"Erro em {tipo.nome}: {str(e)}")
                except Exception as e:
                    erros_detectados = True
                    messages.error(request, f"Erro ao salvar {tipo.nome}: {str(e)}")
            else:
                erros_detectados = True
                messages.error(request, f"Os horários para {tipo.nome} são obrigatórios.")

        if not erros_detectados:
            messages.success(request, 'Configurações de horários salvas com sucesso!')
            return redirect('administrativo:configuracoes')

    # Preparação segura dos dados para renderizar no HTML
    dados_janelas = []
    for tipo in tipos_refeicao:
        # Tenta buscar a janela correspondente ao tipo, se houver
        janela = JanelaReserva.objects.filter(tipo_refeicao=tipo).first()
        
        dados_janelas.append({
            'id': tipo.id,
            'nome': tipo.nome,
            # Se a janela não existir no banco ainda, exibe um valor padrão para o usuário ajustar
            'abertura': janela.horario_abertura.strftime('%H:%M') if janela else '15:00',
            'encerramento': janela.horario_fechamento.strftime('%H:%M') if janela else '07:00'
        })

    return render(request, 'administrativo/configuracoes.html', {
        'janelas': dados_janelas,
    })
@login_required
@perfil_required('nutricionista')
def lista_alunos(request):
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
def alunos(request):
    turmas = Turma.objects.filter(ativo=True).order_by('nome')
    return render(request, 'administrativo/alunos.html', {'turmas': turmas})


@login_required
@perfil_required('nutricionista')
def turmas_lista(request):
    turmas = Turma.objects.all()
    return render(request, 'administrativo/turmas_lista.html', {'turmas': turmas})


@login_required
@perfil_required('nutricionista')
def turma_criar(request):
    if request.method == 'POST':
        form = TurmaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turma cadastrada com sucesso.')
            return redirect('administrativo:turmas_lista')
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
    if request.method == 'POST':
        form = TurmaForm(request.POST, instance=turma)
        if form.is_valid():
            form.save()
            messages.success(request, 'Turma atualizada com sucesso.')
            return redirect('administrativo:turmas_lista')
    else:
        form = TurmaForm(instance=turma)
    return render(request, 'administrativo/turma_form.html', {
        'form': form,
        'titulo': 'Editar turma',
        'subtitulo': f'Atualize os dados de {turma.nome}.',
        'turma': turma,
    })


@login_required
@perfil_required('nutricionista')
@require_POST
def turma_excluir(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
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
    return redirect('administrativo:turmas_lista')


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
            
            # Busca ou cria a janela para o tipo
            janela, _ = JanelaReserva.objects.get_or_create(tipo_refeicao=tipo)
            
            janela.horario_abertura = datetime.strptime(payload['horario_abertura'], '%H:%M').time()
            janela.horario_fechamento = datetime.strptime(payload['horario_fechamento'], '%H:%M').time()
            
            janela.full_clean() # Executa a validação do Model (Clean)
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
