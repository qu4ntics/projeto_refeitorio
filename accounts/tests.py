from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from administrativo.models import Turma
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
            'username': 'novo_aluno',
            'email': 'novo@test.com',
            'turma': str(self.turma.id),
            'senha': 'senha12345',
            'confirmar_senha': 'senha12345',
        })
        self.assertRedirects(response, reverse('accounts:email_verification_sent'))
        aluno = Usuario.objects.get(username='novo_aluno')
        self.assertEqual(aluno.perfil, 'aluno')
        self.assertEqual(aluno.turma, self.turma)
        self.assertFalse(aluno.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('novo@test.com', mail.outbox[0].to)
        self.assertIn('/accounts/cadastro/ativar/', mail.outbox[0].body)

    def test_link_de_verificacao_ativa_conta(self):
        aluno = Usuario.objects.create_user(
            username='aluno_pendente',
            email='pendente@test.com',
            password='senha12345',
            perfil='aluno',
            turma=self.turma,
            is_active=False,
        )
        uid = urlsafe_base64_encode(force_bytes(aluno.pk))
        token = email_verification_token.make_token(aluno)

        response = self.client.get(
            reverse('accounts:email_verification_confirm', args=[uid, token])
        )

        self.assertRedirects(response, reverse('refeicoes:homepage'))
        aluno.refresh_from_db()
        self.assertTrue(aluno.is_active)

    def test_link_de_verificacao_nao_pode_ser_reutilizado(self):
        aluno = Usuario.objects.create_user(
            username='aluno_token_usado',
            email='token_usado@test.com',
            password='senha12345',
            perfil='aluno',
            turma=self.turma,
            is_active=False,
        )
        uid = urlsafe_base64_encode(force_bytes(aluno.pk))
        token = email_verification_token.make_token(aluno)

        self.client.get(
            reverse('accounts:email_verification_confirm', args=[uid, token])
        )
        response = self.client.get(
            reverse('accounts:email_verification_confirm', args=[uid, token])
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Link inválido', status_code=400)

    def test_usuario_inativo_nao_consegue_login_antes_da_verificacao(self):
        Usuario.objects.create_user(
            username='sem_verificar',
            email='sem_verificar@test.com',
            password='senha12345',
            perfil='aluno',
            turma=self.turma,
            is_active=False,
        )

        login_ok = self.client.login(username='sem_verificar', password='senha12345')

        self.assertFalse(login_ok)

    def test_login_exibe_link_esqueci_senha(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, reverse('accounts:password_reset'))
        self.assertContains(response, 'Esqueci minha senha')

    def test_password_reset_envia_email_para_usuario_cadastrado(self):
        Usuario.objects.create_user(
            username='aluno_reset',
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
