from django import forms

from refeicoes.models import Refeicao

from .models import Turma


def label_tipo_refeicao(codigo):
    return dict(Refeicao.TIPOS).get(codigo, codigo)


class TurmaForm(forms.ModelForm):
    dias_contraturno = forms.MultipleChoiceField(
        label='Dias de contraturno',
        choices=Turma.DIAS_SEMANA,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Turma
        fields = ['nome', 'turno', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex.: 1º ano Informática'}),
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
        instance.dias_contraturno = sorted(int(d) for d in dias)
        if commit:
            instance.save()
        return instance
