from django.shortcuts import render

from accounts.decorators import perfil_required


@perfil_required('aluno')
def homepage(request):
    return render(request, 'refeicoes/homepage.html')
