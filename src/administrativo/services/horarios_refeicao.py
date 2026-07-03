from django.utils import timezone

from administrativo.models import TipoRefeicao


def periodo_consumo_configurado(tipo):
    """Retorna (inicio, fim) se ambos estiverem configurados; caso contrário None."""
    if not tipo or not tipo.horario_inicio_consumo or not tipo.horario_fim_consumo:
        return None
    return tipo.horario_inicio_consumo, tipo.horario_fim_consumo


def _tipo_da_refeicao(refeicao):
    return TipoRefeicao.objects.filter(nome=refeicao.tipo).first()


def fase_periodo_consumo(refeicao, agora=None):
    """
    Retorna a fase do período de consumo em relação ao momento atual.
    Valores: 'antes', 'durante', 'depois', 'outro_dia', 'nao_configurado'.
    """
    agora = agora or timezone.localtime()
    if agora.date() != refeicao.data:
        return 'outro_dia'

    periodo = periodo_consumo_configurado(_tipo_da_refeicao(refeicao))
    if not periodo:
        return 'nao_configurado'

    inicio, fim = periodo
    hora = agora.time()
    if hora < inicio:
        return 'antes'
    if hora > fim:
        return 'depois'
    return 'durante'


def pode_abrir_chamada(refeicao, agora=None):
    """Valida se a chamada pode ser aberta agora. Retorna (ok, mensagem_erro)."""
    agora = agora or timezone.localtime()
    if agora.date() != refeicao.data:
        return False, 'A chamada só pode ser aberta no dia da refeição.'

    periodo = periodo_consumo_configurado(_tipo_da_refeicao(refeicao))
    if not periodo:
        return False, (
            'Horário de início e término da refeição não estão configurados. '
            'Solicite à nutricionista.'
        )

    fase = fase_periodo_consumo(refeicao, agora)
    if fase == 'antes':
        inicio, _ = periodo
        return False, (
            f'A chamada estará disponível a partir das {inicio.strftime("%H:%M")}.'
        )
    if fase == 'depois':
        return False, 'O horário da refeição já encerrou. Não é possível abrir a chamada.'
    return True, ''


def pode_reabrir_chamada(refeicao, agora=None):
    """Reabertura permitida no mesmo dia da refeição, até 23:59."""
    agora = agora or timezone.localtime()
    return agora.date() == refeicao.data


def pode_acessar_lista_chamada(refeicao, agora=None):
    """
    GET da lista: permitido se chamada em andamento, encerrada (leitura/resumo)
    ou dentro do período de consumo com chamada ainda fechada.
    """
    agora = agora or timezone.localtime()
    if refeicao.chamada_finalizada:
        return True
    if refeicao.chamada_aberta:
        return True
    ok, _ = pode_abrir_chamada(refeicao, agora)
    return ok
