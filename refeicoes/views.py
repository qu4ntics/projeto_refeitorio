from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta

from accounts.decorators import perfil_required

from .models import Refeicao
from .forms import RefeicaoForm


@perfil_required('aluno')
def homepage(request):
    return render(request, 'refeicoes/homepage.html')


@perfil_required('nutricionista')
def nutricionista_lista(request):
    # lista de refeições da semana atual (segunda a domingo)
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    refeicoes = Refeicao.objects.filter(data__range=(start, end)).order_by('data', 'tipo')
    return render(request, 'refeicoes/nutricionista_lista.html', {'refeicoes': refeicoes})


@perfil_required('nutricionista')
def nutricionista_nova(request):
    if request.method == 'POST':
        form = RefeicaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Refeição cadastrada com sucesso.')
            return redirect('refeicoes:nutricionista_lista')
    else:
        form = RefeicaoForm()
    return render(request, 'refeicoes/nova-refeicao.html', {'form': form})


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
        return redirect('refeicoes:nutricionista_lista')
    return redirect('refeicoes:nutricionista_lista')
