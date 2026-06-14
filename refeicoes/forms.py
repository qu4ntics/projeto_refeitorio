from django import forms
from django.utils import timezone

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
        # ... widgets ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pratos'].queryset = Prato.objects.all()

        # Novo: validar mínimo de vagas em edição
        if self.instance.pk:
            reservas_ativas = self.instance.reservas_ativas_count
            self.fields['limite_vagas'].help_text = (
                f'Mínimo: {reservas_ativas} (reservas confirmadas)'
            )
            self.fields['limite_vagas'].min_value = reservas_ativas

    def clean_limite_vagas(self):
        """Validação no backend: vagas não podem ser menores que reservas ativas"""
        limite = self.cleaned_data.get('limite_vagas')
        
        if self.instance.pk:  # Só valida em edição, não em criação
            reservas_ativas = self.instance.reservas_ativas_count
            if limite < reservas_ativas:
                raise forms.ValidationError(
                    f'O limite de vagas não pode ser menor que {reservas_ativas} '
                    f'(número de reservas confirmadas).'
                )
        
        return limite