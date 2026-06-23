from django import forms
from django.utils import timezone

from administrativo.models import TipoRefeicao

from .models import Prato, Refeicao

ORDEM_CATEGORIAS = Prato.ORDEM_CATEGORIAS


def _label_prato(prato):
    if prato.descricao:
        return f'{prato.nome} — {prato.descricao}'
    return prato.nome


def _queryset_pratos_ordenados():
    return Prato.objects.all().order_by('categoria', 'nome')


def pratos_agrupados_por_categoria():
    grupos = []
    for cat, label in Prato.CATEGORIAS:
        pratos = list(Prato.objects.filter(categoria=cat).order_by('nome'))
        if pratos:
            grupos.append({'categoria': cat, 'label': label, 'pratos': pratos})
    return grupos


def pratos_catalogo_por_categoria():
    """Todas as categorias, inclusive vazias — para a tela de catálogo."""
    return [
        {
            'categoria': cat,
            'label': label,
            'pratos': list(Prato.objects.filter(categoria=cat).order_by('nome')),
        }
        for cat, label in Prato.CATEGORIAS
    ]


class PratoForm(forms.ModelForm):
    class Meta:
        model = Prato
        fields = ['nome', 'descricao', 'categoria']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'campo',
                'placeholder': 'Ex.: Frango grelhado',
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'campo',
                'rows': 3,
                'placeholder': 'Ingredientes ou modo de preparo (opcional)',
            }),
            'categoria': forms.Select(attrs={'class': 'campo'}),
        }
        labels = {
            'nome': 'Nome',
            'descricao': 'Descrição',
            'categoria': 'Categoria',
        }


class RefeicaoForm(forms.ModelForm):
    pratos = forms.ModelMultipleChoiceField(
        queryset=Prato.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'check-prato'}),
        required=True,
        label='Pratos do cardápio',
        error_messages={'required': 'Selecione pelo menos um prato.'},
    )

    class Meta:
        model = Refeicao
        fields = ['data', 'tipo', 'limite_vagas', 'exige_reserva']
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'campo'},
            ),
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
        self.fields['data'].input_formats = ['%Y-%m-%d']
        self.fields['limite_vagas'].required = False
        if not self.is_bound and self.initial.get('limite_vagas') is None:
            self.initial.setdefault('limite_vagas', 180)

        habilitados = set(TipoRefeicao.codigos_habilitados())
        choices = [(c, l) for c, l in Refeicao.TIPOS if c in habilitados]
        self.fields['tipo'].choices = [('', 'Selecione')] + choices

        queryset = _queryset_pratos_ordenados()
        self.fields['pratos'].queryset = queryset
        choices = []
        for prato in queryset:
            choices.append((prato.pk, _label_prato(prato)))
        self.fields['pratos'].choices = choices

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data and data < timezone.localdate():
            raise forms.ValidationError('A data não pode ser anterior a hoje.')
        return data

    def clean_tipo(self):
        tipo = self.cleaned_data.get('tipo')
        if tipo and tipo not in TipoRefeicao.codigos_habilitados():
            raise forms.ValidationError('Este tipo de refeição não está habilitado no sistema.')
        return tipo

    def clean_limite_vagas(self):
        limite_vagas = self.cleaned_data.get('limite_vagas')
        if limite_vagas in (None, ''):
            return None
        if limite_vagas < 0:
            raise forms.ValidationError('O limite de vagas deve ser igual ou superior a zero.')
        if self.instance.pk:
            reservas_ativas = self.instance.reservas_ativas_count
            if limite_vagas < reservas_ativas:
                raise forms.ValidationError(
                    f'O limite de vagas não pode ser menor que {reservas_ativas} '
                    f'(número de reservas confirmadas).'
                )
        return limite_vagas

    def clean_pratos(self):
        pratos = self.cleaned_data.get('pratos')
        if pratos is not None and not pratos:
            raise forms.ValidationError('Selecione pelo menos um prato.')
        return pratos

    def clean(self):
        cleaned_data = super().clean()
        exige_reserva = cleaned_data.get('exige_reserva')
        limite_vagas = cleaned_data.get('limite_vagas')

        if not exige_reserva:
            cleaned_data['limite_vagas'] = limite_vagas if limite_vagas is not None else 0
        else:
            if limite_vagas is None:
                self.add_error('limite_vagas', 'Informe o limite de vagas para refeições com reserva.')
            elif limite_vagas == 0:
                self.add_error('limite_vagas', 'O limite deve ser maior que zero para permitir reservas.')

        return cleaned_data

    def save(self, commit=True):
        refeicao = super().save(commit=commit)
        if commit:
            refeicao.pratos.set(self.cleaned_data['pratos'])
        return refeicao