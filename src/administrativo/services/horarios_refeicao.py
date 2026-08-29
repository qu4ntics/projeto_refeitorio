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


def periodo_consumo_terminou(refeicao, agora=None):
    """
    True quando não há mais como marcar presença: o horário de hoje já passou,
    ou a refeição é de um dia anterior. O segundo caso importa para o cron
    recuperar chamadas de dias em que ele não rodou.
    """
    agora = agora or timezone.localtime()
    if refeicao.data < agora.date():
        return True
    return fase_periodo_consumo(refeicao, agora) == 'depois'


def pode_reabrir_chamada(refeicao, agora=None):
    """
    Reabertura permitida só durante o horário da refeição.

    Fora dele a reabertura não serviria para nada: presença só pode ser marcada
    dentro do período de consumo, e o encerramento automático fecharia a chamada
    de novo no acesso seguinte.
    """
    return fase_periodo_consumo(refeicao, agora) == 'durante'
