from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from administrativo.models import Turma
from .models import Usuario


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
