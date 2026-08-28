"""
Popula o cadastro de pratos com itens típicos de refeitório escolar.

Uso:
    python manage.py criar_pratos
    python manage.py criar_pratos --reset
"""

from django.core.management.base import BaseCommand

from refeicoes.models import Prato

PRATOS_PADRAO = [
    # Principais
    {'nome': 'Arroz branco', 'categoria': 'principal'},
    {'nome': 'Arroz integral', 'categoria': 'principal'},
    {'nome': 'Feijão carioca', 'categoria': 'principal'},
    {'nome': 'Feijão preto', 'categoria': 'principal'},
    {'nome': 'Frango grelhado', 'categoria': 'principal'},
    {'nome': 'Frango à parmegiana', 'categoria': 'principal'},
    {'nome': 'Carne de panela', 'categoria': 'principal'},
    {'nome': 'Estrogonofe de frango', 'categoria': 'principal'},
    {'nome': 'Lasanha de carne', 'categoria': 'principal'},
    {'nome': 'Peixe assado', 'categoria': 'principal'},
    {'nome': 'Omelete', 'categoria': 'principal'},
    {'nome': 'Macarrão ao molho', 'categoria': 'principal'},
    {'nome': 'Strogonoff de carne', 'categoria': 'principal'},
    {'nome': 'Lentilha', 'categoria': 'principal'},
    # Complementos
    {'nome': 'Farofa', 'categoria': 'complemento'},
    {'nome': 'Purê de batata', 'categoria': 'complemento'},
    {'nome': 'Batata assada', 'categoria': 'complemento'},
    {'nome': 'Legumes refogados', 'categoria': 'complemento'},
    {'nome': 'Couve refogada', 'categoria': 'complemento'},
    {'nome': 'Polenta', 'categoria': 'complemento'},
    {'nome': 'Mandioca cozida', 'categoria': 'complemento'},
    # Saladas
    {'nome': 'Salada de alface', 'categoria': 'salada'},
    {'nome': 'Vinagrete', 'categoria': 'salada'},
    {'nome': 'Salada de repolho', 'categoria': 'salada'},
    {'nome': 'Salada de beterraba', 'categoria': 'salada'},
    {'nome': 'Salada de cenoura', 'categoria': 'salada'},
    # Sobremesas
    {'nome': 'Gelatina', 'categoria': 'sobremesa'},
    {'nome': 'Fruta da estação', 'categoria': 'sobremesa'},
    {'nome': 'Pudim', 'categoria': 'sobremesa'},
    {'nome': 'Doce de leite', 'categoria': 'sobremesa'},
    {'nome': 'Banana', 'categoria': 'sobremesa'},
    {'nome': 'Maçã', 'categoria': 'sobremesa'},
]


class Command(BaseCommand):
    help = 'Cadastra vários pratos padrão para uso em testes e demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove os pratos padrão antes de recriá-los',
        )

    def handle(self, *args, **options):
        nomes = [dados['nome'] for dados in PRATOS_PADRAO]

        if options['reset']:
            removidos, _ = Prato.all_objects.filter(nome__in=nomes).delete()
            if removidos:
                self.stdout.write(
                    self.style.WARNING(f'Removidos {removidos} prato(s) padrão.')
                )

        criados = 0
        atualizados = 0

        for dados in PRATOS_PADRAO:
            prato, foi_criado = Prato.all_objects.get_or_create(
                nome=dados['nome'],
                defaults={
                    'categoria': dados['categoria'],
                    'ativo': True,
                },
            )

            if foi_criado:
                criados += 1
                acao = 'Criado'
            else:
                prato.categoria = dados['categoria']
                prato.ativo = True
                prato.save(update_fields=['categoria', 'ativo'])
                atualizados += 1
                acao = 'Atualizado'

            self.stdout.write(
                self.style.SUCCESS(
                    f'{acao}: {prato.nome} ({prato.get_categoria_display()})'
                )
            )

        self.stdout.write('')
        self.stdout.write(
            self.style.NOTICE(
                f'Concluído: {criados} criado(s), {atualizados} atualizado(s).'
            )
        )
