"""
Roda o "relógio" das reservas: ativa pré-reservas de contraturno cuja janela
abriu, expira pendências vencidas e encerra chamadas cujo período de consumo
já terminou.

Deve rodar em cron a cada 5-10 minutos (ex.: Render Cron Job):
    python manage.py sincronizar_reservas
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from administrativo.services.chamada import encerrar_chamadas_vencidas
from refeicoes.models import Refeicao
from reservas.services.pre_reserva import sincronizar_pre_reservas


class Command(BaseCommand):
    help = 'Ativa/expira pré-reservas e encerra chamadas vencidas.'

    def handle(self, *args, **options):
        hoje = timezone.localdate()

        futuras = list(
            Refeicao.objects.filter(data__gte=hoje, exige_reserva=True)
        )
        sincronizar_pre_reservas(futuras)
        self.stdout.write(f'Pré-reservas sincronizadas para {len(futuras)} refeição(ões).')

        # Mesma rotina que as telas disparam; aqui ela cobre o caso de ninguém
        # abrir o sistema depois da refeição.
        encerradas = encerrar_chamadas_vencidas()
        self.stdout.write(self.style.SUCCESS(
            f'{encerradas} chamada(s) encerrada(s) automaticamente.'
        ))
