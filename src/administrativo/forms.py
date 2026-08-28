from django import forms

from refeicoes.models import Refeicao

from .models import Turma

TAMANHO_MAXIMO_CSV = 5 * 1024 * 1024  # 5 MB


def label_tipo_refeicao(codigo):
    return dict(Refeicao.TIPOS).get(codigo, codigo)


class TurmaForm(forms.ModelForm):
    dias_contraturno = forms.MultipleChoiceField(
        label='Dias de contraturno',
        choices=Turma.DIAS_CONTRATURNO,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Turma
        fields = ['nome', 'turno', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'campo',
                'placeholder': 'Ex.: 1º ano Informática',
            }),
            'turno': forms.RadioSelect(),
            'ativo': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['dias_contraturno'].initial = [
                str(d) for d in (self.instance.dias_contraturno or [])
            ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        dias = self.cleaned_data.get('dias_contraturno', [])
        validos = {str(d) for d, _ in Turma.DIAS_CONTRATURNO}
        instance.dias_contraturno = sorted(int(d) for d in dias if d in validos)
        if commit:
            instance.save()
        return instance


class ImportarRosterForm(forms.Form):
    arquivo = forms.FileField(
        label='Planilha CSV',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'}),
    )
    criar_turmas = forms.BooleanField(
        required=False,
        initial=True,
        label='Cadastrar automaticamente as turmas que não existirem',
    )
    substituir = forms.BooleanField(
        required=False,
        label='Substituir a lista inteira (remover alunos que não estão nesta planilha)',
    )
    atualizar_contas = forms.BooleanField(
        required=False,
        initial=True,
        label='Atualizar a turma de alunos já cadastrados',
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        nome = (arquivo.name or '').lower()
        if not nome.endswith('.csv'):
            raise forms.ValidationError('Envie um arquivo no formato .csv.')
        if arquivo.size and arquivo.size > TAMANHO_MAXIMO_CSV:
            raise forms.ValidationError('Arquivo muito grande (limite de 5 MB).')
        return arquivo
