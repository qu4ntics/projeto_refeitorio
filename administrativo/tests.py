import json
from datetime import timedelta, time
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from refeicoes.models import Refeicao
from reservas.models import Reserva
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
        janela = JanelaReserva.objects.get(tipo_refeicao=self.tipo)
        self.assertEqual(janela.horario_fechamento.strftime('%H:%M'), '09:00')


class ListaPresencaTests(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(nome='1º ano Informática', turno='matutino')
        self.aluno = Usuario.objects.create_user(
            username='aluno_teste', email='aluno@teste.com', password='password123',
            perfil='aluno', first_name='João', last_name='Silva', turma=self.turma
        )
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.refeicao = Refeicao.objects.create(
            data=self.amanha, tipo='almoco', limite_vagas=10, exige_reserva=True
        )

    def test_seguranca_aluno_nao_acessa_lista_presenca(self):
        """Segurança: Aluno tentando acessar lista de presença deve receber 403."""
        self.client.login(username='aluno_teste', password='password123')
        url = reverse('refeicoes:lista-presenca')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_seguranca_aluno_nao_deleta_refeicao(self):
        """Segurança: Aluno tentando deletar uma refeição deve receber 403."""
        self.client.login(username='aluno_teste', password='password123')
        url = reverse('refeicoes:nutricionista_deletar', args=[self.refeicao.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_lista_presenca_acesso_refeitorio(self):
        """Garante que o perfil 'refeitorio' acessa a lista e vê as reservas."""
        user_refeitorio = Usuario.objects.create_user(
            username='funcionario_ref', email='ref@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='funcionario_ref', password='123')

        refeicao_hoje = Refeicao.objects.create(
            data=timezone.localdate(), tipo='almoco', limite_vagas=10, exige_reserva=True
        )
        Reserva.objects.create(aluno=self.aluno, refeicao=refeicao_hoje, status='ativa')

        url = reverse('refeicoes:lista-presenca')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.aluno.first_name)
        self.assertContains(response, self.turma.nome)

    def test_lista_presenca_filtro_data(self):
        """Verifica se a lista filtra corretamente por data via GET."""
        user_refeitorio = Usuario.objects.create_user(
            username='funcionario_data', email='data@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='funcionario_data', password='123')

        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        
        url = reverse('reservas:lista_presenca')
        response = self.client.get(url, {'data': self.amanha.strftime('%Y-%m-%d')})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'João')

        response_hoje = self.client.get(url)
        self.assertNotContains(response_hoje, 'João')

    def test_lista_presenca_ordenacao_alfabetica(self):
        """Garante que os alunos aparecem em ordem alfabética na lista."""
        user_refeitorio = Usuario.objects.create_user(
            username='func_ordenacao', email='ord@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='func_ordenacao', password='123')

        aluno_b = Usuario.objects.create_user(username='beatriz', email='b@test.com', first_name='Beatriz', perfil='aluno', turma=self.turma)
        aluno_a = Usuario.objects.create_user(username='ana', email='a@test.com', first_name='Ana', perfil='aluno', turma=self.turma)
        
        refeicao_hoje = Refeicao.objects.create(data=timezone.localdate(), tipo='cafe', limite_vagas=5)
        Reserva.objects.create(aluno=aluno_b, refeicao=refeicao_hoje)
        Reserva.objects.create(aluno=aluno_a, refeicao=refeicao_hoje)

        url = reverse('reservas:lista_presenca')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        self.assertTrue(content.find('Ana') < content.find('Beatriz'))

    def test_lista_presenca_filtros_pesquisa(self):
        """Testa a busca por nome, turma e tipo de refeição com verificação case-insensitive."""
        user_refeitorio = Usuario.objects.create_user(
            username='func_busca', email='busca@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='func_busca', password='123')

        turma_info = Turma.objects.create(nome='Informática')
        aluno_marcos = Usuario.objects.create_user(
            username='marcos', email='m@test.com', first_name='Marcos', last_name='Oliveira', perfil='aluno', turma=turma_info
        )
        
        refeicao_almoco = Refeicao.objects.create(data=timezone.localdate(), tipo='almoco', limite_vagas=5)
        Reserva.objects.create(aluno=aluno_marcos, refeicao=refeicao_almoco)

        url = reverse('reservas:lista_presenca')

        # Busca por nome (Testando case-insensitivity: 'marcos', 'MARCOS', 'Marcos')
        for term in ['Marcos', 'marcos', 'MARCOS']:
            resp = self.client.get(url, {'search': term})
            self.assertContains(resp, 'Marcos', msg_prefix=f"Falha ao buscar termo: {term}")

        # Busca por turma
        resp = self.client.get(url, {'search': 'Informática'})
        self.assertContains(resp, 'Marcos')

        # Busca por tipo de refeição
        resp = self.client.get(url, {'search': 'Almoço'})
        self.assertContains(resp, 'Marcos')
        
        # Busca negativa
        resp = self.client.get(url, {'search': 'Jantar'})
        self.assertNotContains(resp, 'Marcos')

    def test_lista_presenca_exibe_canceladas(self):
        """Garante que alunos que cancelaram aparecem na lista com o status correto."""
        user_refeitorio = Usuario.objects.create_user(
            username='funcionario_cancel', email='cancel@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='funcionario_cancel', password='123')

        refeicao_hoje = Refeicao.objects.create(
            data=timezone.localdate(), tipo='almoco', limite_vagas=10, exige_reserva=True
        )
        Reserva.objects.create(aluno=self.aluno, refeicao=refeicao_hoje, status='cancelada', cancelado_em=timezone.now())

        url = reverse('refeicoes:lista-presenca')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelada")
        self.assertContains(response, self.aluno.first_name)

    def test_lista_presenca_filtro_turma_exclusao(self):
        """Verifica se a lista oculta corretamente alunos de outras turmas ao filtrar."""
        user_refeitorio = Usuario.objects.create_user(
            username='func_filtro_turma', email='exc@test.com', password='123', perfil='refeitorio'
        )
        self.client.login(username='func_filtro_turma', password='123')

        turma_a = Turma.objects.create(nome='Edificações')
        turma_b = Turma.objects.create(nome='Eletrotécnica')
        aluno_a = Usuario.objects.create_user(username='aluno_edif', email='alice@test.com', first_name='Alice', perfil='aluno', turma=turma_a)
        aluno_b = Usuario.objects.create_user(username='aluno_eletro', email='bruno@test.com', first_name='Bruno', perfil='aluno', turma=turma_b)

        refeicao = Refeicao.objects.create(data=timezone.localdate(), tipo='almoco', limite_vagas=10)
        Reserva.objects.create(aluno=aluno_a, refeicao=refeicao)
        Reserva.objects.create(aluno=aluno_b, refeicao=refeicao)

        url = reverse('reservas:lista_presenca')
        response = self.client.get(url, {'search': 'Edificações'})
        self.assertContains(response, 'Alice')
        self.assertNotContains(response, 'Bruno')
