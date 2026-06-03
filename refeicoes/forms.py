from django import forms
from django.utils import timezone

from .models import Prato, Refeicao, RefeicaoPrato


class RefeicaoForm(forms.ModelForm):
    descricao = forms.CharField(
        label='Descrição do prato',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'campo',
            'placeholder': 'Ex.: Arroz, feijão, frango grelhado e salada',
        }),
        required=True,
    )

    class Meta:
        model = Refeicao
        fields = ['data', 'tipo', 'limite_vagas', 'exige_reserva']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'campo'}),
            'tipo': forms.Select(attrs={'class': 'campo'}),
            'limite_vagas': forms.NumberInput(attrs={
                'class': 'campo campo-numero',
                'min': 0,
                'placeholder': '180',
            }),
            'exige_reserva': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
        }
        labels = {
            'data': 'Data',
            'tipo': 'Tipo de refeição',
            'limite_vagas': 'Limite de vagas',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['limite_vagas'].required = False
        if not self.is_bound and self.initial.get('limite_vagas') is None:
            self.initial.setdefault('limite_vagas', 180)

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data and data < timezone.localdate():
            raise forms.ValidationError('A data não pode ser anterior a hoje.')
        return data

    def clean_limite_vagas(self):
        limite_vagas = self.cleaned_data.get('limite_vagas')
        if limite_vagas in (None, ''):
            return None
        if limite_vagas < 0:
            raise forms.ValidationError('O limite de vagas deve ser igual ou superior a zero.')
        return limite_vagas

    def clean(self):
        cleaned_data = super().clean()
        exige_reserva = cleaned_data.get('exige_reserva')
        limite_vagas = cleaned_data.get('limite_vagas')

        if not exige_reserva:
            cleaned_data['limite_vagas'] = limite_vagas if limite_vagas is not None else 0
        elif limite_vagas is None:
            self.add_error('limite_vagas', 'Informe o limite de vagas para refeições com reserva.')
        elif limite_vagas <= 0:
            self.add_error(
                'limite_vagas',
                'Informe um limite de vagas maior que zero para refeição com reserva.',
            )
        return cleaned_data

    def save(self, commit=True):
        refeicao = super().save(commit=commit)
        descricao = self.cleaned_data.get('descricao', '').strip()
        if commit and descricao:
            nome = descricao.split('\n')[0][:200]
            prato = Prato.objects.create(
                nome=nome,
                descricao=descricao,
                categoria='principal',
            )
            RefeicaoPrato.objects.create(refeicao=refeicao, prato=prato)
        return refeicao
