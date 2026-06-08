from django import forms

from administrativo.models import Turma
from .models import Usuario


class CadastroForm(forms.ModelForm):
    senha = forms.CharField(widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(widget=forms.PasswordInput)
    turma = forms.ModelChoiceField(
        queryset=Turma.objects.filter(ativo=True).order_by('nome'),
        empty_label='Turma',
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'turma']

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
        usuario.perfil = 'aluno'
        usuario.set_password(self.cleaned_data['senha'])

        if commit:
            usuario.save()

        return usuario
