from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .emails import enviar_codigo_confirmacao
from .forms import CadastroForm, ConfirmarCodigoForm, EmailAuthenticationForm
from .models import CodigoConfirmacaoEmail, Usuario

SESSAO_CONFIRMACAO = 'confirmacao_uid'
LOGIN_BACKEND = 'accounts.backends.EmailBackend'


def ratelimited(request, exception=None):
    """Página amigável quando o limite de tentativas por IP é atingido."""
    return render(request, 'accounts/muitas_tentativas.html', status=429)


def _mascarar_email(email):
    try:
        local, dominio = email.split('@', 1)
    except ValueError:
        return email
    if len(local) <= 2:
        visivel = local[:1]
    else:
        visivel = local[:2]
    return f'{visivel}{"*" * max(3, len(local) - len(visivel))}@{dominio}'


def _usuario_pendente(request):
    """Usuário aguardando confirmação, a partir da sessão. Limpa sessão se inválido."""
    uid = request.session.get(SESSAO_CONFIRMACAO)
    if not uid:
        return None
    usuario = Usuario.objects.filter(pk=uid, is_active=False).first()
    if usuario is None:
        request.session.pop(SESSAO_CONFIRMACAO, None)
    return usuario


@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def cadastro_view(request):
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            codigo = CodigoConfirmacaoEmail.gerar_para(usuario)
            enviar_codigo_confirmacao(usuario, codigo)
            request.session[SESSAO_CONFIRMACAO] = str(usuario.pk)
            return redirect('accounts:confirmar_email')
    else:
        form = CadastroForm()

    return render(request, 'accounts/cadastrar.html', {'form': form})


@ratelimit(key='ip', rate='30/h', method='POST', block=True)
def confirmar_email_view(request):
    usuario = _usuario_pendente(request)
    if usuario is None:
        return redirect('accounts:cadastro')

    codigo_obj = getattr(usuario, 'codigo_confirmacao', None)
    if codigo_obj is None:
        codigo = CodigoConfirmacaoEmail.gerar_para(usuario)
        enviar_codigo_confirmacao(usuario, codigo)
        codigo_obj = usuario.codigo_confirmacao

    if request.method == 'POST':
        form = ConfirmarCodigoForm(request.POST, codigo_obj=codigo_obj)
        if form.is_valid():
            usuario.is_active = True
            usuario.save(update_fields=['is_active'])
            codigo_obj.delete()
            request.session.pop(SESSAO_CONFIRMACAO, None)
            login(request, usuario, backend=LOGIN_BACKEND)
            messages.success(request, 'E-mail confirmado. Bem-vindo(a)!')
            return redirect('refeicoes:homepage')
    else:
        form = ConfirmarCodigoForm(codigo_obj=codigo_obj)

    return render(request, 'accounts/confirmar_email.html', {
        'form': form,
        'email_mascarado': _mascarar_email(usuario.email),
        'segundos_reenviar': codigo_obj.segundos_para_reenviar(),
    })


@ratelimit(key='ip', rate='5/h', method='POST', block=True)
@require_POST
def reenviar_codigo_view(request):
    usuario = _usuario_pendente(request)
    if usuario is None:
        return redirect('accounts:cadastro')

    codigo_obj = getattr(usuario, 'codigo_confirmacao', None)
    if codigo_obj is not None and not codigo_obj.pode_reenviar():
        messages.error(
            request,
            f'Aguarde {codigo_obj.segundos_para_reenviar()}s para reenviar o código.',
        )
        return redirect('accounts:confirmar_email')

    codigo = CodigoConfirmacaoEmail.gerar_para(usuario)
    enviar_codigo_confirmacao(usuario, codigo)
    messages.success(request, 'Enviamos um novo código para o seu e-mail.')
    return redirect('accounts:confirmar_email')


REDIRECT_POR_PERFIL = {
    'aluno': 'refeicoes:homepage',
    'nutricionista': 'administrativo:painel_nutricionista',
    'refeitorio': 'administrativo:painel_refeitorio',
}


@method_decorator(
    ratelimit(key='post:username', rate='8/h', method='POST', block=True), name='post'
)
class LoginPerfilView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        perfil = getattr(self.request.user, 'perfil', 'aluno')
        url_name = REDIRECT_POR_PERFIL.get(perfil, 'refeicoes:homepage')
        return reverse(url_name)
