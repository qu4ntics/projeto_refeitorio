from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from reservaif.models import UUIDModel


# Status em que a reserva ainda "vale": ocupa vaga e impede uma segunda
# reserva do mesmo aluno para a mesma refeição. `concluida` entra aqui porque
# marcar presença apenas muda o status — a reserva não deixou de existir.
STATUS_OCUPA_VAGA = ['ativa', 'concluida']


class Reserva(UUIDModel):
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('cancelada', 'Cancelada'),
        ('concluida', 'Concluída'),
    ]

    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'perfil': 'aluno'},
        related_name='reservas',
    )
    refeicao = models.ForeignKey(
        'refeicoes.Refeicao',
        on_delete=models.CASCADE,
        related_name='reservas',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativa')
    reservado_em = models.DateTimeField(auto_now_add=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['aluno', 'refeicao'],
                condition=models.Q(status__in=STATUS_OCUPA_VAGA),
                name='unique_reserva_valida_aluno_refeicao',
            ),
        ]

    def __str__(self):
        return f'{self.aluno} — {self.refeicao} ({self.status})'

    def clean(self):
        if self.aluno.bloqueado:
            raise ValidationError('Não é possível fazer reservas com uma conta bloqueada.')


class PreReserva(UUIDModel):
    STATUS = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('rejeitada', 'Rejeitada'),
        ('expirada', 'Expirada'),
    ]

    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'perfil': 'aluno'},
        related_name='pre_reservas',
    )
    refeicao = models.ForeignKey(
        'refeicoes.Refeicao',
        on_delete=models.CASCADE,
        related_name='pre_reservas',
    )
    status = models.CharField(max_length=12, choices=STATUS, default='pendente')
    expira_em = models.DateTimeField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['aluno', 'refeicao'],
                name='unique_pre_reserva',
            ),
        ]

    def __str__(self):
        return f'{self.aluno} — {self.refeicao} ({self.status})'
