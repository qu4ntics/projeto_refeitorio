from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


# Reserva de refeição feita por um aluno
class Reserva(models.Model):
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('cancelada', 'Cancelada'),
        ('concluida', 'Concluída'),
    ]

    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'perfil': 'aluno', 'bloqueado': False},
        related_name='reservas'
    )
    refeicao = models.ForeignKey(
        'refeicoes.Refeicao',
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativa')
    reservado_em = models.DateTimeField(auto_now_add=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['aluno', 'refeicao'], name='unique_reserva_aluno_refeicao'),
        ]

    def __str__(self):
        return f'{self.aluno} — {self.refeicao} ({self.status})'

    def clean(self):
        # Comentário: Validação para evitar reservas de usuários bloqueados.
        # O modelo administrativo.Strike já gerencia os strikes dos alunos,
        # com expiração automática em 30 dias. Esta validação garante
        # que contas bloqueadas não façam novas reservas.
        if self.aluno.bloqueado:
            raise ValidationError('Não é possível fazer reservas com uma conta bloqueada.')
