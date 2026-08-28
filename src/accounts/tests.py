import re

from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from administrativo.models import AlunoAutorizado, Notificacao, Turma
from .models import CodigoConfirmacaoEmail, MAX_TENTATIVAS, Usuario


def _codigo_do_email():
    """Extrai o código de 6 dígitos do último e-mail enviado."""
    return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)


@override_settings(ALUNO_EMAIL_DOMINIOS=[])
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

    def _cadastrar(self, email='novo@test.com', nome='João Silva'):
        return self.client.post(reverse('accounts:cadastro'), {
            'nome_completo': nome,
            'email': email,
            'senha': 'senha12345',
            'confirmar_senha': 'senha12345',
        })

    def test_cadastro_cria_conta_inativa_e_envia_codigo(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        response = self._cadastrar(email='Novo@test.com')
        self.assertRedirects(response, reverse('accounts:confirmar_email'))

        aluno = Usuario.objects.get(email='novo@test.com')
        self.assertEqual(aluno.first_name, 'João')
        self.assertEqual(aluno.last_name, 'Silva')
        self.assertEqual(aluno.username, 'novo')
        self.assertEqual(aluno.perfil, 'aluno')
        self.assertFalse(aluno.is_active)
        self.assertEqual(aluno.turma, self.turma)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(aluno.email, mail.outbox[0].to)
        self.assertTrue(hasattr(aluno, 'codigo_confirmacao'))

    def test_codigo_correto_ativa_conta_e_loga(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()
        codigo = _codigo_do_email()

        response = self.client.post(reverse('accounts:confirmar_email'), {'codigo': codigo})
        self.assertRedirects(response, reverse('refeicoes:homepage'))

        aluno = Usuario.objects.get(email='novo@test.com')
        self.assertTrue(aluno.is_active)
        self.assertFalse(CodigoConfirmacaoEmail.objects.filter(usuario=aluno).exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_codigo_errado_nao_ativa_e_conta_tentativa(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()

        response = self.client.post(reverse('accounts:confirmar_email'), {'codigo': '000000'})
        self.assertEqual(response.status_code, 200)
        aluno = Usuario.objects.get(email='novo@test.com')
        self.assertFalse(aluno.is_active)
        self.assertEqual(aluno.codigo_confirmacao.tentativas, 1)

    def test_bloqueia_apos_limite_de_tentativas(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()
        codigo = _codigo_do_email()
        for _ in range(MAX_TENTATIVAS):
            self.client.post(reverse('accounts:confirmar_email'), {'codigo': '999999'})

        response = self.client.post(reverse('accounts:confirmar_email'), {'codigo': codigo})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.get(email='novo@test.com').is_active)

    def test_codigo_expirado(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()
        codigo = _codigo_do_email()
        obj = CodigoConfirmacaoEmail.objects.get()
        obj.expira_em = timezone.now() - timezone.timedelta(minutes=1)
        obj.save(update_fields=['expira_em'])

        response = self.client.post(reverse('accounts:confirmar_email'), {'codigo': codigo})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expirado')

    def test_reenviar_dentro_do_cooldown_nao_reenvia(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()
        response = self.client.post(reverse('accounts:reenviar_codigo'))
        self.assertRedirects(response, reverse('accounts:confirmar_email'))
        self.assertEqual(len(mail.outbox), 1)

    def test_reenviar_apos_cooldown_gera_novo_codigo(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar()
        codigo_antigo = _codigo_do_email()
        obj = CodigoConfirmacaoEmail.objects.get()
        obj.enviado_em = timezone.now() - timezone.timedelta(minutes=2)
        obj.save(update_fields=['enviado_em'])

        self.client.post(reverse('accounts:reenviar_codigo'))
        self.assertEqual(len(mail.outbox), 2)

        r = self.client.post(reverse('accounts:confirmar_email'), {'codigo': codigo_antigo})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('accounts:confirmar_email'), {'codigo': _codigo_do_email()})
        self.assertRedirects(r, reverse('refeicoes:homepage'))

    def test_recadastro_reaproveita_conta_inativa(self):
        AlunoAutorizado.objects.create(email='novo@test.com', turma=self.turma)
        self._cadastrar(nome='Nome Antigo')
        pk = Usuario.objects.get(email='novo@test.com').pk

        response = self._cadastrar(nome='Nome Novo')
        self.assertRedirects(response, reverse('accounts:confirmar_email'))
        contas = Usuario.objects.filter(email='novo@test.com')
        self.assertEqual(contas.count(), 1)
        self.assertEqual(contas.first().pk, pk)
        self.assertEqual(contas.first().first_name, 'Nome')
        self.assertEqual(contas.first().last_name, 'Novo')

    def test_confirmar_sem_sessao_redireciona_cadastro(self):
        response = self.client.get(reverse('accounts:confirmar_email'))
        self.assertRedirects(response, reverse('accounts:cadastro'))

    def test_cadastro_recusado_fora_do_roster(self):
        response = self.client.post(reverse('accounts:cadastro'), {
            'nome_completo': 'Fulano Intruso',
            'email': 'intruso@test.com',
            'senha': 'senha12345',
            'confirmar_senha': 'senha12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='intruso@test.com').exists())

    @override_settings(ALUNO_EMAIL_DOMINIOS=['estudante.if.edu.br'])
    def test_cadastro_recusado_dominio_invalido(self):
        AlunoAutorizado.objects.create(email='aluno@gmail.com', turma=self.turma)
        response = self.client.post(reverse('accounts:cadastro'), {
            'nome_completo': 'Aluno Dominio',
            'email': 'aluno@gmail.com',
            'senha': 'senha12345',
            'confirmar_senha': 'senha12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='aluno@gmail.com').exists())

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
        self.assertNotContains(response, 'Marcar todas como lidas')

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
        url = reverse('refeicoes:notificacoes_aluno')
        response = self.client.post(url, {'acao': 'marcar_lidas'})
        self.assertRedirects(response, url)
        self.assertFalse(Notificacao.objects.filter(usuario=self.aluno, lida=False).exists())

    def test_aluno_acessa_notificacoes(self):
        self.client.login(username='cfg@test.com', password='senha12345')
        Notificacao.objects.create(
            usuario=self.aluno,
            titulo='Novo Strike Recebido',
            mensagem='Você recebeu um strike.',
        )
        url = reverse('refeicoes:notificacoes_aluno')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NOTIFICAÇÕES')
        self.assertContains(response, 'Novo Strike Recebido')
        self.assertContains(response, 'Marcar todas como lidas')

    def test_nutricionista_acessa_notificacoes(self):
        nutri = Usuario.objects.create_user(
            username='nutri', email='nutri@test.com', password='123', perfil='nutricionista',
        )
        self.client.login(username='nutri@test.com', password='123')
        Notificacao.objects.create(
            usuario=nutri,
            titulo='Vagas Esgotadas!',
            mensagem='As vagas para o almoço acabaram.',
        )
        url = reverse('refeicoes:notificacoes_aluno')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NOTIFICAÇÕES')
        self.assertContains(response, 'Vagas Esgotadas!')

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


@override_settings(ALUNO_EMAIL_DOMINIOS=[], RATELIMIT_ENABLE=True)
class RateLimitTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)

    def test_cadastro_bloqueia_apos_muitas_tentativas_do_mesmo_ip(self):
        url = reverse('accounts:cadastro')
        for _ in range(10):
            self.client.post(url, {'email': 'x@x.com'})
        resposta = self.client.post(url, {'email': 'x@x.com'})
        self.assertEqual(resposta.status_code, 429)
        self.assertContains(resposta, 'muitas tentativas', status_code=429)
