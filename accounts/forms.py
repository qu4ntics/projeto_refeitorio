import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from administrativo.models import Turma
from .models import Usuario


def gerar_username_unico(email):
    base = email.split('@')[0].lower()
    base = re.sub(r'[^\w.@+-]', '', base, flags=re.UNICODE)
    if not base:
        base = 'user'
    base = base[:150]
    if not Usuario.objects.filter(username__iexact=base).exists():
        return base
    i = 2
    while True:
        suffix = str(i)
        candidate = f"{base[:150 - len(suffix)]}{suffix}"
        if not Usuario.objects.filter(username__iexact=candidate).exists():
            return candidate
        i += 1


class EmailAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'
        self.fields['username'].widget = forms.EmailInput(
            attrs={'placeholder': ' ', 'autocomplete': 'email'}
        )


class CadastroForm(forms.ModelForm):
    nome_completo = forms.CharField(
        label='Nome completo',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Nome completo'}),
    )
    senha = forms.CharField(widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(widget=forms.PasswordInput)
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.filter(ativo=True).order_by('nome'),
        empty_label='Turma',
    )

    class Meta:
        model = Usuario
        fields = ['email', 'turma']

    def clean_nome_completo(self):
        nome = self.cleaned_data.get('nome_completo', '').strip()
        if not nome:
            raise forms.ValidationError('Informe seu nome completo.')
        return nome

    def clean(self):
        dados = super().clean()

        senha = dados.get('senha')
        confirmar_senha = dados.get('confirmar_senha')

        if senha != confirmar_senha:
            raise forms.ValidationError("SENHAS NÃO COINCIDEM!!!")

        return dados

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        if ' ' in email:
            raise forms.ValidationError("O email não pode conter espaços!")
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("EMAIL JÁ CADASTRADO!")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        partes = self.cleaned_data['nome_completo'].split(maxsplit=1)
        usuario.first_name = partes[0]
        usuario.last_name = partes[1] if len(partes) > 1 else ''
        usuario.username = gerar_username_unico(usuario.email)
        usuario.perfil = 'aluno'
        usuario.set_password(self.cleaned_data['senha'])

        if commit:
            usuario.save()

        return usuario
