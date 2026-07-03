from django.core.exceptions import ValidationError
from django.db import transaction

from administrativo.models import Presenca, Strike
from reservas.models import Reserva

from .horarios_refeicao import pode_abrir_chamada, pode_reabrir_chamada


class ChamadaError(ValidationError):
    pass


def abrir_chamada(refeicao):
    if not refeicao.exige_reserva:
        raise ChamadaError('Esta refeição não exige reserva e não possui chamada.')
    if refeicao.chamada_finalizada:
        raise ChamadaError('A chamada desta refeição já foi encerrada.')
    ok, mensagem = pode_abrir_chamada(refeicao)
    if not ok:
        raise ChamadaError(mensagem)
    refeicao.chamada_aberta = True
    refeicao.save(update_fields=['chamada_aberta'])


def marcar_presenca(reserva, usuario_refeitorio, presente):
    refeicao = reserva.refeicao
    if reserva.status == 'cancelada':
        raise ChamadaError('Não é possível marcar presença em uma reserva cancelada.')
    if refeicao.chamada_finalizada:
        raise ChamadaError('Esta chamada já foi finalizada e não pode mais ser alterada.')
    if not refeicao.chamada_aberta:
        raise ChamadaError('A chamada desta refeição ainda não foi aberta.')

    if presente:
        Presenca.objects.update_or_create(
            reserva=reserva,
            defaults={
                'compareceu': True,
                'confirmado_por': usuario_refeitorio,
            },
        )
        reserva.status = 'concluida'
    else:
        Presenca.objects.filter(reserva=reserva).delete()
        reserva.status = 'ativa'
    reserva.save(update_fields=['status'])
    return reserva.status


def encerrar_chamada(refeicao, usuario_refeitorio):
    if not refeicao.exige_reserva:
        raise ChamadaError('Esta refeição não exige reserva e não possui chamada.')
    if refeicao.chamada_finalizada:
        raise ChamadaError('A chamada desta refeição já foi encerrada.')
    if not refeicao.chamada_aberta:
        raise ChamadaError('A chamada desta refeição ainda não foi aberta.')

    resumo = {
        'presentes': 0,
        'ausentes': 0,
        'strikes_aplicados': 0,
        'bloqueios': [],
    }

    with transaction.atomic():
        refeicao_locked = type(refeicao).objects.select_for_update().get(pk=refeicao.pk)
        reservas = (
            Reserva.objects.select_for_update()
            .filter(refeicao=refeicao_locked)
            .exclude(status='cancelada')
        )

        for reserva in reservas:
            if reserva.status == 'concluida':
                resumo['presentes'] += 1
                continue

            presenca, _ = Presenca.objects.get_or_create(
                reserva=reserva,
                defaults={
                    'compareceu': False,
                    'confirmado_por': usuario_refeitorio,
                },
            )
            if not presenca.compareceu:
                presenca.compareceu = False
                presenca.confirmado_por = usuario_refeitorio
                presenca.save(update_fields=['compareceu', 'confirmado_por'])

            if not hasattr(presenca, 'strike'):
                aluno_bloqueado_antes = reserva.aluno.bloqueado
                Strike.objects.create(aluno=reserva.aluno, presenca=presenca)
                resumo['strikes_aplicados'] += 1
                reserva.aluno.refresh_from_db(fields=['bloqueado'])
                if not aluno_bloqueado_antes and reserva.aluno.bloqueado:
                    resumo['bloqueios'].append(reserva.aluno.get_full_name() or reserva.aluno.username)

            resumo['ausentes'] += 1

        refeicao_locked.chamada_aberta = False
        refeicao_locked.chamada_finalizada = True
        refeicao_locked.save(update_fields=['chamada_aberta', 'chamada_finalizada'])

    refeicao.refresh_from_db()
    return resumo


def reabrir_chamada(refeicao):
    if not refeicao.exige_reserva:
        raise ChamadaError('Esta refeição não exige reserva e não possui chamada.')
    if not pode_reabrir_chamada(refeicao):
        raise ChamadaError(
            'A chamada só pode ser reaberta no dia da refeição.'
        )
    refeicao.chamada_aberta = True
    refeicao.chamada_finalizada = False
    refeicao.save(update_fields=['chamada_aberta', 'chamada_finalizada'])


def status_chamada_refeicao(refeicao):
    if refeicao.chamada_finalizada:
        return 'encerrada'
    if refeicao.chamada_aberta:
        return 'em_andamento'
    return 'fechada'


def estado_aluno_chamada(reserva, refeicao):
    if reserva.status == 'cancelada':
        return 'cancelada'
    if reserva.status == 'concluida':
        return 'presente'
    if refeicao.chamada_finalizada:
        return 'ausente'
    return 'pendente'
