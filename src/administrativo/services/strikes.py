"""Aplicação de strike com seus efeitos: notificação e bloqueio automático.

Antes essa lógica vivia em ``Strike.save()`` — rodava em qualquer save (inclusive
no-op) e era difícil de testar. Agora é uma função explícita, chamada por quem
realmente aplica um strike (encerramento de chamada, dados de teste).
"""

from datetime import timedelta

from django.utils import timezone

from administrativo.models import Notificacao, Strike

LIMITE_BLOQUEIO = 2


def aplicar_strike(aluno, presenca, *, aplicado_em=None):
    """Cria o strike, notifica o aluno e bloqueia a conta se atingir o limite.

    Retorna o ``Strike`` criado.
    """
    strike = Strike(aluno=aluno, presenca=presenca)
    if aplicado_em is not None:
        strike.aplicado_em = aplicado_em
        strike.expira_em = aplicado_em + timedelta(days=30)
    strike.save()

    Notificacao.objects.create(
        usuario=aluno,
        titulo='Novo Strike Recebido',
        mensagem=(
            f'Você recebeu um strike por falta na refeição '
            f'{presenca.reserva.refeicao}. Lembre-se que {LIMITE_BLOQUEIO} '
            f'strikes ativos resultam em bloqueio.'
        ),
    )

    strikes_ativos = aluno.strikes.filter(expira_em__gt=timezone.now()).count()
    if strikes_ativos >= LIMITE_BLOQUEIO and not aluno.bloqueado:
        aluno.bloqueado = True
        aluno.save(update_fields=['bloqueado'])
        Notificacao.objects.create(
            usuario=aluno,
            titulo='Sua conta foi bloqueada',
            mensagem=(
                'Devido ao acúmulo de 2 strikes ativos, seu acesso a novas '
                'reservas foi suspenso. Procure a nutricionista.'
            ),
        )

    return strike
