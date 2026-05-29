from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate

from .forms import CadastroForm

def cadastro_view(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            usuario = authenticate(
                request,
                username=usuario.username,
                password=form.cleaned_data['senha']
            )
            if usuario is not None:
                login(request, usuario)
                return redirect('cardapio')
            else:
                form = CadastroForm()
    else:
        form = CadastroForm()

    return render(request, 'accounts/cadastrar.html', {'form': form})