"""
Cria um usuário de cada perfil para testes locais.

Uso:
    python manage.py criar_usuarios_teste
    python manage.py criar_usuarios_teste --senha minhasenha
    python manage.py criar_usuarios_teste --reset
"""

from django.core.management.base import BaseCommand

from accounts.models import Usuario
from administrativo.models import Turma

SENHA_PADRAO = 'teste12345'

USUARIOS_TESTE = [
    {
        'username': 'aluno_teste',
        'email': 'aluno@teste.local',
        'first_name': 'Aluno',
        'last_name': 'Teste',
        'perfil': 'aluno',
        'precisa_turma': True,
    },
    {
        'username': 'nutri_teste',
        'email': 'nutri@teste.local',
        'first_name': 'Nutricionista',
        'last_name': 'Teste',
        'perfil': 'nutricionista',
        'precisa_turma': False,
    },
    {
        'username': 'refeitorio_teste',
        'email': 'refeitorio@teste.local',
        'first_name': 'Refeitório',
        'last_name': 'Teste',
        'perfil': 'refeitorio',
        'precisa_turma': False,
    },
]


class Command(BaseCommand):
    help = 'Cria um usuário de cada perfil (aluno, nutricionista, refeitório) para testes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--senha',
            default=SENHA_PADRAO,
            help=f'Senha dos usuários (padrão: {SENHA_PADRAO})',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove os usuários de teste antes de recriá-los',
        )

    def handle(self, *args, **options):
        senha = options['senha']
        emails = [dados['email'] for dados in USUARIOS_TESTE]

        if options['reset']:
            removidos, _ = Usuario.objects.filter(email__in=emails).delete()
            if removidos:
                self.stdout.write(self.style.WARNING(f'Removidos {removidos} registro(s) de teste.'))

        turma = self._obter_turma()

        for dados in USUARIOS_TESTE:
            usuario, criado = Usuario.objects.get_or_create(
                email=dados['email'],
                defaults={
                    'username': dados['username'],
                    'first_name': dados['first_name'],
                    'last_name': dados['last_name'],
                    'perfil': dados['perfil'],
                    'turma': turma if dados['precisa_turma'] else None,
                },
            )

            if not criado:
                usuario.username = dados['username']
                usuario.first_name = dados['first_name']
                usuario.last_name = dados['last_name']
                usuario.perfil = dados['perfil']
                usuario.turma = turma if dados['precisa_turma'] else None
                usuario.bloqueado = False
                usuario.save()

            usuario.set_password(senha)
            usuario.save(update_fields=['password'])

            acao = 'Criado' if criado else 'Atualizado'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{acao}: {usuario.get_full_name()} '
                    f'({usuario.get_perfil_display()}) - {usuario.email}'
                )
            )

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Credenciais de acesso (login por e-mail):'))
        self.stdout.write(f'  Senha: {senha}')
        for dados in USUARIOS_TESTE:
            self.stdout.write(f"  {dados['perfil'].capitalize():14} -> {dados['email']}")

    def _obter_turma(self):
        turma, criada = Turma.objects.get_or_create(
            nome='Turma Teste',
            defaults={'turno': 'matutino', 'dias_contraturno': [2, 4]},
        )
        if criada:
            self.stdout.write(self.style.NOTICE(f'Turma criada: {turma.nome}'))
        return turma
