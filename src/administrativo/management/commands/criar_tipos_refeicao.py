"""
Cadastra os tipos de refeição (café, almoço, etc.) e janelas padrão.

Uso:
    python manage.py criar_tipos_refeicao
    python manage.py criar_tipos_refeicao --com-janelas
"""

from django.core.management.base import BaseCommand

from administrativo.services.tipos_refeicao import (
    garantir_janelas_reserva_padrao,
    garantir_tipos_refeicao,
)
from administrativo.models import TipoRefeicao
from refeicoes.models import Refeicao


class Command(BaseCommand):
    help = 'Cadastra os tipos de refeição do sistema (café, almoço, jantar, etc.).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--com-janelas',
            action='store_true',
            help='Cria janelas de reserva padrão para tipos habilitados',
        )

    def handle(self, *args, **options):
        criados, atualizados = garantir_tipos_refeicao()

        labels = dict(Refeicao.TIPOS)
        for tipo in TipoRefeicao.objects.order_by('nome'):
            status = 'habilitado' if tipo.ativo else 'desabilitado'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{labels.get(tipo.nome, tipo.nome)} ({tipo.nome}) — {status}'
                )
            )

        janelas_criadas = 0
        if options['com_janelas']:
            janelas_criadas = garantir_janelas_reserva_padrao()

        self.stdout.write('')
        self.stdout.write(
            self.style.NOTICE(
                f'Concluído: {criados} tipo(s) criado(s), '
                f'{atualizados} atualizado(s), '
                f'{janelas_criadas} janela(s) criada(s).'
            )
        )
