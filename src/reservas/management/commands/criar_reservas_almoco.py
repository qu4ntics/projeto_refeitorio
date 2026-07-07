"""
Cria reservas ativas de alunos para o almoço de uma data.

Uso:
    python manage.py criar_reservas_almoco
    python manage.py criar_reservas_almoco --data 2026-07-08
    python manage.py criar_reservas_almoco --quantidade 10
    python manage.py criar_reservas_almoco --apenas-demo
"""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import Usuario
from refeicoes.models import Prato, Refeicao, RefeicaoPrato
from reservas.models import Reserva

PRATOS_PADRAO = [
    'Arroz branco',
    'Feijão carioca',
    'Frango grelhado',
    'Farofa',
    'Salada de alface',
    'Fruta da estação',
]


def garantir_almoco(data, limite_vagas=50):
    refeicao, criada = Refeicao.objects.get_or_create(
        data=data,
        tipo='almoco',
        defaults={
            'limite_vagas': limite_vagas,
            'exige_reserva': True,
        },
    )

    if not criada and refeicao.limite_vagas < limite_vagas:
        refeicao.limite_vagas = limite_vagas
        refeicao.save(update_fields=['limite_vagas'])

    if not refeicao.pratos.exists():
        for nome in PRATOS_PADRAO:
            prato = Prato.objects.filter(nome=nome, ativo=True).first()
            if prato:
                RefeicaoPrato.objects.get_or_create(refeicao=refeicao, prato=prato)

    return refeicao, criada


def criar_reservas_almoco(data=None, quantidade=None, apenas_demo=False):
    data = data or timezone.localdate()
    refeicao, refeicao_criada = garantir_almoco(data)

    alunos = Usuario.objects.filter(perfil='aluno', bloqueado=False).order_by('email')
    if apenas_demo:
        alunos = alunos.filter(email__iendswith='@demo.local')

    ja_reservaram = set(
        Reserva.objects.filter(
            refeicao=refeicao,
            status='ativa',
        ).values_list('aluno_id', flat=True)
    )

    vagas_ocupadas = len(ja_reservaram)
    vagas_restantes = max(0, refeicao.limite_vagas - vagas_ocupadas)

    if quantidade is not None:
        vagas_restantes = min(vagas_restantes, quantidade)

    criadas = 0
    pulados = 0

    for aluno in alunos:
        if criadas >= vagas_restantes:
            break
        if aluno.id in ja_reservaram:
            pulados += 1
            continue
        Reserva.objects.create(aluno=aluno, refeicao=refeicao, status='ativa')
        criadas += 1

    return {
        'refeicao': refeicao,
        'refeicao_criada': refeicao_criada,
        'criadas': criadas,
        'pulados': pulados,
        'total_ativas': Reserva.objects.filter(refeicao=refeicao, status='ativa').count(),
    }


class Command(BaseCommand):
    help = 'Cria reservas ativas para o almoço de hoje (ou de outra data).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            help='Data da refeição (AAAA-MM-DD). Padrão: hoje.',
        )
        parser.add_argument(
            '--quantidade',
            type=int,
            help='Máximo de novas reservas a criar',
        )
        parser.add_argument(
            '--apenas-demo',
            action='store_true',
            help='Reservar somente alunos com e-mail *@demo.local',
        )
        parser.add_argument(
            '--limite-vagas',
            type=int,
            default=50,
            help='Limite de vagas ao criar a refeição (padrão: 50)',
        )

    def handle(self, *args, **options):
        if options['data']:
            try:
                data = datetime.strptime(options['data'], '%Y-%m-%d').date()
            except ValueError as exc:
                raise CommandError('Data inválida. Use o formato AAAA-MM-DD.') from exc
        else:
            data = timezone.localdate()

        if options['limite_vagas'] < 1:
            raise CommandError('O limite de vagas deve ser pelo menos 1.')

        garantir_almoco(data, limite_vagas=options['limite_vagas'])
        resultado = criar_reservas_almoco(
            data=data,
            quantidade=options['quantidade'],
            apenas_demo=options['apenas_demo'],
        )

        if resultado['refeicao_criada']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Refeição criada: Almoço em {data.strftime("%d/%m/%Y")} '
                    f'({resultado["refeicao"].limite_vagas} vagas)'
                )
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f'Usando refeição existente: Almoço em {data.strftime("%d/%m/%Y")}'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'{resultado["criadas"]} reserva(s) criada(s), '
                f'{resultado["pulados"]} aluno(s) já tinham reserva.'
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f'Total de reservas ativas no almoço: {resultado["total_ativas"]}/'
                f'{resultado["refeicao"].limite_vagas}'
            )
        )
