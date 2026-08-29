from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def enviar_codigo_confirmacao(usuario, codigo):
    """Envia o código de confirmação de e-mail para o aluno."""
    contexto = {'usuario': usuario, 'codigo': codigo}
    assunto = render_to_string('accounts/email_codigo_subject.txt', contexto).strip()
    texto = render_to_string('accounts/email_codigo.txt', contexto)
    html = render_to_string('accounts/email_codigo.html', contexto)
    send_mail(
        assunto,
        texto,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        html_message=html,
    )
