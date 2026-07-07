from django.db.models.signals import post_save
from django.dispatch import receiver

from refeicoes.models import Refeicao
from reservas.services.pre_reserva import ativar_pre_reservas


@receiver(post_save, sender=Refeicao)
def ativar_pre_reservas_ao_criar_refeicao(sender, instance, created, **kwargs):
    if created and instance.exige_reserva:
        ativar_pre_reservas(instance)
