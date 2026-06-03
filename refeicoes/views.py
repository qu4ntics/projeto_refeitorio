from django.shortcuts import render

from accounts.decorators import perfil_required


@perfil_required('aluno')
def homepage(request):
    return render(request, 'refeicoes/homepage.html')


def lista_presenca(request):
    from datetime import date
    from django.db.models import Q
    from reservas.models import Reserva

    pesquisa = request.GET.get('search', '').strip()
    reservas = Reserva.objects.filter(refeicao__data=date.today())
    if pesquisa:
        reservas = reservas.filter(
            Q(aluno__first_name__icontains=pesquisa)
            | Q(aluno__last_name__icontains=pesquisa)
            | Q(aluno__turma__icontains=pesquisa)
        )

    return render(request, 'refeicoes/lista-presenca.html', {'reservas': reservas, 'pesquisa': pesquisa})
