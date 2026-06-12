import json
from datetime import time

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts.models import Usuario
from .models import Turma, TipoRefeicao, JanelaReserva


class TurmaCRUDTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri',
            email='nutri@test.com',
            password='senha123',
            perfil='nutricionista',
        )
        self.turma = Turma.objects.create(
            nome='2º ano Administração',
            turno='vespertino',
            dias_contraturno=[4],
        )
        self.client.login(username='nutri', password='senha123')

    def test_lista_turmas_requer_nutricionista(self):
        response = self.client.get(reverse('administrativo:turmas_lista'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2º ano Administração')

    def test_aluno_nao_acessa_crud_turmas(self):
        aluno = Usuario.objects.create_user(
            username='aluno',
            email='aluno@test.com',
            password='senha123',
            perfil='aluno',
            turma=self.turma,
        )
        self.client.logout()
        self.client.login(username='aluno', password='senha123')
        response = self.client.get(reverse('administrativo:turmas_lista'))
        self.assertEqual(response.status_code, 403)

    def test_criar_turma(self):
        response = self.client.post(reverse('administrativo:turma_criar'), {
            'nome': 'Turma teste contraturno',
            'turno': 'noturno',
            'dias_contraturno': ['1', '3'],
            'ativo': True,
        })
        self.assertRedirects(response, reverse('administrativo:turmas_lista'))
        turma = Turma.objects.get(nome='Turma teste contraturno')
        self.assertEqual(turma.dias_contraturno, [1, 3])

    def test_excluir_turma_sem_alunos(self):
        turma_vazia = Turma.objects.create(nome='Turma vazia', turno='matutino')
        response = self.client.post(reverse('administrativo:turma_excluir', args=[turma_vazia.id]))
        self.assertRedirects(response, reverse('administrativo:turmas_lista'))
        self.assertFalse(Turma.objects.filter(pk=turma_vazia.id).exists())

    def test_excluir_turma_com_alunos_bloqueado(self):
        Usuario.objects.create_user(
            username='aluno_turma',
            email='aluno_turma@test.com',
            password='senha123',
            perfil='aluno',
            turma=self.turma,
        )
        response = self.client.post(reverse('administrativo:turma_excluir', args=[self.turma.id]))
        self.assertRedirects(response, reverse('administrativo:turmas_lista'))
        self.assertTrue(Turma.objects.filter(pk=self.turma.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('alunos vinculados' in str(m).lower() for m in messages))


class ConfiguracoesTipoRefeicaoTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_cfg',
            email='nutri_cfg@test.com',
            password='123',
            perfil='nutricionista',
        )
        self.client.login(username='nutri_cfg', password='123')

    def test_tipos_seed_existem(self):
        self.assertEqual(TipoRefeicao.objects.count(), 5)

    def test_habilitar_tipo_e_salvar_horarios(self):
        tipo = TipoRefeicao.objects.get(nome='almoco')
        response = self.client.post(reverse('administrativo:configuracoes'), {
            'acao': 'salvar_refeicoes',
            f'ativo_{tipo.id}': 'on',
            f'abertura_{tipo.id}': '15:00',
            f'encerramento_{tipo.id}': '07:00',
        })
        self.assertRedirects(response, reverse('administrativo:configuracoes'))
        tipo.refresh_from_db()
        self.assertTrue(tipo.ativo)
        self.assertEqual(tipo.janela.horario_abertura.strftime('%H:%M'), '15:00')

    def test_desabilitar_tipo_nao_exige_horarios(self):
        tipo = TipoRefeicao.objects.get(nome='almoco')
        tipo.ativo = True
        tipo.save()
        JanelaReserva.objects.create(
            tipo_refeicao=tipo,
            horario_abertura=time(15, 0),
            horario_fechamento=time(7, 0),
        )
        response = self.client.post(reverse('administrativo:configuracoes'), {
            'acao': 'salvar_refeicoes',
        })
        self.assertRedirects(response, reverse('administrativo:configuracoes'))
        tipo.refresh_from_db()
        self.assertFalse(tipo.ativo)


class JanelaReservaAPITests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_api', email='nutri_api@test.com', 
            password='123', perfil='nutricionista'
        )
        self.tipo = TipoRefeicao.objects.get(nome='almoco')
        JanelaReserva.objects.get_or_create(
            tipo_refeicao=self.tipo,
            defaults={
                'horario_abertura': time(15, 0),
                'horario_fechamento': time(7, 0),
            },
        )
        self.client.login(username='nutri_api', password='123')

    def test_get_janelas(self):
        url = reverse('administrativo:janela_horarios_lista')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_update_janela_sucesso(self):
        url = reverse('administrativo:janela_horarios_detalhe', args=[self.tipo.id])
        payload = {
            'horario_abertura': '15:30',
            'horario_fechamento': '09:00'
        }
        response = self.client.post(
            url, data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.tipo.janela.refresh_from_db()
        self.assertEqual(self.tipo.janela.horario_fechamento.strftime('%H:%M'), '09:00')
