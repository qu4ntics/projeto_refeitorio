from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from administrativo.models import ConfigReserva, Presenca, Strike, TipoRefeicao, Turma
from reservas.models import Reserva

from .forms import RefeicaoForm
from .models import Prato, Refeicao


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


class PodeCancelarTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri',
            email='nutri@test.com',
            password='123',
            perfil='nutricionista',
        )
        self.tipo_almoco = TipoRefeicao.objects.get(nome='almoco')
        self.tipo_almoco.horario_inicio_consumo = time(12, 0)
        self.tipo_almoco.save(update_fields=['horario_inicio_consumo'])
        ConfigReserva.objects.create(
            abertura=time(0, 0),
            encerramento=time(23, 59),
            minutos_cancelamento=60,
            criado_por=self.nutri,
        )
        self.hoje = timezone.localdate()
        self.refeicao = Refeicao.objects.create(
            data=self.hoje,
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )

    def test_pode_cancelar_antes_do_limite(self):
        agora = timezone.make_aware(
            datetime.combine(self.hoje, time(10, 30)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            self.assertTrue(self.refeicao.pode_cancelar)

    def test_nao_pode_cancelar_apos_limite(self):
        agora = timezone.make_aware(
            datetime.combine(self.hoje, time(11, 30)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            self.assertFalse(self.refeicao.pode_cancelar)

    def test_fallback_usa_fechamento_da_janela_sem_horario_inicio(self):
        self.tipo_almoco.horario_inicio_consumo = None
        self.tipo_almoco.save(update_fields=['horario_inicio_consumo'])

        from administrativo.models import JanelaReserva
        JanelaReserva.objects.update_or_create(
            tipo_refeicao=self.tipo_almoco,
            defaults={
                'horario_abertura': time(0, 0),
                'horario_fechamento': time(9, 0),
            },
        )

        agora = timezone.make_aware(
            datetime.combine(self.hoje, time(8, 30)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            self.assertFalse(self.refeicao.pode_cancelar)


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


class JanelaEncerradaAguardandoRefeicaoTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_enc',
            email='nutri_enc@test.com',
            password='123',
            perfil='nutricionista',
        )
        self.tipo_almoco = TipoRefeicao.objects.get(nome='almoco')
        self.tipo_almoco.ativo = True
        self.tipo_almoco.horario_inicio_consumo = time(12, 0)
        self.tipo_almoco.save(update_fields=['ativo', 'horario_inicio_consumo'])
        from administrativo.models import JanelaReserva

        JanelaReserva.objects.update_or_create(
            tipo_refeicao=self.tipo_almoco,
            defaults={
                'horario_abertura': time(15, 0),
                'horario_fechamento': time(7, 0),
                'horario_fechamento_pre_reserva': time(6, 0),
            },
        )
        self.hoje = timezone.localdate()
        self.refeicao = Refeicao.objects.create(
            data=self.hoje,
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )

    def test_detecta_janela_encerrada_antes_da_refeicao(self):
        agora = timezone.make_aware(
            datetime.combine(self.hoje, time(10, 30)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            self.assertTrue(self.refeicao.janela_encerrada_aguardando_refeicao)
            self.assertIn('12:00', self.refeicao.aviso_reserva_encerrada)

    def test_homepage_exibe_aviso_reserva_encerrada(self):
        Usuario.objects.create_user(
            username='aluno_enc',
            email='aluno_enc@test.com',
            password='123',
            perfil='aluno',
        )
        agora = timezone.make_aware(
            datetime.combine(self.hoje, time(10, 30)),
            timezone.get_current_timezone(),
        )
        self.client.login(username='aluno_enc@test.com', password='123')
        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reservas encerradas')
        self.assertNotContains(response, 'RESERVAS ENCERRADAS')



class HomepageQueryCountTests(TestCase):
    """Trava regressão do N+1 nas propriedades de janela/vaga da Refeicao."""

    def setUp(self):
        from administrativo.models import JanelaReserva

        self.turma = Turma.objects.create(nome='1 Info', turno='matutino')
        self.aluno = Usuario.objects.create_user(
            username='aluno_qc', email='aluno_qc@test.com', password='123',
            perfil='aluno', turma=self.turma,
        )
        tipo = TipoRefeicao.objects.get(nome='almoco')
        tipo.ativo = True
        tipo.horario_inicio_consumo = time(12, 0)
        tipo.save(update_fields=['ativo', 'horario_inicio_consumo'])
        JanelaReserva.objects.update_or_create(
            tipo_refeicao=tipo,
            defaults={
                'horario_abertura': time(15, 0),
                'horario_fechamento': time(7, 0),
                'horario_fechamento_pre_reserva': time(6, 0),
            },
        )
        segunda = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        pratos = [
            Prato.objects.create(nome=f'Prato {i}', categoria='principal')
            for i in range(2)
        ]
        for offset in range(5):
            refeicao = Refeicao.objects.create(
                data=segunda + timedelta(days=offset),
                tipo='almoco',
                limite_vagas=50,
                exige_reserva=True,
            )
            refeicao.pratos.set(pratos)

    def test_homepage_nao_faz_n_mais_1_de_janela(self):
        # Teto de regressão: hoje ~51 queries para uma semana de 5 refeições. Um
        # N+1 de verdade (janela recalculada por acesso) passa de 100. A redução
        # completa (preload/annotate) fica para a rodada de refactor.
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        self.client.login(username='aluno_qc@test.com', password='123')
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('refeicoes:homepage'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx), 65,
            f'homepage fez {len(ctx)} queries (regressão de N+1?)',
        )


class ExcluirRefeicaoTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_del', email='nutri_del@test.com', password='123',
            perfil='nutricionista',
        )
        self.turma = Turma.objects.create(nome='1 Del', turno='matutino')
        self.aluno = Usuario.objects.create_user(
            username='aluno_del', email='aluno_del@test.com', password='123',
            perfil='aluno', turma=self.turma,
        )
        self.refeicao = Refeicao.objects.create(
            data=timezone.localdate() + timedelta(days=1),
            tipo='almoco', limite_vagas=10, exige_reserva=True,
        )
        self.client.login(username='nutri_del@test.com', password='123')
        self.url = reverse('refeicoes:nutricionista_deletar', args=[self.refeicao.id])

    def test_exclui_com_apenas_reservas_canceladas(self):
        Reserva.objects.create(
            aluno=self.aluno, refeicao=self.refeicao, status='cancelada',
            cancelado_em=timezone.now(),
        )
        self.client.post(self.url)
        self.assertFalse(Refeicao.objects.filter(pk=self.refeicao.pk).exists())

    def test_nao_exclui_com_reserva_ativa(self):
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        self.client.post(self.url)
        self.assertTrue(Refeicao.objects.filter(pk=self.refeicao.pk).exists())

    def test_exclui_sem_reservas(self):
        self.client.post(self.url)
        self.assertFalse(Refeicao.objects.filter(pk=self.refeicao.pk).exists())


class SincronizarReservasChamadaTests(TestCase):
    """Encerramento automático da chamada quando o horário da refeição acaba."""

    def setUp(self):
        self.turma = Turma.objects.create(nome='2 ano Info')
        self.aluno = Usuario.objects.create_user(
            username='sync@test.com', email='sync@test.com',
            password='123', perfil='aluno', turma=self.turma,
        )
        TipoRefeicao.objects.filter(nome='almoco').update(
            horario_inicio_consumo=time(11, 0), horario_fim_consumo=time(13, 0),
        )

    def _mock_agora(self, hora, minuto=0, dia=None):
        agora = timezone.make_aware(
            datetime.combine(dia or timezone.localdate(), time(hora, minuto)),
        )
        return patch('django.utils.timezone.localtime', return_value=agora)

    def _refeicao_com_reserva(self, data=None):
        refeicao = Refeicao.objects.create(
            data=data or timezone.localdate(), tipo='almoco',
            limite_vagas=10, exige_reserva=True,
        )
        Reserva.objects.create(aluno=self.aluno, refeicao=refeicao, status='ativa')
        return refeicao

    def test_encerra_sem_ninguem_ter_aberto_a_chamada(self):
        """Antes, uma chamada nunca aberta ficava pendente para sempre e o
        ausente escapava do strike."""
        refeicao = self._refeicao_com_reserva()

        with self._mock_agora(15, 0):
            call_command('sincronizar_reservas')

        refeicao.refresh_from_db()
        self.assertTrue(refeicao.chamada_finalizada)
        self.assertEqual(Strike.objects.filter(aluno=self.aluno).count(), 1)

    def test_encerra_sem_usuario_do_refeitorio_cadastrado(self):
        """O encerramento automático não tem funcionário por trás: a presença
        fica sem `confirmado_por` em vez de a chamada travar."""
        self.assertFalse(Usuario.objects.filter(perfil='refeitorio').exists())
        refeicao = self._refeicao_com_reserva()

        with self._mock_agora(15, 0):
            call_command('sincronizar_reservas')

        refeicao.refresh_from_db()
        self.assertTrue(refeicao.chamada_finalizada)
        presenca = Presenca.objects.get(reserva__refeicao=refeicao)
        self.assertIsNone(presenca.confirmado_por)
        self.assertFalse(presenca.compareceu)

    def test_nao_encerra_durante_o_horario(self):
        refeicao = self._refeicao_com_reserva()

        with self._mock_agora(12, 0):
            call_command('sincronizar_reservas')

        refeicao.refresh_from_db()
        self.assertFalse(refeicao.chamada_finalizada)
        self.assertEqual(Strike.objects.count(), 0)

    def test_recupera_refeicao_de_dia_anterior(self):
        """Se o cron ficar fora do ar, na volta ele fecha o que ficou para trás."""
        refeicao = self._refeicao_com_reserva(
            data=timezone.localdate() - timedelta(days=2),
        )

        call_command('sincronizar_reservas')

        refeicao.refresh_from_db()
        self.assertTrue(refeicao.chamada_finalizada)
        self.assertEqual(Strike.objects.filter(aluno=self.aluno).count(), 1)

    def test_nao_reaplica_strike_em_chamada_ja_encerrada(self):
        refeicao = self._refeicao_com_reserva(
            data=timezone.localdate() - timedelta(days=1),
        )

        call_command('sincronizar_reservas')
        call_command('sincronizar_reservas')

        self.assertEqual(Strike.objects.filter(aluno=self.aluno).count(), 1)


class RefeicoesDadosAtualizadosTests(TestCase):
    """Endpoint em lote que alimenta o polling das telas."""

    def setUp(self):
        self.turma = Turma.objects.create(nome='3 ano Info')
        self.aluno = Usuario.objects.create_user(
            username='aluno_api@test.com', email='aluno_api@test.com',
            password='123', perfil='aluno', turma=self.turma,
        )
        self.outro_aluno = Usuario.objects.create_user(
            username='outro_api@test.com', email='outro_api@test.com',
            password='123', perfil='aluno', turma=self.turma,
        )
        self.refeicao = Refeicao.objects.create(
            data=timezone.localdate(), tipo='almoco',
            limite_vagas=10, exige_reserva=True,
        )
        self.url = reverse('refeicoes:refeicoes_dados_atualizados')

    def _get(self, *refeicoes):
        ids = ','.join(str(r.id) for r in refeicoes)
        return self.client.get(self.url, {'ids': ids})

    def test_exige_login(self):
        self.assertEqual(self._get(self.refeicao).status_code, 302)

    def test_retorna_numeros_da_refeicao(self):
        self.client.login(username='aluno_api@test.com', password='123')
        dados = self._get(self.refeicao).json()['refeicoes'][str(self.refeicao.id)]

        self.assertEqual(dados['limite_vagas'], 10)
        self.assertEqual(dados['vagas_disponiveis'], 10)
        self.assertEqual(dados['reservas_ativas_count'], 0)

    def test_reflete_reserva_feita_por_outro_aluno(self):
        self.client.login(username='aluno_api@test.com', password='123')
        Reserva.objects.create(
            aluno=self.outro_aluno, refeicao=self.refeicao, status='ativa',
        )

        dados = self._get(self.refeicao).json()['refeicoes'][str(self.refeicao.id)]
        self.assertEqual(dados['reservas_ativas_count'], 1)
        self.assertEqual(dados['vagas_ocupadas'], 1)
        self.assertEqual(dados['vagas_disponiveis'], 9)

    def test_reservas_validas_incluem_concluidas(self):
        """O painel do refeitório conta ativas + concluídas; a chamada muda o
        status de ativa para concluída e o total não pode cair."""
        self.client.login(username='aluno_api@test.com', password='123')
        Reserva.objects.create(
            aluno=self.aluno, refeicao=self.refeicao, status='concluida',
        )
        Reserva.objects.create(
            aluno=self.outro_aluno, refeicao=self.refeicao, status='ativa',
        )

        dados = self._get(self.refeicao).json()['refeicoes'][str(self.refeicao.id)]
        self.assertEqual(dados['reservas_ativas_count'], 1)
        self.assertEqual(dados['reservas_validas_count'], 2)
        self.assertEqual(dados['presentes_count'], 1)

    def test_contagens_nao_inflam_com_reserva_e_pre_reserva_juntas(self):
        """As duas relações no mesmo JOIN inflariam as contagens sem distinct."""
        from reservas.models import PreReserva

        self.client.login(username='aluno_api@test.com', password='123')
        Reserva.objects.create(
            aluno=self.outro_aluno, refeicao=self.refeicao, status='ativa',
        )
        PreReserva.objects.create(
            aluno=self.aluno, refeicao=self.refeicao, status='pendente',
            expira_em=timezone.now() + timedelta(hours=1),
        )

        dados = self._get(self.refeicao).json()['refeicoes'][str(self.refeicao.id)]
        self.assertEqual(dados['reservas_ativas_count'], 1)
        # 10 - 1 reserva - 1 pré-reserva pendente
        self.assertEqual(dados['vagas_disponiveis'], 8)

    def test_varias_refeicoes_em_uma_resposta(self):
        self.client.login(username='aluno_api@test.com', password='123')
        outra = Refeicao.objects.create(
            data=timezone.localdate(), tipo='jantar',
            limite_vagas=5, exige_reserva=True,
        )

        refeicoes = self._get(self.refeicao, outra).json()['refeicoes']
        self.assertEqual(len(refeicoes), 2)
        self.assertEqual(refeicoes[str(outra.id)]['limite_vagas'], 5)

    def test_custo_em_queries_nao_cresce_com_o_numero_de_refeicoes(self):
        """O motivo de existir o endpoint em lote: uma requisição por refeição
        multiplicaria a carga pelo tamanho do cardápio."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.client.login(username='aluno_api@test.com', password='123')
        self._get(self.refeicao)  # aquece sessão/usuário

        with CaptureQueriesContext(connection) as uma:
            self._get(self.refeicao)

        extras = [
            Refeicao.objects.create(
                data=timezone.localdate() + timedelta(days=i), tipo='almoco',
                limite_vagas=10, exige_reserva=True,
            )
            for i in range(1, 8)
        ]
        with CaptureQueriesContext(connection) as oito:
            self._get(self.refeicao, *extras)

        self.assertEqual(len(oito), len(uma), 'consultas cresceram com o nº de refeições')

    def test_ids_vazio_retorna_dicionario_vazio(self):
        self.client.login(username='aluno_api@test.com', password='123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['refeicoes'], {})

    def test_id_invalido_retorna_400(self):
        self.client.login(username='aluno_api@test.com', password='123')
        response = self.client.get(self.url, {'ids': 'nao-e-uuid'})
        self.assertEqual(response.status_code, 400)

    def test_id_inexistente_e_ignorado(self):
        self.client.login(username='aluno_api@test.com', password='123')
        response = self.client.get(
            self.url, {'ids': '00000000-0000-0000-0000-000000000000'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['refeicoes'], {})

    def test_limite_de_refeicoes_por_consulta(self):
        self.client.login(username='aluno_api@test.com', password='123')
        ids = ','.join(str(self.refeicao.id) for _ in range(101))
        response = self.client.get(self.url, {'ids': ids})
        self.assertEqual(response.status_code, 400)




class OrdemCronologicaRefeicoesTests(TestCase):
    """Ordenar pelo campo `tipo` daria a ordem alfabética do código guardado
    (almoco, cafe, jantar, lanche_manha, lanche_tarde), e não a ordem em que as
    refeições acontecem no dia."""

    ORDEM_ESPERADA = ['cafe', 'lanche_manha', 'almoco', 'lanche_tarde', 'jantar']
    ROTULOS = ['Café', 'Lanche da Manhã', 'Almoço', 'Lanche da Tarde', 'Jantar']

    def setUp(self):
        self.turma = Turma.objects.create(nome='1 ano Info')
        self.aluno = Usuario.objects.create_user(
            username='aluno_ordem@test.com', email='aluno_ordem@test.com',
            password='123', perfil='aluno', turma=self.turma,
        )
        self.refeitorio = Usuario.objects.create_user(
            username='ref_ordem@test.com', email='ref_ordem@test.com',
            password='123', perfil='refeitorio',
        )

    def _criar_refeicoes(self, data):
        """Cria as cinco fora de ordem, para a ordenação ter o que corrigir."""
        for tipo in ['jantar', 'almoco', 'cafe', 'lanche_tarde', 'lanche_manha']:
            Refeicao.objects.create(
                data=data, tipo=tipo, limite_vagas=10, exige_reserva=True,
            )

    def _assert_em_ordem(self, html):
        posicoes = [html.index(rotulo) for rotulo in self.ROTULOS]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_queryset_da_semana_sai_em_ordem_cronologica(self):
        from refeicoes.views import _queryset_refeicoes_periodo

        data = timezone.localdate()
        self._criar_refeicoes(data)

        tipos = list(
            _queryset_refeicoes_periodo(data, data).values_list('tipo', flat=True)
        )
        self.assertEqual(tipos, self.ORDEM_ESPERADA)

    def test_homepage_do_aluno_exibe_em_ordem_cronologica(self):
        from refeicoes.views import _obter_semana

        # A data vem da mesma lógica da view: os painéis só cobrem segunda a
        # sexta, então fixar em "hoje" faria o teste quebrar no fim de semana.
        _, segunda, _ = _obter_semana()
        self._criar_refeicoes(segunda)

        self.client.login(username='aluno_ordem@test.com', password='123')
        html = self.client.get(reverse('refeicoes:homepage')).content.decode('utf-8')
        self._assert_em_ordem(html)

    def test_cardapio_da_nutricionista_exibe_em_ordem_cronologica(self):
        from refeicoes.views import _obter_semana

        _, segunda, _ = _obter_semana()
        self._criar_refeicoes(segunda)

        nutri = Usuario.objects.create_user(
            username='nutri_ordem@test.com', email='nutri_ordem@test.com',
            password='123', perfil='nutricionista',
        )
        self.client.force_login(nutri)
        html = self.client.get(
            reverse('refeicoes:cardapio_semana')
        ).content.decode('utf-8')
        self._assert_em_ordem(html)

    def test_painel_do_refeitorio_exibe_em_ordem_cronologica(self):
        self._criar_refeicoes(timezone.localdate())

        self.client.login(username='ref_ordem@test.com', password='123')
        html = self.client.get(
            reverse('administrativo:painel_refeitorio')
        ).content.decode('utf-8')
        self._assert_em_ordem(html)

    def test_ordem_acompanha_a_declaracao_dos_tipos(self):
        """ORDEM_TIPOS deriva de TIPOS: basta declarar um tipo novo na posição
        certa da lista para ele aparecer no lugar certo."""
        self.assertEqual(Refeicao.ORDEM_TIPOS, self.ORDEM_ESPERADA)
