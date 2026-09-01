from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from administrativo.models import Presenca
from reservas.models import Reserva

from .horarios_refeicao import (
    fase_periodo_consumo,
    periodo_consumo_configurado,
    periodo_consumo_terminou,
    pode_reabrir_chamada,
)
from .strikes import aplicar_strike


class ChamadaError(ValidationError):
    pass


def _erro_fora_do_horario(refeicao, fase):
    """Mensagem para quem tenta mexer na chamada fora do período de consumo."""
    if fase == 'nao_configurado':
        return (
            'Horário de início e término da refeição não estão configurados. '
            'Solicite à nutricionista.'
        )
    if fase == 'outro_dia':
        return 'A presença só pode ser marcada no dia da refeição.'
    if fase == 'depois':
        return 'O horário da refeição já encerrou.'

    periodo = periodo_consumo_configurado(refeicao.tipo_refeicao)
    inicio = periodo[0].strftime('%H:%M') if periodo else None
    if inicio:
        return f'A refeição começa às {inicio}; a presença só pode ser marcada a partir daí.'
    return 'A refeição ainda não começou.'


def marcar_presenca(reserva, usuario_refeitorio, presente):
    refeicao = reserva.refeicao
    if reserva.status == 'cancelada':
        raise ChamadaError('Não é possível marcar presença em uma reserva cancelada.')
    if refeicao.chamada_finalizada:
        raise ChamadaError('Esta chamada já foi finalizada e não pode mais ser alterada.')

    fase = fase_periodo_consumo(refeicao)
    if fase != 'durante':
        raise ChamadaError(_erro_fora_do_horario(refeicao, fase))

    Presenca.objects.update_or_create(
        reserva=reserva,
        defaults={
            'compareceu': presente,
            'confirmado_por': usuario_refeitorio,
        },
    )
    reserva.status = 'concluida' if presente else 'ativa'
    reserva.save(update_fields=['status'])
    return reserva.status


def encerrar_chamada(refeicao, usuario_refeitorio):
    """
    Fecha a chamada e aplica strike em quem não foi marcado como presente.

    Chamada de dois lugares: automaticamente pelo cron quando o horário da
    refeição termina (`usuario_refeitorio=None`) e manualmente pelo refeitório,
    que pode encerrar antes da hora (ex.: a comida acabou).
    """
    if not refeicao.exige_reserva:
        raise ChamadaError('Esta refeição não exige reserva e não possui chamada.')
    if refeicao.chamada_finalizada:
        raise ChamadaError('A chamada desta refeição já foi encerrada.')

    fase = fase_periodo_consumo(refeicao)
    if fase != 'durante' and not periodo_consumo_terminou(refeicao):
        raise ChamadaError(_erro_fora_do_horario(refeicao, fase))

    resumo = {
        'presentes': 0,
        'ausentes': 0,
        'strikes_aplicados': 0,
        'bloqueios': [],
    }

    with transaction.atomic():
        refeicao_locked = type(refeicao).objects.select_for_update().get(pk=refeicao.pk)
        # Recheca com a linha travada: o encerramento também é disparado por
        # acesso às telas, então duas requisições podem chegar juntas aqui.
        if refeicao_locked.chamada_finalizada:
            raise ChamadaError('A chamada desta refeição já foi encerrada.')

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
                aplicar_strike(reserva.aluno, presenca)
                resumo['strikes_aplicados'] += 1
                reserva.aluno.refresh_from_db(fields=['bloqueado'])
                if not aluno_bloqueado_antes and reserva.aluno.bloqueado:
                    resumo['bloqueios'].append(reserva.aluno.get_full_name() or reserva.aluno.username)

            resumo['ausentes'] += 1

        refeicao_locked.chamada_finalizada = True
        refeicao_locked.save(update_fields=['chamada_finalizada'])

    refeicao.refresh_from_db()
    return resumo


def encerrar_chamadas_vencidas():
    """
    Encerra toda chamada cujo horário de consumo já terminou, aplicando os
    strikes dos ausentes. Retorna quantas foram encerradas.

    É idempotente e barata quando não há nada vencido, porque é chamada tanto
    pelo cron (`sincronizar_reservas`) quanto pelas telas do refeitório e da
    nutricionista. A redundância é proposital: sem ela, os strikes dependeriam
    de o cron estar configurado, e uma falha silenciosa de infraestrutura
    deixaria de penalizar ausências sem ninguém perceber.
    """
    from refeicoes.models import Refeicao

    pendentes = Refeicao.objects.filter(
        data__lte=timezone.localdate(),
        exige_reserva=True,
        chamada_finalizada=False,
    )

    encerradas = 0
    for refeicao in pendentes:
        if not periodo_consumo_terminou(refeicao):
            continue
        try:
            encerrar_chamada(refeicao, None)
            encerradas += 1
        except ChamadaError:
            # Outra requisição encerrou primeiro, ou a refeição não está em
            # condição de encerrar: seguir para a próxima.
            continue
    return encerradas


def reabrir_chamada(refeicao):
    """Reabre para correção: volta a valer o horário da refeição."""
    if not refeicao.exige_reserva:
        raise ChamadaError('Esta refeição não exige reserva e não possui chamada.')
    if not pode_reabrir_chamada(refeicao):
        raise ChamadaError(
            'A chamada só pode ser reaberta durante o horário da refeição.'
        )
    refeicao.chamada_finalizada = False
    refeicao.save(update_fields=['chamada_finalizada'])


def status_chamada_refeicao(refeicao):
    """
    A chamada não é aberta por ninguém: ela vale enquanto durar o horário de
    consumo da refeição. `chamada_finalizada` é o único estado persistido,
    porque encerrar aplica strikes e só pode acontecer uma vez.
    """
    if refeicao.chamada_finalizada:
        return 'encerrada'
    if fase_periodo_consumo(refeicao) == 'durante':
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
