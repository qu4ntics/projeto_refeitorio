from django.core.exceptions import ValidationError
from django.db import models

from reservaif.models import UUIDModel


class Prato(UUIDModel):
    CATEGORIAS = [
        ('principal', 'Principal'),
        ('complemento', 'Complemento'),
        ('salada', 'Salada'),
        ('sobremesa', 'Sobremesa'),
    ]

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prato'
        verbose_name_plural = 'Pratos'
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.get_categoria_display()})'


class Refeicao(UUIDModel):
    TIPOS = [
        ('cafe', 'Café'),
        ('lanche_manha', 'Lanche da Manhã'),
        ('almoco', 'Almoço'),
        ('lanche_tarde', 'Lanche da Tarde'),
        ('jantar', 'Jantar'),
    ]

    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    limite_vagas = models.IntegerField()
    exige_reserva = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    pratos = models.ManyToManyField(Prato, through='RefeicaoPrato', related_name='refeicoes')

    class Meta:
        verbose_name = 'Refeição'
        verbose_name_plural = 'Refeições'
        ordering = ['data', 'tipo']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.data}'

    @property
    def reservas_ativas_count(self):
        if hasattr(self, 'reservas_ativas'):
            return self.reservas_ativas
        return self.reservas.filter(status='ativa').count()

    @property
    def descricao_exibicao(self):
        partes = []
        for prato in self.pratos.all():
            texto = (prato.descricao or prato.nome).strip()
            if texto:
                partes.append(texto)
        return ' · '.join(partes)

    @property
    def descricao(self):
        return self.descricao_exibicao

    @property
    def vagas_disponiveis(self):
        return self.limite_vagas - self.reservas_ativas_count

    def clean(self):
        super().clean()
        if self.pk:
            reservas_ativas = self.reservas_ativas_count
            if self.limite_vagas < reservas_ativas:
                raise ValidationError({
                    'limite_vagas': (
                        f'O limite não pode ser menor que {reservas_ativas} '
                        f'(número de reservas ativas).'
                    ),
                })


class RefeicaoPrato(UUIDModel):
    refeicao = models.ForeignKey(Refeicao, on_delete=models.CASCADE, related_name='itens_prato')
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE, related_name='refeicoes_vinculadas')

    class Meta:
        verbose_name = 'Prato da refeição'
        verbose_name_plural = 'Pratos da refeição'
        constraints = [
            models.UniqueConstraint(fields=['refeicao', 'prato'], name='unique_refeicao_prato'),
        ]

    def __str__(self):
        return f'{self.refeicao} — {self.prato}'
