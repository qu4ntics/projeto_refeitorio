from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from administrativo.models import Presenca, Strike, TipoRefeicao, Turma
from reservas.models import Reserva

from .forms import RefeicaoForm
from .models import Refeicao


class RefeicaoFormTipoTests(TestCase):
    def test_form_mostra_apenas_tipos_habilitados(self):
        TipoRefeicao.objects.filter(nome='almoco').update(ativo=True)
        TipoRefeicao.objects.exclude(nome='almoco').update(ativo=False)

        form = RefeicaoForm()
        codigos = [c[0] for c in form.fields['tipo'].choices if c[0]]
        self.assertEqual(codigos, ['almoco'])

    def test_form_rejeita_tipo_nao_habilitado(self):
        TipoRefeicao.objects.update(ativo=False)

        form = RefeicaoForm(data={
            'data': '2099-01-15',
            'tipo': 'almoco',
            'limite_vagas': 50,
            'exige_reserva': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('tipo', form.errors)

    def test_form_preenche_data_na_edicao(self):
        TipoRefeicao.objects.filter(nome='almoco').update(ativo=True)
        refeicao = Refeicao.objects.create(
            data=date(2099, 3, 15),
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )
        form = RefeicaoForm(instance=refeicao)
        self.assertEqual(form['data'].value(), date(2099, 3, 15))
        self.assertIn('2099-03-15', str(form['data']))


class StrikesAlunoViewTests(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(nome='1º ano Informática', turno='matutino')
        self.aluno = Usuario.objects.create_user(
            username='aluno_teste',
            email='aluno@teste.com',
            password='password123',
            perfil='aluno',
            first_name='João',
            last_name='Silva',
            turma=self.turma,
        )
        self.outro_aluno = Usuario.objects.create_user(
            username='outro_aluno',
            email='outro@teste.com',
            password='password123',
            perfil='aluno',
            turma=self.turma,
        )
        self.refeitorio = Usuario.objects.create_user(
            username='func_ref',
            email='ref@test.com',
            password='123',
            perfil='refeitorio',
        )
        self.nutricionista = Usuario.objects.create_user(
            username='nutri',
            email='nutri@test.com',
            password='123',
            perfil='nutricionista',
        )
        self.url = reverse('refeicoes:strikes_aluno')

    def _criar_strike(self, aluno, tipo='almoco', data=None):
        data = data or timezone.localdate()
        refeicao = Refeicao.objects.create(
            data=data,
            tipo=tipo,
            limite_vagas=10,
            exige_reserva=True,
        )
        reserva = Reserva.objects.create(aluno=aluno, refeicao=refeicao, status='ativa')
        presenca = Presenca.objects.create(
            reserva=reserva,
            confirmado_por=self.refeitorio,
            compareceu=False,
        )
        return Strike.objects.create(aluno=aluno, presenca=presenca)

    def test_aluno_acessa_historico_de_strikes(self):
        self.client.login(username='aluno@teste.com', password='password123')
        strike = self._criar_strike(self.aluno)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'STRIKES')
        self.assertContains(response, strike.presenca.reserva.refeicao.get_tipo_display())
        self.assertContains(response, 'Ativo')

    def test_aluno_sem_strikes_ve_mensagem_vazia(self):
        self.client.login(username='aluno@teste.com', password='password123')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Você não possui strikes registrados.')

    def test_aluno_nao_ve_strikes_de_outro_aluno(self):
        self.client.login(username='aluno@teste.com', password='password123')
        self._criar_strike(self.outro_aluno, tipo='jantar')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Jantar')

    def test_nutricionista_nao_acessa_pagina(self):
        self.client.login(username='nutri@test.com', password='123')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_refeitorio_nao_acessa_pagina(self):
        self.client.login(username='ref@test.com', password='123')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_strike_expirado_exibe_badge_correto(self):
        self.client.login(username='aluno@teste.com', password='password123')
        strike = self._criar_strike(self.aluno)
        Strike.objects.filter(pk=strike.pk).update(
            expira_em=timezone.now() - timedelta(days=1),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expirado')
        self.assertNotContains(response, 'strike-badge--ativo')

