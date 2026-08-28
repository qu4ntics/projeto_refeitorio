"""
Roda o "relógio" das reservas: ativa pré-reservas de contraturno cuja janela
abriu, expira pendências vencidas e encerra chamadas cujo período de consumo
já terminou.

Deve rodar em cron a cada 5-10 minutos (ex.: Render Cron Job):
    python manage.py sincronizar_reservas
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Usuario
from administrativo.services.chamada import ChamadaError, encerrar_chamada
from administrativo.services.horarios_refeicao import fase_periodo_consumo
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

        refeitorio = Usuario.objects.filter(perfil='refeitorio').first()
        chamadas_pendentes = Refeicao.objects.filter(
            data=hoje,
            exige_reserva=True,
            chamada_aberta=True,
            chamada_finalizada=False,
        )

        encerradas = 0
        for refeicao in chamadas_pendentes:
            if fase_periodo_consumo(refeicao) != 'depois':
                continue
            if refeitorio is None:
                self.stdout.write(self.style.WARNING(
                    f'Chamada de {refeicao} venceu, mas não há usuário do '
                    f'refeitório para encerrá-la automaticamente.'
                ))
                continue
            try:
                encerrar_chamada(refeicao, refeitorio)
                encerradas += 1
            except ChamadaError as e:
                self.stdout.write(self.style.WARNING(f'{refeicao}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'{encerradas} chamada(s) encerrada(s) automaticamente.'
        ))
