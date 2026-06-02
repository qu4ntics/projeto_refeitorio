from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Refeicao


User = get_user_model()


class RefeicoesNutricionistaTest(TestCase):
    def setUp(self):
        self.nutri = User.objects.create_user(
            username='nutricionista',
            password='test1234',
            email='nutri@example.com',
            turma='1',
            perfil='nutricionista',
        )
        self.client.login(username='nutricionista', password='test1234')

    def test_acesso_lista_nutricionista(self):
        response = self.client.get(reverse('refeicoes:nutricionista_lista'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'refeicoes/nutricionista_lista.html')

    def test_criar_refeicao_com_sucesso(self):
        response = self.client.post(
            reverse('refeicoes:nutricionista_nova'),
            {
                'data': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'tipo': 'almoco',
                'descricao': 'Almoço teste',
                'limite_vagas': 20,
                'exige_reserva': True,
            },
        )
        self.assertRedirects(response, reverse('refeicoes:nutricionista_lista'))
        self.assertEqual(Refeicao.objects.count(), 1)
        refeicao = Refeicao.objects.first()
        self.assertEqual(refeicao.tipo, 'almoco')
        self.assertEqual(refeicao.limite_vagas, 20)

    def test_deletar_refeicao(self):
        refeicao = Refeicao.objects.create(
            data=(date.today() + timedelta(days=1)),
            tipo='almoco',
            descricao='Refeição para deletar',
            limite_vagas=10,
            exige_reserva=True,
        )
        response = self.client.post(
            reverse('refeicoes:nutricionista_deletar', args=[refeicao.pk])
        )
        self.assertRedirects(response, reverse('refeicoes:nutricionista_lista'))
        self.assertEqual(Refeicao.objects.count(), 0)

    def test_criar_refeicao_com_data_passada_falha(self):
        response = self.client.post(
            reverse('refeicoes:nutricionista_nova'),
            {
                'data': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'tipo': 'almoco',
                'descricao': 'Almoço passado',
                'limite_vagas': 10,
                'exige_reserva': True,
            },
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('data', form.errors)
        self.assertEqual(form.errors['data'], ['A data não pode ser anterior a hoje.'])
        self.assertEqual(Refeicao.objects.count(), 0)

    def test_acesso_sem_perfil_nutricionista_retorna_403(self):
        aluno = User.objects.create_user(
            username='aluno',
            password='test1234',
            email='aluno@example.com',
            turma='1',
            perfil='aluno',
        )
        self.client.login(username='aluno', password='test1234')
        response = self.client.get(reverse('refeicoes:nutricionista_lista'))
        self.assertEqual(response.status_code, 403)
