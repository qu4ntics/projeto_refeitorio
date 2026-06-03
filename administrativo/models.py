from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from reservaif.models import UUIDModel


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
