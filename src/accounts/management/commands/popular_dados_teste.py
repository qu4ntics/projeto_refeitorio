"""
Popula o banco com alunos de demonstração em todas as turmas ativas.

Cria, por turma:
  - 2 alunos normais
  - 1 aluno com 1 strike ativo
  - 1 aluno bloqueado (2 strikes ativos)

Também garante usuários de nutricionista e refeitório para testes.

Uso:
    python manage.py popular_dados_teste
    python manage.py popular_dados_teste --senha minhasenha
    python manage.py popular_dados_teste --reset
"""

from django.core.management.base import BaseCommand, CommandError

from accounts.services.dados_teste import (
    DOMINIO_DEMO,
    PERFIS_DEMO,
    SENHA_PADRAO,
    criar_ou_atualizar_aluno_demo,
    emails_demo,
    garantir_usuarios_staff,
)
from administrativo.models import Turma


class Command(BaseCommand):
    help = 'Popula turmas com alunos de demonstração (normais, strikes e bloqueados).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--senha',
            default=SENHA_PADRAO,
            help=f'Senha dos usuários criados (padrão: {SENHA_PADRAO})',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help=f'Remove usuários @{DOMINIO_DEMO} antes de recriar os dados',
        )

    def handle(self, *args, **options):
        senha = options['senha']

        if options['reset']:
            removidos, _ = emails_demo().delete()
            if removidos:
                self.stdout.write(
                    self.style.WARNING(f'Removidos {removidos} registro(s) de demonstração.')
                )

        turmas = list(Turma.objects.filter(ativo=True).order_by('nome'))
        if not turmas:
            raise CommandError(
                'Nenhuma turma ativa encontrada. Cadastre turmas antes de popular o banco.'
            )

        staff_criados = 0
        staff = garantir_usuarios_staff(senha)
        refeitorio = None
        for usuario, foi_criado in staff:
            if usuario.perfil == 'refeitorio':
                refeitorio = usuario
            acao = 'Criado' if foi_criado else 'Atualizado'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{acao} staff: {usuario.get_full_name()} ({usuario.email})'
                )
            )
            if foi_criado:
                staff_criados += 1

        if refeitorio is None:
            raise CommandError('Usuário do refeitório não pôde ser criado.')

        total_alunos = 0
        total_bloqueados = 0
        indice_global = 0

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Alunos por turma:'))

        for turma in turmas:
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(f'  {turma.nome} ({turma.get_turno_display()})'))
            if turma.dias_contraturno:
                dias = ', '.join(str(d) for d in sorted(turma.dias_contraturno))
                self.stdout.write(f'    Contraturno: dias {dias}')

            for perfil_demo in PERFIS_DEMO:
                resultado = criar_ou_atualizar_aluno_demo(
                    turma,
                    perfil_demo,
                    indice_global,
                    senha,
                    refeitorio=refeitorio,
                )
                indice_global += 1
                total_alunos += 1
                if resultado['bloqueado']:
                    total_bloqueados += 1

                status = 'BLOQUEADO' if resultado['bloqueado'] else resultado['perfil']
                acao = 'Criado' if resultado['criado'] else 'Atualizado'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    {acao}: {resultado["aluno"].get_full_name()} '
                        f'({resultado["aluno"].email}) — {status}'
                    )
                )

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Resumo:'))
        self.stdout.write(f'  Turmas: {len(turmas)}')
        self.stdout.write(f'  Alunos demo: {total_alunos} ({total_bloqueados} bloqueado(s))')
        self.stdout.write(f'  Staff: nutricionista + refeitório')
        self.stdout.write(f'  Senha padrão: {senha}')
        self.stdout.write(f'  E-mails demo: *@{DOMINIO_DEMO}')
