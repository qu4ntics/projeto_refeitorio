from django.contrib import messages
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import CadastroForm, EmailAuthenticationForm

def cadastro_view(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            usuario = authenticate(
                request,
                username=usuario.email,
                password=form.cleaned_data['senha']
            )
            if usuario is not None:
                login(request, usuario)
                return redirect('refeicoes:homepage')
            else:
                form = CadastroForm()
    else:
        form = CadastroForm()

    return render(request, 'accounts/cadastrar.html', {'form': form})

 
REDIRECT_POR_PERFIL = {
    'aluno': 'refeicoes:homepage',
    'nutricionista': 'administrativo:painel_nutricionista',
    'refeitorio': 'administrativo:painel_refeitorio',
}

class LoginPerfilView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm

    def form_invalid(self, form):
        print("POST:", self.request.POST)
        print("ERROS:", form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        perfil = getattr(self.request.user, 'perfil', 'aluno')
        url_name = REDIRECT_POR_PERFIL.get(perfil, 'refeicoes:homepage')
        return reverse(url_name)
