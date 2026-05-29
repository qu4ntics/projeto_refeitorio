from django.shortcuts import render
from accounts.decorators import perfil_required


@perfil_required('nutricionista')
def painel_nutricionista(request):
    return render(request, 'administrativo/painel_nutricionista.html')


@perfil_required('refeitorio')
def painel_refeitorio(request):
    return render(request, 'administrativo/painel_refeitorio.html')
