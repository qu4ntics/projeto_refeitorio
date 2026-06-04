from django.shortcuts import render

from django.utils import timezone
from django.db.models import Q
from .models import Reserva

def lista_presenca(request):
    hoje = timezone.now().date()
    
    # Busca reservas ativas ou concluídas de hoje, trazendo o Usuário e a Refeição juntos
    reservas = Reserva.objects.filter(
        refeicao__data=hoje
    ).exclude(status='cancelada').select_related('aluno', 'refeicao')

    # Filtro de pesquisa por Nome, Sobrenome ou código da Turma
    pesquisa = request.GET.get('search')
    if pesquisa:
        reservas = reservas.filter(
            Q(aluno__first_name__icontains=pesquisa) | 
            Q(aluno__last_name__icontains=pesquisa) |
            Q(aluno__turma__icontains=pesquisa)
        )

    return render(request, 'refeitorio/lista_presenca.html', {
        'reservas': reservas, 
        'pesquisa': pesquisa
    })