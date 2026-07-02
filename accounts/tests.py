from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from administrativo.models import Notificacao, Turma
from .models import Usuario
from .tokens import email_verification_token


class UsuarioTurmaTests(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(
            nome='1º ano Informática',
            turno='matutino',
            dias_contraturno=[2],
        )

    def test_aluno_sem_turma_falha_validacao(self):
        aluno = Usuario(username='aluno', email='a@test.com', perfil='aluno')
        with self.assertRaises(ValidationError):
            aluno.full_clean()

    def test_nutricionista_nao_pode_ter_turma(self):
        nutri = Usuario(
            username='nutri',
            email='n@test.com',
            perfil='nutricionista',
            turma=self.turma,
        )
        with self.assertRaises(ValidationError):
            nutri.full_clean()

    def test_save_zera_turma_para_nao_aluno(self):
        nutri = Usuario.objects.create_user(
            username='nutri2',
            email='nutri2@test.com',
            perfil='nutricionista',
        )
        nutri.turma = self.turma
        nutri.save()
        nutri.refresh_from_db()
        self.assertIsNone(nutri.turma)

    def test_cadastro_aluno_com_turma(self):
        response = self.client.post(reverse('accounts:cadastro'), {
            'nome_completo': 'João Silva',
            'email': 'novo@test.com',
            'turma': str(self.turma.id),
            'senha': 'senha12345',
            'confirmar_senha': 'senha12345',
        })
        self.assertEqual(response.status_code, 302)
        aluno = Usuario.objects.get(email='novo@test.com')
        self.assertEqual(aluno.first_name, 'João')
        self.assertEqual(aluno.last_name, 'Silva')
        self.assertEqual(aluno.username, 'novo')
        self.assertEqual(aluno.perfil, 'aluno')
        self.assertEqual(aluno.turma, self.turma)

    def test_login_apenas_por_email(self):
        Usuario.objects.create_user(
            username='aluno_login',
            email='login@test.com',
            password='senha12345',
            first_name='Maria',
            last_name='Santos',
            perfil='aluno',
            turma=self.turma,
        )
        response = self.client.post(reverse('accounts:login'), {
            'username': 'login@test.com',
            'password': 'senha12345',
        })
        self.assertRedirects(response, reverse('refeicoes:homepage'))

    def test_login_por_username_nao_funciona(self):
        Usuario.objects.create_user(
            username='aluno_login',
            email='outro@test.com',
            password='senha12345',
            perfil='aluno',
            turma=self.turma,
        )
        response = self.client.post(reverse('accounts:login'), {
            'username': 'aluno_login',
            'password': 'senha12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_password_reset_envia_email(self):
        Usuario.objects.create_user(
            username='reset_user',
            email='reset@test.com',
            password='senha12345',
            perfil='aluno',
            turma=self.turma,
        )
        response = self.client.post(
            reverse('accounts:password_reset'),
            {'email': 'reset@test.com'},
        )
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset@test.com', mail.outbox[0].to)
        self.assertIn('/accounts/senha/redefinir/', mail.outbox[0].body)


class ConfiguracoesAlunoTests(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(nome='1º ano Mineração', turno='matutino')
        self.aluno = Usuario.objects.create_user(
            username='aluno_cfg',
            email='cfg@test.com',
            password='senha12345',
            first_name='Ala',
            last_name='Bama',
            perfil='aluno',
            turma=self.turma,
        )
        self.url = reverse('refeicoes:configuracoes_aluno')

    def test_aluno_acessa_configuracoes(self):
        self.client.login(username='cfg@test.com', password='senha12345')
        Notificacao.objects.create(
            usuario=self.aluno,
            titulo='Novo Strike Recebido',
            mensagem='Você recebeu um strike.',
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CONFIGURAÇÕES')
        self.assertContains(response, 'Ala Bama')
        self.assertContains(response, 'AL')
        self.assertContains(response, 'strikes ativos')
        self.assertContains(response, 'strike-area--light')
        self.assertContains(response, 'Ver histórico de strikes')
        self.assertContains(response, 'Sair')
        self.assertContains(response, reverse('accounts:logout'))
        self.assertContains(response, 'Novo Strike Recebido')

    def test_nutricionista_nao_acessa(self):
        Usuario.objects.create_user(
            username='nutri', email='nutri@test.com', password='123', perfil='nutricionista',
        )
        self.client.login(username='nutri@test.com', password='123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_marcar_notificacoes_como_lidas(self):
        self.client.login(username='cfg@test.com', password='senha12345')
        Notificacao.objects.create(
            usuario=self.aluno, titulo='Teste', mensagem='Msg',
        )
        response = self.client.post(self.url, {'acao': 'marcar_lidas'})
        self.assertRedirects(response, self.url)
        self.assertFalse(Notificacao.objects.filter(usuario=self.aluno, lida=False).exists())

    def test_alterar_senha(self):
        self.client.login(username='cfg@test.com', password='senha12345')
        response = self.client.post(self.url, {
            'acao': 'senha',
            'old_password': 'senha12345',
            'new_password1': 'novaSenha999',
            'new_password2': 'novaSenha999',
        })
        self.assertRedirects(response, self.url)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password('novaSenha999'))
