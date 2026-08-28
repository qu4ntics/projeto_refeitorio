import re

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm

from administrativo.models import AlunoAutorizado
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

    class Meta:
        model = Usuario
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aluno_autorizado = None
        # Conta inativa preexistente com o mesmo e-mail (cadastro não confirmado).
        self._usuario_pendente = None

    def _post_clean(self):
        if self._aluno_autorizado is not None:
            self.instance.turma = self._aluno_autorizado.turma
        super()._post_clean()

    def _update_errors(self, errors):
        # A turma vem da lista de alunos autorizados (definida em save/_post_clean),
        # não é um campo deste formulário — ignore erros de modelo sobre ela.
        if hasattr(errors, 'error_dict'):
            errors.error_dict.pop('turma', None)
            if not errors.error_dict:
                return
        super()._update_errors(errors)

    def validate_unique(self):
        # Reaproveitando uma conta inativa: o e-mail dela não é "duplicado".
        if self._usuario_pendente is not None:
            return
        super().validate_unique()

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

        email = email.strip().lower()

        existente = Usuario.objects.filter(email__iexact=email).first()
        if existente is not None:
            if existente.is_active:
                raise forms.ValidationError("EMAIL JÁ CADASTRADO!")
            # Conta nunca confirmada: reaproveita no save() e reenvia código.
            self._usuario_pendente = existente

        dominios = settings.ALUNO_EMAIL_DOMINIOS
        if dominios and email.rsplit('@', 1)[-1] not in dominios:
            raise forms.ValidationError(
                'Use seu e-mail institucional (%(dominios)s).'
                % {'dominios': ', '.join(dominios)}
            )

        self._aluno_autorizado = (
            AlunoAutorizado.objects.select_related('turma')
            .filter(email__iexact=email)
            .first()
        )
        if self._aluno_autorizado is None:
            raise forms.ValidationError(
                'Este e-mail não está na lista de alunos autorizados do campus. '
                'Procure a nutricionista.'
            )

        return email

    def save(self, commit=True):
        usuario = self._usuario_pendente or super().save(commit=False)
        usuario.email = self.cleaned_data['email']
        partes = self.cleaned_data['nome_completo'].split(maxsplit=1)
        usuario.first_name = partes[0]
        usuario.last_name = partes[1] if len(partes) > 1 else ''
        if not usuario.username:
            usuario.username = gerar_username_unico(usuario.email)
        usuario.perfil = 'aluno'
        usuario.is_active = False
        if self._aluno_autorizado is not None:
            usuario.turma = self._aluno_autorizado.turma
        usuario.set_password(self.cleaned_data['senha'])

        if commit:
            usuario.save()

        return usuario


class ConfirmarCodigoForm(forms.Form):
    codigo = forms.CharField(
        label='Código',
        max_length=6,
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'pattern': '[0-9]*',
            'maxlength': '6',
            'placeholder': '000000',
        }),
    )

    def __init__(self, *args, codigo_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.codigo_obj = codigo_obj

    def clean_codigo(self):
        codigo = re.sub(r'\s+', '', self.cleaned_data.get('codigo', ''))
        if not (len(codigo) == 6 and codigo.isdigit()):
            raise forms.ValidationError('O código tem 6 dígitos.')
        return codigo

    def clean(self):
        dados = super().clean()
        codigo = dados.get('codigo')
        if not codigo:
            return dados

        if self.codigo_obj is None:
            raise forms.ValidationError(
                'Não há código pendente. Faça o cadastro novamente.'
            )
        if self.codigo_obj.bloqueado:
            raise forms.ValidationError(
                'Muitas tentativas. Reenvie o código e tente de novo.'
            )
        if self.codigo_obj.expirado:
            raise forms.ValidationError('Código expirado. Reenvie o código.')
        if not self.codigo_obj.conferir(codigo):
            raise forms.ValidationError('Código incorreto.')

        return dados
