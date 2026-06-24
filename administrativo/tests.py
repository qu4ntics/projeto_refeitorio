import json
from datetime import timedelta, time
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Usuario
from refeicoes.models import Refeicao
from reservas.models import Reserva
from .models import Turma, TipoRefeicao, JanelaReserva, Presenca, Strike


class AlunosBloqueadosTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_bloq',
            email='nutri_bloq@test.com',
            password='senha123',
            perfil='nutricionista',
        )
        self.refeitorio = Usuario.objects.create_user(
            username='ref_bloq',
            email='ref_bloq@test.com',
            password='123',
            perfil='refeitorio',
        )
        self.turma = Turma.objects.create(nome='2º Informática', turno='matutino')
        self.aluno_livre = Usuario.objects.create_user(
            username='aluno_livre',
            email='livre@test.com',
            password='123',
            perfil='aluno',
            first_name='Ana',
            last_name='Livre',
            turma=self.turma,
        )
        self.aluno_bloqueado = Usuario.objects.create_user(
            username='aluno_bloq',
            email='bloq@test.com',
            password='123',
            perfil='aluno',
            first_name='João',
            last_name='Bloqueado',
            turma=self.turma,
            bloqueado=True,
        )
        self._criar_strike(self.aluno_bloqueado, timezone.now() - timedelta(days=1))
        self._criar_strike(self.aluno_bloqueado)
        self.url_pagina = reverse('administrativo:alunos_bloqueados')
        self.url_api = reverse('administrativo:lista_alunos')

    def _criar_strike(self, aluno, aplicado_em=None):
        refeicao = Refeicao.objects.create(
            data=timezone.localdate(),
            tipo='almoco',
            limite_vagas=10,
            exige_reserva=True,
        )
        reserva = Reserva.objects.create(aluno=aluno, refeicao=refeicao, status='ativa')
        presenca = Presenca.objects.create(
            reserva=reserva,
            confirmado_por=self.refeitorio,
            compareceu=False,
        )
        strike = Strike(aluno=aluno, presenca=presenca)
        if aplicado_em:
            strike.aplicado_em = aplicado_em
            strike.expira_em = aplicado_em + timedelta(days=30)
        strike.save()
        return strike

    def test_nutricionista_acessa_pagina_bloqueados(self):
        self.client.login(username='nutri_bloq@test.com', password='senha123')
        response = self.client.get(self.url_pagina)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alunos Bloqueados')
        self.assertContains(response, 'BLOQUEADOS')

    def test_aluno_nao_acessa_pagina_bloqueados(self):
        self.client.login(username='livre@test.com', password='123')
        response = self.client.get(self.url_pagina)
        self.assertEqual(response.status_code, 403)

    def test_refeitorio_nao_acessa_pagina_bloqueados(self):
        self.client.login(username='ref_bloq@test.com', password='123')
        response = self.client.get(self.url_pagina)
        self.assertEqual(response.status_code, 403)

    def test_api_lista_somente_bloqueados_com_data(self):
        self.client.login(username='nutri_bloq@test.com', password='senha123')
        response = self.client.get(self.url_api, {'bloqueados': 'true'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        emails = [a['email'] for a in data['alunos']]
        self.assertIn('bloq@test.com', emails)
        self.assertNotIn('livre@test.com', emails)
        bloqueado = next(a for a in data['alunos'] if a['email'] == 'bloq@test.com')
        self.assertTrue(bloqueado['bloqueado'])
        self.assertIsNotNone(bloqueado['bloqueado_em'])


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
        self.client.login(username='nutri@test.com', password='senha123')

    def test_turmas_lista_redireciona_para_alunos(self):
        response = self.client.get(reverse('administrativo:turmas_lista'))
        self.assertRedirects(response, reverse('administrativo:alunos_turmas'))

    def test_aluno_nao_acessa_crud_turmas(self):
        aluno = Usuario.objects.create_user(
            username='aluno',
            email='aluno@test.com',
            password='senha123',
            perfil='aluno',
            turma=self.turma,
        )
        self.client.logout()
        self.client.login(username='aluno@test.com', password='senha123')
        response = self.client.get(reverse('administrativo:turmas_lista'))
        self.assertEqual(response.status_code, 403)

    def test_criar_turma(self):
        response = self.client.post(reverse('administrativo:turma_criar'), {
            'nome': 'Turma teste contraturno',
            'turno': 'noturno',
            'dias_contraturno': ['1', '3'],
            'ativo': True,
        })
        self.assertRedirects(response, reverse('administrativo:alunos_turmas'))
        turma = Turma.objects.get(nome='Turma teste contraturno')
        self.assertEqual(turma.dias_contraturno, [1, 3])

    def test_excluir_turma_sem_alunos(self):
        turma_vazia = Turma.objects.create(nome='Turma vazia', turno='matutino')
        response = self.client.post(reverse('administrativo:turma_excluir', args=[turma_vazia.id]))
        self.assertRedirects(response, reverse('administrativo:alunos_turmas'))
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
        self.assertRedirects(response, reverse('administrativo:alunos_turmas'))
        self.assertTrue(Turma.objects.filter(pk=self.turma.id).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('alunos vinculados' in str(m).lower() for m in messages))

    def test_lista_alunos_turma_inclui_metadados(self):
        url = reverse('administrativo:lista_alunos_turma', args=[self.turma.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['turma']['turno'], 'vespertino')
        self.assertEqual(data['turma']['dias_contraturno'], [4])
        self.assertEqual(len(data['dias_semana']), 7)

    def test_atualizar_contraturno_via_api(self):
        url = reverse('administrativo:turma_atualizar_contraturno', args=[self.turma.id])
        response = self.client.post(
            url,
            data=json.dumps({'dias_contraturno': [1, 3]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.turma.refresh_from_db()
        self.assertEqual(self.turma.dias_contraturno, [1, 3])

    def test_excluir_turma_redireciona_para_alunos(self):
        turma_vazia = Turma.objects.create(nome='Turma origem alunos', turno='matutino')
        response = self.client.post(
            reverse('administrativo:turma_excluir', args=[turma_vazia.id]),
            {'origem': 'alunos'},
        )
        self.assertRedirects(response, reverse('administrativo:alunos_turmas'))

    def test_lista_turmas_arquivadas_json(self):
        Turma.objects.create(nome='Turma inativa', turno='matutino', ativo=False)
        response = self.client.get(
            reverse('administrativo:lista_turmas_json'),
            {'arquivadas': '1'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['arquivadas'])
        nomes = [t['nome'] for t in data['turmas']]
        self.assertIn('Turma inativa', nomes)
        self.assertNotIn('2º ano Administração', nomes)

    def test_alunos_turma_inativa_acessivel(self):
        turma_inativa = Turma.objects.create(
            nome='Turma arquivada teste',
            turno='noturno',
            ativo=False,
        )
        response = self.client.get(
            reverse('administrativo:alunos_turma', args=[turma_inativa.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Turma arquivada teste')


class ConfiguracoesTipoRefeicaoTests(TestCase):
    def setUp(self):
        self.nutri = Usuario.objects.create_user(
            username='nutri_cfg',
            email='nutri_cfg@test.com',
            password='123',
            perfil='nutricionista',
        )
        self.client.login(username='nutri_cfg@test.com', password='123')

    def test_tipos_seed_existem(self):
        self.assertEqual(TipoRefeicao.objects.count(), 5)

    def test_salvar_horario_consumo(self):
        tipo = TipoRefeicao.objects.get(nome='almoco')
        response = self.client.post(reverse('administrativo:configuracoes'), {
            'acao': 'salvar_refeicoes',
            f'ativo_{tipo.id}': 'on',
            f'abertura_{tipo.id}': '15:00',
            f'encerramento_{tipo.id}': '07:00',
            f'horario_consumo_{tipo.id}': '12:30',
        })
        self.assertRedirects(response, reverse('administrativo:configuracoes'))
        tipo.refresh_from_db()
        self.assertEqual(tipo.horario_inicio_consumo.strftime('%H:%M'), '12:30')

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
        self.client.login(username='nutri_api@test.com', password='123')

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
        self.refeitorio = Usuario.objects.create_user(
            username='func_ref', email='ref@test.com', password='123', perfil='refeitorio'
        )
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.refeicao = Refeicao.objects.create(
            data=self.amanha, tipo='almoco', limite_vagas=10, exige_reserva=True
        )
        self.refeicao_hoje = Refeicao.objects.create(
            data=timezone.localdate(), tipo='almoco', limite_vagas=10, exige_reserva=True
        )

    def _login_refeitorio(self):
        self.client.login(username='ref@test.com', password='123')

    def _abrir_chamada(self, refeicao=None):
        refeicao = refeicao or self.refeicao_hoje
        return self.client.post(reverse('administrativo:abrir_chamada', args=[refeicao.id]))

    def test_seguranca_aluno_nao_acessa_chamada(self):
        self.client.login(username='aluno@teste.com', password='password123')
        url = reverse('refeicoes:chamada', args=[self.refeicao_hoje.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_seguranca_aluno_nao_deleta_refeicao(self):
        self.client.login(username='aluno@teste.com', password='password123')
        url = reverse('refeicoes:nutricionista_deletar', args=[self.refeicao.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_abrir_chamada_apenas_exige_reserva(self):
        self._login_refeitorio()
        refeicao_livre = Refeicao.objects.create(
            data=timezone.localdate(), tipo='cafe', limite_vagas=5, exige_reserva=False
        )
        response = self.client.post(reverse('administrativo:abrir_chamada', args=[refeicao_livre.id]))
        self.assertEqual(response.status_code, 404)

    def test_painel_refeitorio_lista_refeicoes_do_dia(self):
        self._login_refeitorio()
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        response = self.client.get(reverse('administrativo:painel_refeitorio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almoço')
        self.assertContains(response, 'Abrir chamada')

    def test_fluxo_chamada_marca_presenca_cria_presenca(self):
        from administrativo.models import Presenca

        self._login_refeitorio()
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()

        response = self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva.id]),
            data=json.dumps({'checked': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'concluida')
        self.assertTrue(Presenca.objects.filter(reserva=reserva, compareceu=True).exists())

    def test_desmarcar_presenca_remove_registro(self):
        from administrativo.models import Presenca

        self._login_refeitorio()
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()

        self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva.id]),
            data=json.dumps({'checked': True}),
            content_type='application/json',
        )
        response = self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva.id]),
            data=json.dumps({'checked': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'ativa')
        self.assertFalse(Presenca.objects.filter(reserva=reserva).exists())

    def test_encerrar_aplica_strike_apenas_ausentes(self):
        from administrativo.models import Presenca, Strike

        self._login_refeitorio()
        presente = Usuario.objects.create_user(
            username='presente', email='p@test.com', password='123',
            perfil='aluno', first_name='Ana', turma=self.turma,
        )
        ausente = Usuario.objects.create_user(
            username='ausente', email='a@test.com', password='123',
            perfil='aluno', first_name='Bruno', turma=self.turma,
        )
        reserva_p = Reserva.objects.create(aluno=presente, refeicao=self.refeicao_hoje, status='ativa')
        reserva_a = Reserva.objects.create(aluno=ausente, refeicao=self.refeicao_hoje, status='ativa')
        Reserva.objects.create(
            aluno=self.aluno, refeicao=self.refeicao_hoje, status='cancelada',
            cancelado_em=timezone.now(),
        )

        self._abrir_chamada()
        self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva_p.id]),
            data=json.dumps({'checked': True}),
            content_type='application/json',
        )

        response = self.client.post(
            reverse('administrativo:encerrar_chamada', args=[self.refeicao_hoje.id])
        )
        self.assertRedirects(response, reverse('refeicoes:chamada_resumo', args=[self.refeicao_hoje.id]))

        self.refeicao_hoje.refresh_from_db()
        self.assertTrue(self.refeicao_hoje.chamada_finalizada)
        self.assertFalse(self.refeicao_hoje.chamada_aberta)
        self.assertEqual(Strike.objects.count(), 1)
        strike = Strike.objects.get()
        self.assertEqual(strike.aluno, ausente)
        self.assertFalse(strike.presenca.compareceu)
        self.assertTrue(Presenca.objects.filter(reserva=reserva_p, compareceu=True).exists())

    def test_dois_strikes_bloqueiam_aluno(self):
        from administrativo.models import Strike

        self._login_refeitorio()
        aluno = Usuario.objects.create_user(
            username='faltoso', email='faltoso@test.com', password='123',
            perfil='aluno', first_name='Carlos', turma=self.turma,
        )
        refeicao1 = Refeicao.objects.create(
            data=timezone.localdate(), tipo='cafe', limite_vagas=5, exige_reserva=True,
        )
        refeicao2 = Refeicao.objects.create(
            data=timezone.localdate(), tipo='jantar', limite_vagas=5, exige_reserva=True,
        )
        Reserva.objects.create(aluno=aluno, refeicao=refeicao1, status='ativa')
        Reserva.objects.create(aluno=aluno, refeicao=refeicao2, status='ativa')

        self.client.post(reverse('administrativo:abrir_chamada', args=[refeicao1.id]))
        self.client.post(reverse('administrativo:encerrar_chamada', args=[refeicao1.id]))
        self.client.post(reverse('administrativo:abrir_chamada', args=[refeicao2.id]))
        self.client.post(reverse('administrativo:encerrar_chamada', args=[refeicao2.id]))

        aluno.refresh_from_db()
        self.assertTrue(aluno.bloqueado)
        self.assertEqual(Strike.objects.filter(aluno=aluno).count(), 2)

    def test_chamada_exibe_contador_presentes(self):
        self._login_refeitorio()
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()
        response = self.client.get(reverse('refeicoes:chamada', args=[self.refeicao_hoje.id]))
        self.assertContains(response, '0')
        self.assertContains(response, '1')
        self.assertContains(response, 'presentes')

    def test_resumo_pos_encerramento(self):
        self._login_refeitorio()
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()
        self.client.post(reverse('administrativo:encerrar_chamada', args=[self.refeicao_hoje.id]))
        response = self.client.get(reverse('refeicoes:chamada_resumo', args=[self.refeicao_hoje.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ausentes')
        self.assertContains(response, 'Strikes aplicados')

    def test_reabrir_nao_remove_strikes(self):
        from administrativo.models import Strike

        self._login_refeitorio()
        Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()
        self.client.post(reverse('administrativo:encerrar_chamada', args=[self.refeicao_hoje.id]))
        self.assertEqual(Strike.objects.count(), 1)

        self.client.post(reverse('administrativo:reabrir_chamada', args=[self.refeicao_hoje.id]))
        self.refeicao_hoje.refresh_from_db()
        self.assertTrue(self.refeicao_hoje.chamada_aberta)
        self.assertFalse(self.refeicao_hoje.chamada_finalizada)
        self.assertEqual(Strike.objects.count(), 1)

    def test_atualizar_presenca_bloqueia_sem_chamada_aberta(self):
        self._login_refeitorio()
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        response = self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva.id]),
            data=json.dumps({'checked': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'ativa')

    def test_atualizar_presenca_bloqueia_chamada_finalizada(self):
        self._login_refeitorio()
        reserva = Reserva.objects.create(aluno=self.aluno, refeicao=self.refeicao_hoje, status='ativa')
        self._abrir_chamada()
        self.client.post(reverse('administrativo:encerrar_chamada', args=[self.refeicao_hoje.id]))
        response = self.client.post(
            reverse('administrativo:atualizar_status_reserva', args=[reserva.id]),
            data=json.dumps({'checked': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_chamada_ordenacao_alfabetica(self):
        self._login_refeitorio()
        aluno_b = Usuario.objects.create_user(
            username='beatriz', email='b@test.com', first_name='Beatriz',
            perfil='aluno', turma=self.turma,
        )
        aluno_a = Usuario.objects.create_user(
            username='ana', email='a@test.com', first_name='Ana',
            perfil='aluno', turma=self.turma,
        )
        Reserva.objects.create(aluno=aluno_b, refeicao=self.refeicao_hoje)
        Reserva.objects.create(aluno=aluno_a, refeicao=self.refeicao_hoje)
        self._abrir_chamada()
        response = self.client.get(reverse('refeicoes:chamada', args=[self.refeicao_hoje.id]))
        content = response.content.decode('utf-8')
        self.assertTrue(content.find('Ana') < content.find('Beatriz'))

    def test_chamada_filtros_pesquisa(self):
        self._login_refeitorio()
        turma_info = Turma.objects.create(nome='Informática')
        aluno_marcos = Usuario.objects.create_user(
            username='marcos', email='m@test.com', first_name='Marcos', last_name='Oliveira',
            perfil='aluno', turma=turma_info,
        )
        Reserva.objects.create(aluno=aluno_marcos, refeicao=self.refeicao_hoje)
        self._abrir_chamada()
        url = reverse('refeicoes:chamada', args=[self.refeicao_hoje.id])

        for term in ['Marcos', 'marcos', 'MARCOS']:
            resp = self.client.get(url, {'search': term})
            self.assertContains(resp, 'Marcos', msg_prefix=f"Falha ao buscar termo: {term}")

        resp = self.client.get(url, {'search': 'Informática'})
        self.assertContains(resp, 'Marcos')

        resp = self.client.get(url, {'search': 'Inexistente'})
        self.assertNotContains(resp, 'Marcos')

    def test_chamada_exibe_canceladas(self):
        self._login_refeitorio()
        Reserva.objects.create(
            aluno=self.aluno, refeicao=self.refeicao_hoje,
            status='cancelada', cancelado_em=timezone.now(),
        )
        self._abrir_chamada()
        response = self.client.get(reverse('refeicoes:chamada', args=[self.refeicao_hoje.id]))
        self.assertContains(response, 'Cancelada')
        self.assertContains(response, self.aluno.first_name)

    def test_lista_presenca_redireciona_para_painel(self):
        self._login_refeitorio()
        response = self.client.get(reverse('refeicoes:lista-presenca'))
        self.assertRedirects(response, reverse('administrativo:painel_refeitorio'))
