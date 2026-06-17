from datetime import date, time, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from accounts.models import Usuario
from refeicoes.models import Refeicao
from administrativo.models import ConfigReserva, JanelaReserva, TipoRefeicao, Turma
from .models import Reserva

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
        self.client.login(username='aluno_teste', password='password123')

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

    def test_validacao_aluno_bloqueado(self):
        """Validação 1: Aluno bloqueado não pode reservar."""
        self.aluno.bloqueado = True
        self.aluno.save()

        response = self.client.post(reverse('reservas:criar_reserva', args=[self.refeicao.id]))
        
        self.assertEqual(Reserva.objects.count(), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("bloqueada" in str(m).lower() for m in messages))

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
        """Regra 3.2: Bloquear cancelamento após o prazo limite (config.minutos_cancelamento)."""
        self.refeicao.data = timezone.localdate()
        self.refeicao.save()

        # Encerramento à meia-noite do dia da refeição; com 60 min de antecedência, o prazo já expirou.
        # Alteramos na Janela pois a view agora prioriza o tipo da refeição
        self.janela.horario_fechamento = time(0, 0, 0)
        self.janela.save()
        self.config.minutos_cancelamento = 60
        self.config.save()
        
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao, status='ativa')
        response = self.client.post(reverse('reservas:cancelar_reserva', args=[reserva.id]))
        
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'ativa') # Não deve mudar para cancelada
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
     