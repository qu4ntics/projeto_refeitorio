from django import forms
from django.utils import timezone

from .models import Refeicao


class RefeicaoForm(forms.ModelForm):
    class Meta:
        model = Refeicao
        fields = ['data', 'tipo', 'descricao', 'limite_vagas', 'exige_reserva']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data and data < timezone.localdate():
            raise forms.ValidationError('A data não pode ser anterior a hoje.')
        return data

    def clean_limite_vagas(self):
        limite_vagas = self.cleaned_data.get('limite_vagas')
        if limite_vagas is not None and limite_vagas < 0:
            raise forms.ValidationError('O limite de vagas deve ser igual ou superior a zero.')
        return limite_vagas

    def clean(self):
        cleaned_data = super().clean()
        exige_reserva = cleaned_data.get('exige_reserva')
        limite_vagas = cleaned_data.get('limite_vagas')

        if exige_reserva and limite_vagas is not None and limite_vagas <= 0:
            self.add_error(
                'limite_vagas',
                'Informe um limite de vagas maior que zero para refeição com reserva.',
            )
        return cleaned_data
