from django.contrib import messages
from django.db.models import ProtectedError
from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from accounts.decorators import perfil_required
from accounts.models import Usuario

from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual

from .forms import TurmaForm
from .models import Turma


@perfil_required('nutricionista')
def painel_nutricionista(request):
    _, start, end = _semana_atual()
    refeicoes = _queryset_refeicoes_periodo(start, end)[:5]
    return render(request, 'administrativo/painel_nutricionista.html', {'refeicoes': refeicoes})


@perfil_required('refeitorio')
def painel_refeitorio(request):
    return render(request, 'administrativo/painel_refeitorio.html')


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


@perfil_required('nutricionista')
def desbloquear_aluno(request, aluno_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    aluno = get_object_or_404(Usuario, pk=aluno_id, perfil='aluno')
    if not aluno.bloqueado:
        return JsonResponse({'erro': 'Aluno não está bloqueado.'}, status=400)

    agora = timezone.now()
    aluno.bloqueado = False
    aluno.save()
    aluno.strikes.filter(expira_em__gt=agora).update(expira_em=agora)
    return JsonResponse({'sucesso': True, 'id': str(aluno.id), 'bloqueado': aluno.bloqueado})


@perfil_required('nutricionista')
def alunos(request):
    turmas = Turma.objects.filter(ativo=True).order_by('nome')
    return render(request, 'administrativo/alunos.html', {'turmas': turmas})


@perfil_required('nutricionista')
def turmas_lista(request):
    turmas = Turma.objects.all()
    return render(request, 'administrativo/turmas_lista.html', {'turmas': turmas})


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


@perfil_required('nutricionista')
def turma_excluir(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if request.method == 'POST':
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
    return redirect('administrativo:turmas_lista')
