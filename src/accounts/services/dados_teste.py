from datetime import timedelta

from django.utils import timezone

from accounts.models import Usuario
from administrativo.models import Notificacao, Presenca, Strike
from refeicoes.models import Refeicao
from reservas.models import Reserva

DOMINIO_DEMO = 'demo.local'
SENHA_PADRAO = 'senha'

USUARIOS_STAFF = [
    {
        'username': 'nutri_teste',
        'email': 'nutri@gmail.com',
        'first_name': 'Nutricionista',
        'last_name': 'Teste',
        'perfil': 'nutricionista',
    },
    {
        'username': 'refeitorio_teste',
        'email': 'refeitorio@gmail.com',
        'first_name': 'Refeitório',
        'last_name': 'Teste',
        'perfil': 'refeitorio',
    },
]

PRIMEIROS_NOMES = [
    'Ana', 'Bruno', 'Carla', 'Diego', 'Elena', 'Felipe', 'Gabriela', 'Henrique',
    'Isabela', 'João', 'Karina', 'Lucas', 'Mariana', 'Nicolas', 'Olivia', 'Pedro',
]

SOBRENOMES = [
    'Silva', 'Santos', 'Oliveira', 'Souza', 'Lima', 'Costa', 'Ferreira', 'Almeida',
]

PERFIS_DEMO = [
    {'sufixo': 'normal1', 'strikes': 0, 'label': 'Normal'},
    {'sufixo': 'normal2', 'strikes': 0, 'label': 'Normal'},
    {'sufixo': 'strike', 'strikes': 1, 'label': '1 strike'},
    {'sufixo': 'bloqueado', 'strikes': 2, 'label': 'Bloqueado'},
]


def emails_demo():
    return Usuario.objects.filter(email__iendswith=f'@{DOMINIO_DEMO}')


def slug_turma(nome):
    import re
    import unicodedata

    texto = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', texto).strip('-')[:40] or 'turma'


def garantir_usuarios_staff(senha):
    criados = []
    for dados in USUARIOS_STAFF:
        usuario, foi_criado = Usuario.objects.get_or_create(
            email=dados['email'],
            defaults={
                'username': dados['username'],
                'first_name': dados['first_name'],
                'last_name': dados['last_name'],
                'perfil': dados['perfil'],
            },
        )
        if not foi_criado:
            usuario.username = dados['username']
            usuario.first_name = dados['first_name']
            usuario.last_name = dados['last_name']
            usuario.perfil = dados['perfil']
            usuario.bloqueado = False
            usuario.turma = None
            usuario.save()

        usuario.set_password(senha)
        usuario.save(update_fields=['password'])
        criados.append((usuario, foi_criado))
    return criados


def _obter_refeitorio():
    refeitorio = Usuario.objects.filter(perfil='refeitorio').first()
    if not refeitorio:
        raise ValueError('Nenhum usuário do refeitório encontrado.')
    return refeitorio


def aplicar_strikes(aluno, quantidade, refeitorio=None):
    if quantidade <= 0:
        return 0

    refeitorio = refeitorio or _obter_refeitorio()
    agora = timezone.now()
    criados = 0

    for indice in range(quantidade):
        refeicao = Refeicao.objects.create(
            data=timezone.localdate() - timedelta(days=indice + 1),
            tipo='almoco',
            limite_vagas=50,
            exige_reserva=True,
        )
        reserva = Reserva.objects.create(
            aluno=aluno,
            refeicao=refeicao,
            status='ativa',
        )
        presenca = Presenca.objects.create(
            reserva=reserva,
            confirmado_por=refeitorio,
            compareceu=False,
        )
        aplicado_em = agora - timedelta(days=indice + 1)
        strike = Strike(aluno=aluno, presenca=presenca)
        strike.aplicado_em = aplicado_em
        strike.expira_em = aplicado_em + timedelta(days=30)
        strike.save()
        criados += 1

    aluno.refresh_from_db()
    return criados


def criar_ou_atualizar_aluno_demo(turma, perfil_demo, indice_global, senha, refeitorio):
    slug = slug_turma(turma.nome)
    email = f'{slug}.{perfil_demo["sufixo"]}@{DOMINIO_DEMO}'
    primeiro_nome = PRIMEIROS_NOMES[indice_global % len(PRIMEIROS_NOMES)]
    sobrenome = SOBRENOMES[(indice_global // len(PRIMEIROS_NOMES)) % len(SOBRENOMES)]
    username = email.split('@')[0].replace('.', '_')

    aluno, criado = Usuario.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'first_name': primeiro_nome,
            'last_name': sobrenome,
            'perfil': 'aluno',
            'turma': turma,
            'bloqueado': False,
        },
    )

    if not criado:
        aluno.username = username
        aluno.first_name = primeiro_nome
        aluno.last_name = sobrenome
        aluno.perfil = 'aluno'
        aluno.turma = turma
        aluno.bloqueado = False
        aluno.save()

    aluno.set_password(senha)
    aluno.save(update_fields=['password'])

    Strike.objects.filter(aluno=aluno).delete()
    Notificacao.objects.filter(usuario=aluno).delete()
    aluno.bloqueado = False
    aluno.save(update_fields=['bloqueado'])

    strikes_criados = 0
    if perfil_demo['strikes'] > 0:
        strikes_criados = aplicar_strikes(aluno, perfil_demo['strikes'], refeitorio=refeitorio)

    return {
        'aluno': aluno,
        'criado': criado,
        'perfil': perfil_demo['label'],
        'strikes_criados': strikes_criados,
        'bloqueado': aluno.bloqueado,
    }
