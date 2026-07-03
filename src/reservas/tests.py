from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from accounts.models import Usuario
from refeicoes.models import Refeicao
from administrativo.models import ConfigReserva, JanelaReserva, Notificacao, TipoRefeicao, Turma
from .models import PreReserva, Reserva
from .services.pre_reserva import (
    PreReservaError,
    confirmar_pre_reserva,
    expirar_pendentes,
    rejeitar_pre_reserva,
)

class ReservaViewTests(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(
            nome='1º ano Informática',
            turno='matutino',
        )
        self.aluno = Usuario.objects.create_user(
            username='aluno_teste',
            email='aluno@teste.com',
            password='password123',
            perfil='aluno',
            first_name='João',
            last_name='Silva',
            bloqueado=False,
            turma=self.turma,
        )
        self.client.login(username='aluno@teste.com', password='password123')

        # Criar uma refeição padrão para amanhã (para cair dentro da janela de reserva)
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.refeicao = Refeicao.objects.create(
            data=self.amanha,
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True
        )

        self.tipo_almoco = TipoRefeicao.objects.get(nome='almoco')
        self.tipo_almoco.ativo = True
        self.tipo_almoco.save(update_fields=['ativo'])
        self.janela, _ = JanelaReserva.objects.get_or_create(
            tipo_refeicao=self.tipo_almoco,
            defaults={
                'horario_abertura': time(0, 0),
                'horario_fechamento': time(11, 0),
            },
        )
        # Garantimos que para os testes de sucesso, o "agora" esteja dentro da janela.
        
        # Criar nutricionista para fins de auditoria se necessário
        self.nutri = Usuario.objects.create_user(
                username='nutri',
                email='nutri@teste.com',
                password='123',
                perfil='nutricionista'
        )

        # Criar Configuração Global para fallback e cancelamento
        self.config = ConfigReserva.objects.create(
            abertura=time(0, 0),
            encerramento=time(23, 59),
            minutos_cancelamento=60,
            criado_por=self.nutri
        )

    def test_reserva_sucesso(self):
        """Garante que uma reserva válida é criada com sucesso."""
        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertRedirects(response, reverse('refeicoes:homepage'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("sucesso" in str(m).lower() for m in messages))

    def test_homepage_exibe_almoco_hoje_em_destaque(self):
        hoje = timezone.localdate()
        refeicao_hoje = Refeicao.objects.create(
            data=hoje,
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )
        agora = timezone.make_aware(
            datetime.combine(hoje, time(10, 0)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almoço de hoje')
        url_reserva = reverse('reservas:criar_reserva', args=[refeicao_hoje.id])
        self.assertEqual(response.content.decode('utf-8').count(url_reserva), 1)

        outra_semana = (hoje + timedelta(days=14)).strftime('%Y-%m-%d')
        with patch('django.utils.timezone.localtime', return_value=agora):
            response_outra = self.client.get(reverse('refeicoes:homepage'), {'data': outra_semana})
        self.assertContains(response_outra, 'Almoço de hoje')

    def test_homepage_apos_almoco_mostra_amanha_desabilitado(self):
        hoje = timezone.localdate()
        Refeicao.objects.create(
            data=hoje,
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )
        refeicao_amanha = self.refeicao
        self.janela.horario_abertura = time(15, 0)
        self.janela.horario_fechamento = time(11, 0)
        self.janela.save()

        agora = timezone.make_aware(
            datetime.combine(hoje, time(13, 0)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))

        self.assertContains(response, 'Almoço de amanhã')
        self.assertContains(response, 'Reservas abrem em')
        self.assertContains(response, 'disabled')
        url_reserva = reverse('reservas:criar_reserva', args=[refeicao_amanha.id])
        self.assertEqual(response.content.decode('utf-8').count(url_reserva), 0)

    def test_homepage_amanha_habilita_reserva_na_janela(self):
        hoje = timezone.localdate()
        refeicao_amanha = self.refeicao
        self.janela.horario_abertura = time(15, 0)
        self.janela.horario_fechamento = time(11, 0)
        self.janela.save()

        agora = timezone.make_aware(
            datetime.combine(hoje, time(16, 0)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))

        self.assertContains(response, 'Almoço de amanhã')
        self.assertNotContains(response, 'Reservas abrem em')
        url_reserva = reverse('reservas:criar_reserva', args=[refeicao_amanha.id])
        self.assertEqual(response.content.decode('utf-8').count(url_reserva), 1)

    def test_validacao_aluno_bloqueado(self):
        """Validação 1: Aluno bloqueado não pode reservar."""
        self.aluno.bloqueado = True
        self.aluno.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("bloqueada" in str(m).lower() for m in messages))

    def test_homepage_exibe_banner_quando_bloqueado(self):
        self.aluno.bloqueado = True
        self.aluno.save()

        hoje = timezone.localdate()
        agora = timezone.make_aware(
            datetime.combine(hoje, time(16, 0)),
            timezone.get_current_timezone(),
        )
        self.janela.horario_abertura = time(15, 0)
        self.janela.horario_fechamento = time(11, 0)
        self.janela.save()

        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))

        self.assertContains(response, 'Conta bloqueada')
        self.assertContains(response, 'reserve-btn--blocked')
        self.assertContains(response, 'BLOQUEADO')
        url_reserva = reverse('reservas:criar_reserva', args=[self.refeicao.id])
        self.assertEqual(response.content.decode('utf-8').count(url_reserva), 0)

    def test_homepage_sem_banner_quando_ativo(self):
        hoje = timezone.localdate()
        agora = timezone.make_aware(
            datetime.combine(hoje, time(16, 0)),
            timezone.get_current_timezone(),
        )
        self.janela.horario_abertura = time(15, 0)
        self.janela.horario_fechamento = time(11, 0)
        self.janela.save()

        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.get(reverse('refeicoes:homepage'))

        self.assertNotContains(response, 'Conta bloqueada')
        self.assertNotContains(response, 'reserve-btn--blocked')
        url_reserva = reverse('reservas:criar_reserva', args=[self.refeicao.id])
        self.assertEqual(response.content.decode('utf-8').count(url_reserva), 1)

    def test_validacao_refeicao_sem_reserva(self):
        """Validação 2: Refeição que não exige reserva não gera objeto Reserva."""
        self.refeicao.exige_reserva = False
        self.refeicao.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("apenas informativa" in str(m).lower() for m in messages))

    def test_validacao_janela_fechada(self):
        """Validação 3: Barrar reserva fora do horário (Simulando encerramento no passado)."""
        # Para garantir que falhe, colocamos a refeição para HOJE e o encerramento no início do dia
        self.refeicao.data = timezone.localdate()
        self.refeicao.save()

        self.janela.horario_abertura = time(0, 0)
        self.janela.horario_fechamento = time(0, 1)
        self.janela.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("encerrada" in str(m).lower() for m in messages))

    def test_validacao_vagas_esgotadas(self):
        """Validação 4: Barrar reserva se não houver mais vagas."""
        self.refeicao.limite_vagas = 0
        self.refeicao.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("esgotadas" in str(m).lower() for m in messages))

    def test_validacao_reserva_duplicada(self):
        """Validação 5: Aluno não pode reservar a mesma refeição duas vezes."""
        # Cria a primeira reserva
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        
        # Tenta criar a segunda via POST
        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        # Deve continuar existindo apenas 1 reserva
        self.assertEqual(Reserva.objects.filter(aluno=self.aluno, refeicao=self.refeicao).count(), 1)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("já possui uma reserva ativa" in str(m).lower() for m in messages))

    def test_cancelamento_sucesso(self):
        """Garante que o aluno pode cancelar sua própria reserva dentro do prazo."""
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        
        response = self.client.post(reverse('reservas:cancelar_reserva', args=[reserva.id]))
        
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')
        self.assertIsNotNone(reserva.cancelado_em)
        self.assertRedirects(response, reverse('refeicoes:homepage'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("cancelada com sucesso" in str(m).lower() for m in messages))

    def test_cancelamento_fora_do_prazo(self):
        """Regra 3.2: Bloquear cancelamento após o prazo limite (minutos antes do início da refeição)."""
        hoje = timezone.localdate()
        self.refeicao.data = hoje
        self.refeicao.save()

        self.tipo_almoco.horario_inicio_consumo = time(12, 0)
        self.tipo_almoco.save(update_fields=['horario_inicio_consumo'])
        self.config.minutos_cancelamento = 60
        self.config.save()

        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        agora = timezone.make_aware(
            datetime.combine(hoje, time(11, 30)),
            timezone.get_current_timezone(),
        )
        with patch('django.utils.timezone.localtime', return_value=agora):
            response = self.client.post(reverse('reservas:cancelar_reserva', args=[reserva.id]))

        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'ativa')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("prazo para cancelamento" in str(m).lower() for m in messages))

    def test_validacao_antecedencia_excessiva(self):
        """Validação: Barrar reserva com antecedência excessiva (ex: reservar sexta na quarta)."""
        # Refeição para depois de amanhã (fora da janela D-1)
        depois_de_amanha = timezone.localdate() + timedelta(days=2)
        self.refeicao.data = depois_de_amanha
        self.refeicao.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("abrem em" in str(m).lower() for m in messages))

    def test_validacao_data_passada(self):
        """Validação: Barrar reserva para uma data que já passou."""
        # Força uma data no passado (ontem)
        ontem = timezone.localdate() - timedelta(days=1)
        self.refeicao.data = ontem
        self.refeicao.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("que já passaram" in str(m).lower() for m in messages))

    def test_cancelamento_reserva_alheia(self):
        """Segurança: Um aluno não pode cancelar a reserva de outro (deve retornar 404)."""
        outro_aluno = Usuario.objects.create_user(
            username='outro_aluno',
            email='outro@teste.com',
            password='123',
            perfil='aluno',
            turma=self.turma,
        )
        reserva_alheia = Reserva.objects.create(aluno=outro_aluno, refeicao=self.refeicao, status='ativa')
        
        response = self.client.post(reverse('reservas:cancelar_reserva', args=[reserva_alheia.id]))
        
        self.assertEqual(response.status_code, 404)

    def test_integridade_reserva_refeicao_inexistente(self):
        """Integridade: Tentar reservar um UUID que não existe deve retornar 404."""
        import uuid
        url = reverse('reservas:criar_reserva', args=[uuid.uuid4()])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class PreReservaTests(TestCase):
    def setUp(self):
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.weekday_amanha = self.amanha.weekday()

        self.turma = Turma.objects.create(
            nome='1º ano Informática',
            turno='matutino',
            dias_contraturno=[self.weekday_amanha],
        )
        self.aluno = Usuario.objects.create_user(
            username='aluno_ct',
            email='ct@teste.com',
            password='password123',
            perfil='aluno',
            first_name='Maria',
            turma=self.turma,
        )
        self.outro_aluno = Usuario.objects.create_user(
            username='outro_ct',
            email='outro_ct@teste.com',
            password='password123',
            perfil='aluno',
            turma=self.turma,
        )
        self.client.login(username='ct@teste.com', password='password123')

        self.tipo_almoco = TipoRefeicao.objects.get(nome='almoco')
        self.tipo_almoco.ativo = True
        self.tipo_almoco.save(update_fields=['ativo'])
        self.janela, _ = JanelaReserva.objects.get_or_create(
            tipo_refeicao=self.tipo_almoco,
            defaults={
                'horario_abertura': time(15, 0),
                'horario_fechamento': time(11, 0),
            },
        )
        self.nutri = Usuario.objects.create_user(
            username='nutri_ct',
            email='nutri_ct@teste.com',
            password='123',
            perfil='nutricionista',
        )
        self.config = ConfigReserva.objects.create(
            abertura=time(15, 0),
            encerramento=time(23, 59),
            minutos_cancelamento=60,
            criado_por=self.nutri,
        )

    def _criar_refeicao(self, **kwargs):
        defaults = {
            'data': self.amanha,
            'tipo': 'almoco',
            'limite_vagas': 10,
            'exige_reserva': True,
        }
        defaults.update(kwargs)
        return Refeicao.objects.create(**defaults)

    def _criar_pre_reserva_pendente(self, refeicao=None, aluno=None, expira_em=None):
        if refeicao is None:
            refeicao = self._criar_refeicao()
        aluno = aluno or self.aluno
        pre = PreReserva.objects.get(refeicao=refeicao, aluno=aluno)
        pre.status = 'pendente'
        pre.expira_em = expira_em or timezone.now() + timedelta(hours=2)
        pre.save(update_fields=['status', 'expira_em'])
        return pre

    def test_signal_cria_pre_reservas_para_contraturno(self):
        refeicao = self._criar_refeicao()
        self.assertEqual(PreReserva.objects.filter(refeicao=refeicao, aluno=self.aluno).count(), 1)
        self.assertTrue(
            Notificacao.objects.filter(usuario=self.aluno, titulo='Pré-reserva de contra-turno').exists()
        )

    def test_signal_ignora_turma_sem_contraturno_no_dia(self):
        self.turma.dias_contraturno = []
        self.turma.save(update_fields=['dias_contraturno'])
        refeicao = self._criar_refeicao()
        self.assertEqual(PreReserva.objects.filter(refeicao=refeicao).count(), 0)

    def test_vagas_disponiveis_conta_pre_reservas_pendentes(self):
        refeicao = self._criar_refeicao(limite_vagas=5)
        pendentes = refeicao.pre_reservas.filter(status='pendente').count()
        self.assertGreater(pendentes, 0)
        self.assertEqual(refeicao.vagas_disponiveis, 5 - pendentes)

    def test_confirmar_pre_reserva_cria_reserva(self):
        pre = self._criar_pre_reserva_pendente()
        confirmar_pre_reserva(pre.id, self.aluno)
        pre.refresh_from_db()
        self.assertEqual(pre.status, 'confirmada')
        self.assertTrue(
            Reserva.objects.filter(aluno=self.aluno, refeicao=pre.refeicao, status='ativa').exists()
        )

    def test_confirmar_pre_reserva_expirada(self):
        pre = self._criar_pre_reserva_pendente(expira_em=timezone.now() - timedelta(hours=1))
        with self.assertRaises(PreReservaError):
            confirmar_pre_reserva(pre.id, self.aluno)

    def test_confirmar_pre_reserva_de_outro_aluno(self):
        pre = self._criar_pre_reserva_pendente()
        with self.assertRaises(PreReservaError):
            confirmar_pre_reserva(pre.id, self.outro_aluno)

    def test_confirmar_sem_vaga_disponivel(self):
        turma_solo = Turma.objects.create(
            nome='Solo CT 2',
            turno='matutino',
            dias_contraturno=[self.weekday_amanha],
        )
        self.aluno.turma = turma_solo
        self.aluno.save(update_fields=['turma'])
        refeicao = self._criar_refeicao(limite_vagas=1)
        Reserva.objects.create(aluno=self.outro_aluno, refeicao=refeicao, status='ativa')
        pre = PreReserva.objects.get(refeicao=refeicao, aluno=self.aluno)
        pre.expira_em = timezone.now() + timedelta(hours=2)
        pre.save(update_fields=['expira_em'])
        with self.assertRaises(PreReservaError):
            confirmar_pre_reserva(pre.id, self.aluno)

    def test_rejeitar_pre_reserva_libera_vaga(self):
        turma_solo = Turma.objects.create(
            nome='Solo CT',
            turno='matutino',
            dias_contraturno=[self.weekday_amanha],
        )
        self.aluno.turma = turma_solo
        self.aluno.save(update_fields=['turma'])
        self.outro_aluno.turma = Turma.objects.create(
            nome='Sem CT',
            turno='vespertino',
            dias_contraturno=[],
        )
        self.outro_aluno.save(update_fields=['turma'])
        refeicao = self._criar_refeicao(limite_vagas=1)
        pre = PreReserva.objects.get(refeicao=refeicao, aluno=self.aluno)
        self.assertEqual(refeicao.vagas_disponiveis, 0)
        rejeitar_pre_reserva(pre.id, self.aluno)
        pre.refresh_from_db()
        refeicao.refresh_from_db()
        self.assertEqual(pre.status, 'rejeitada')
        self.assertEqual(refeicao.vagas_disponiveis, 1)

    def test_expirar_pendentes(self):
        pre = self._criar_pre_reserva_pendente(expira_em=timezone.now() - timedelta(minutes=5))
        expirar_pendentes(pre.refeicao)
        pre.refresh_from_db()
        self.assertEqual(pre.status, 'expirada')

    def test_homepage_exibe_banner_pre_reserva(self):
        pre = self._criar_pre_reserva_pendente()
        response = self.client.get(reverse('refeicoes:homepage'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pré-reserva de contra-turno')
        self.assertContains(response, 'CONFIRMAR')
        self.assertContains(response, 'REJEITAR')

    def test_view_confirmar_pre_reserva(self):
        pre = self._criar_pre_reserva_pendente()
        response = self.client.post(reverse('reservas:confirmar_pre_reserva', args=[pre.id]))
        self.assertRedirects(response, reverse('refeicoes:homepage'))
        pre.refresh_from_db()
        self.assertEqual(pre.status, 'confirmada')

    def test_view_rejeitar_pre_reserva(self):
        pre = self._criar_pre_reserva_pendente()
        response = self.client.post(reverse('reservas:rejeitar_pre_reserva', args=[pre.id]))
        self.assertRedirects(response, reverse('refeicoes:homepage'))
        pre.refresh_from_db()
        self.assertEqual(pre.status, 'rejeitada')