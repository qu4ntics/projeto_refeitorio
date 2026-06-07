from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from accounts.decorators import perfil_required
from accounts.models import Usuario

from refeicoes.views import _queryset_refeicoes_periodo, _semana_atual


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
    alunos = Usuario.objects.filter(perfil='aluno')

    turma = request.GET.get('turma')
    if turma:
        alunos = alunos.filter(turma=turma)

    search = request.GET.get('search')
    if search:
        alunos = alunos.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))

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
            'turma': aluno.get_turma_display(),
            'bloqueado': aluno.bloqueado,
            'strikes_ativos': strikes_ativos.count(),
            'proximo_strike_expira_em': (
                proximo_expira.expira_em.isoformat() if proximo_expira else None
            )
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
    return render(request, 'administrativo/alunos.html')