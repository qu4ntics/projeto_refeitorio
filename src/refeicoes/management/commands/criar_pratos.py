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
    {'nome': 'Arroz branco', 'categoria': 'principal', 'descricao': 'Arroz soltinho'},
    {'nome': 'Arroz integral', 'categoria': 'principal', 'descricao': 'Arroz integral cozido'},
    {'nome': 'Feijão carioca', 'categoria': 'principal', 'descricao': 'Feijão carioca temperado'},
    {'nome': 'Feijão preto', 'categoria': 'principal', 'descricao': 'Feijão preto temperado'},
    {'nome': 'Frango grelhado', 'categoria': 'principal', 'descricao': 'Peito de frango grelhado'},
    {'nome': 'Frango à parmegiana', 'categoria': 'principal', 'descricao': 'Filé de frango empanado com molho e queijo'},
    {'nome': 'Carne de panela', 'categoria': 'principal', 'descricao': 'Carne bovina cozida em panela'},
    {'nome': 'Estrogonofe de frango', 'categoria': 'principal', 'descricao': 'Frango em cubos com molho cremoso'},
    {'nome': 'Lasanha de carne', 'categoria': 'principal', 'descricao': 'Lasanha ao molho bolonhesa'},
    {'nome': 'Peixe assado', 'categoria': 'principal', 'descricao': 'Filé de peixe assado com limão'},
    {'nome': 'Omelete', 'categoria': 'principal', 'descricao': 'Omelete simples'},
    {'nome': 'Macarrão ao molho', 'categoria': 'principal', 'descricao': 'Macarrão com molho de tomate'},
    {'nome': 'Strogonoff de carne', 'categoria': 'principal', 'descricao': 'Carne em cubos com molho cremoso'},
    {'nome': 'Lentilha', 'categoria': 'principal', 'descricao': 'Lentilha cozida temperada'},
    # Complementos
    {'nome': 'Farofa', 'categoria': 'complemento', 'descricao': 'Farofa de mandioca'},
    {'nome': 'Purê de batata', 'categoria': 'complemento', 'descricao': 'Purê cremoso de batata'},
    {'nome': 'Batata assada', 'categoria': 'complemento', 'descricao': 'Batata em cubos assada'},
    {'nome': 'Legumes refogados', 'categoria': 'complemento', 'descricao': 'Mix de legumes refogados'},
    {'nome': 'Couve refogada', 'categoria': 'complemento', 'descricao': 'Couve refogada com alho'},
    {'nome': 'Polenta', 'categoria': 'complemento', 'descricao': 'Polenta cremosa'},
    {'nome': 'Mandioca cozida', 'categoria': 'complemento', 'descricao': 'Mandioca cozida'},
    # Saladas
    {'nome': 'Salada de alface', 'categoria': 'salada', 'descricao': 'Alface americana fresca'},
    {'nome': 'Vinagrete', 'categoria': 'salada', 'descricao': 'Tomate, cebola e pimentão'},
    {'nome': 'Salada de repolho', 'categoria': 'salada', 'descricao': 'Repolho ralado temperado'},
    {'nome': 'Salada de beterraba', 'categoria': 'salada', 'descricao': 'Beterraba ralada'},
    {'nome': 'Salada de cenoura', 'categoria': 'salada', 'descricao': 'Cenoura ralada'},
    # Sobremesas
    {'nome': 'Gelatina', 'categoria': 'sobremesa', 'descricao': 'Gelatina de frutas'},
    {'nome': 'Fruta da estação', 'categoria': 'sobremesa', 'descricao': 'Fruta fresca do dia'},
    {'nome': 'Pudim', 'categoria': 'sobremesa', 'descricao': 'Pudim de leite'},
    {'nome': 'Doce de leite', 'categoria': 'sobremesa', 'descricao': 'Doce de leite caseiro'},
    {'nome': 'Banana', 'categoria': 'sobremesa', 'descricao': 'Banana prata'},
    {'nome': 'Maçã', 'categoria': 'sobremesa', 'descricao': 'Maçã fresca'},
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
                    'descricao': dados.get('descricao', ''),
                    'ativo': True,
                },
            )

            if foi_criado:
                criados += 1
                acao = 'Criado'
            else:
                prato.categoria = dados['categoria']
                prato.descricao = dados.get('descricao', '')
                prato.ativo = True
                prato.save(update_fields=['categoria', 'descricao', 'ativo'])
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
