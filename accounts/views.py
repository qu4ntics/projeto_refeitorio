from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


from .forms import CadastroForm
from .tokens import email_verification_token


def enviar_email_verificacao(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = email_verification_token.make_token(usuario)
    contexto = {
        'usuario': usuario,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': request.get_host(),
        'uid': uid,
        'token': token,
    }
    assunto = render_to_string(
        'accounts/email_verification_subject.txt',
        contexto,
    ).strip()
    mensagem = render_to_string(
        'accounts/email_verification_email.html',
        contexto,
    )
    send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [usuario.email])


def cadastro_view(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            enviar_email_verificacao(request, usuario)
            return redirect('accounts:email_verification_sent')
    else:
        form = CadastroForm()

    return render(request, 'accounts/cadastrar.html', {'form': form})


def email_verification_sent_view(request):
    return render(request, 'accounts/email_verification_sent.html')


def ativar_conta_view(request, uidb64, token):
    UserModel = get_user_model()
    usuario = None

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = UserModel.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        usuario = None

    if usuario is not None and email_verification_token.check_token(usuario, token):
        usuario.is_active = True
        usuario.save(update_fields=['is_active'])
        login(request, usuario, backend='accounts.backends.EmailOrUsernameBackend')
        messages.success(request, 'Email verificado com sucesso.')
        return redirect('refeicoes:homepage')

    return render(request, 'accounts/email_verification_invalid.html', status=400)

 
REDIRECT_POR_PERFIL = {
    'aluno': 'refeicoes:homepage',
    'nutricionista': 'administrativo:painel_nutricionista',
    'refeitorio': 'administrativo:painel_refeitorio',
}

class LoginPerfilView(LoginView):
    template_name = 'accounts/login.html'

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
