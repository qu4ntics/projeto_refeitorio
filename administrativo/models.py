from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from reservaif.models import UUIDModel


class Turma(UUIDModel):
    TURNOS = [
        ('matutino', 'Matutino'),
        ('vespertino', 'Vespertino'),
        ('noturno', 'Noturno'),
    ]
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    nome = models.CharField('Nome', max_length=100)
    turno = models.CharField('Turno', max_length=20, choices=TURNOS, default='matutino')
    dias_contraturno = models.JSONField(
        'Dias de contraturno',
        default=list,
        blank=True,
        help_text='Dias da semana (0=segunda … 6=domingo) em que a turma possui contraturno.',
    )
    ativo = models.BooleanField('Ativa', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

    def __str__(self):
        return self.nome

    def dias_contraturno_display(self):
        labels = dict(self.DIAS_SEMANA)
        return ', '.join(labels[d] for d in sorted(self.dias_contraturno or []) if d in labels)


class Presenca(UUIDModel):
    reserva = models.OneToOneField(
        'reservas.Reserva',
        on_delete=models.CASCADE,
        related_name='presenca',
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'perfil': 'refeitorio'},
        related_name='presencas_confirmadas',
    )
    compareceu = models.BooleanField()
    confirmado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Presença de {self.reserva} - {"Sim" if self.compareceu else "Não"}'


class Strike(UUIDModel):
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='strikes',
    )
    presenca = models.OneToOneField(
        Presenca,
        on_delete=models.CASCADE,
        related_name='strike',
    )
    aplicado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.aplicado_em:
            self.aplicado_em = timezone.now()
        if not self.expira_em:
            self.expira_em = self.aplicado_em + timedelta(days=30)
        super().save(*args, **kwargs)

    def esta_ativo(self):
        return self.expira_em > timezone.now()

    def __str__(self):
        return f'Strike de {self.aluno} até {self.expira_em:%Y-%m-%d %H:%M}'


class ConfigReserva(UUIDModel):
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'perfil': 'nutricionista'},
        related_name='configuracoes_criadas',
    )
    abertura = models.TimeField()
    encerramento = models.TimeField()
    minutos_cancelamento = models.IntegerField()
    vigente_desde = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Configuração de Reserva'
        verbose_name_plural = 'Configurações de Reserva'
        ordering = ['-vigente_desde']

    def __str__(self):
        return f'Configuração desde {self.vigente_desde:%Y-%m-%d %H:%M}'

    @classmethod
    def get_config_ativa(cls):
        return cls.objects.order_by('-vigente_desde').first()
