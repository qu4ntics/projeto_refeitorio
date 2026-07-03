from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import ExtractWeekDay
from django.utils import timezone

from accounts.models import Usuario
from administrativo.models import Presenca, Strike, TipoRefeicao
from refeicoes.models import Refeicao, RefeicaoPrato
from reservas.models import Reserva

DIAS_SEMANA = {
    1: 'Domingo',
    2: 'Segunda-feira',
    3: 'Terça-feira',
    4: 'Quarta-feira',
    5: 'Quinta-feira',
    6: 'Sexta-feira',
    7: 'Sábado',
}

RESERVAS_VALIDAS = Q(status__in=['ativa', 'concluida'])
RESERVAS_ATIVAS = Q(status='ativa')
RESERVAS_VALIDAS_AGG = Q(reservas__status__in=['ativa', 'concluida'])
RESERVAS_ATIVAS_AGG = Q(reservas__status='ativa')


def _periodo(inicio_dias=30):
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=inicio_dias)
    return inicio, hoje


def _refeicoes_encerradas_periodo(inicio, fim):
    return Refeicao.objects.filter(
        data__gte=inicio,
        data__lte=fim,
        exige_reserva=True,
        chamada_finalizada=True,
    )


def calcular_ausencias(periodo_dias=30):
    inicio, fim = _periodo(periodo_dias)
    refeicoes = _refeicoes_encerradas_periodo(inicio, fim)

    total = Presenca.objects.filter(
        compareceu=False,
        reserva__refeicao__in=refeicoes,
    ).count()

    total_reservas = Reserva.objects.filter(
        refeicao__in=refeicoes,
    ).filter(RESERVAS_VALIDAS).count()

    taxa = round(100 * total / total_reservas, 1) if total_reservas else 0

    return {
        'disponivel': total_reservas > 0,
        'total': total,
        'taxa': taxa,
    }


def calcular_dia_pico_almoco(periodo_dias=30):
    inicio, fim = _periodo(periodo_dias)

    por_dia = (
        Reserva.objects.filter(
            refeicao__tipo='almoco',
            refeicao__data__gte=inicio,
            refeicao__data__lte=fim,
        )
        .filter(RESERVAS_VALIDAS)
        .annotate(dow=ExtractWeekDay('refeicao__data'))
        .values('dow')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    pico = por_dia.first()
    if not pico:
        return {'disponivel': False, 'dia': None, 'media': 0}

    dow = pico['dow']
    total_reservas = pico['total']
    ocorrencias = Refeicao.objects.filter(
        tipo='almoco',
        data__gte=inicio,
        data__lte=fim,
        exige_reserva=True,
    ).annotate(dow=ExtractWeekDay('data')).filter(dow=dow).count()

    media = round(total_reservas / ocorrencias, 1) if ocorrencias else 0

    return {
        'disponivel': True,
        'dia': DIAS_SEMANA.get(dow, ''),
        'media': media,
    }


def _ranking_pratos_almoco(periodo_dias=30, limite=3, min_ocorrencias=2, reverse=False):
    inicio, fim = _periodo(periodo_dias)
    refeicoes = _refeicoes_encerradas_periodo(inicio, fim).filter(tipo='almoco')

    itens = (
        RefeicaoPrato.objects.filter(
            prato__categoria='principal',
            refeicao__in=refeicoes,
        )
        .annotate(
            reservas=Count(
                'refeicao__reservas',
                filter=Q(refeicao__reservas__status__in=['ativa', 'concluida']),
            )
        )
        .values('prato__nome', 'prato_id', 'reservas')
    )

    por_prato = defaultdict(lambda: {'nome': '', 'reservas': []})
    for item in itens:
        pid = item['prato_id']
        por_prato[pid]['nome'] = item['prato__nome']
        por_prato[pid]['reservas'].append(item['reservas'])

    rankings = []
    for data in por_prato.values():
        if len(data['reservas']) >= min_ocorrencias:
            media = sum(data['reservas']) / len(data['reservas'])
            rankings.append((media, data['nome']))

    rankings.sort(key=lambda item: item[0], reverse=reverse)
    nomes = [nome for _, nome in rankings[:limite]]

    return {
        'disponivel': bool(nomes),
        'nomes': nomes,
        'texto': ', '.join(nomes) if nomes else '',
    }


def calcular_pratos_menos_populares(periodo_dias=30, limite=3, min_ocorrencias=2):
    return _ranking_pratos_almoco(
        periodo_dias=periodo_dias,
        limite=limite,
        min_ocorrencias=min_ocorrencias,
        reverse=False,
    )


def calcular_pratos_mais_populares(periodo_dias=30, limite=3, min_ocorrencias=2):
    return _ranking_pratos_almoco(
        periodo_dias=periodo_dias,
        limite=limite,
        min_ocorrencias=min_ocorrencias,
        reverse=True,
    )


def calcular_taxa_comparecimento(periodo_dias=30):
    inicio, fim = _periodo(periodo_dias)
    refeicoes = _refeicoes_encerradas_periodo(inicio, fim)

    total_reservas = Reserva.objects.filter(
        refeicao__in=refeicoes,
    ).filter(RESERVAS_VALIDAS).count()

    presentes = Reserva.objects.filter(
        refeicao__in=refeicoes,
        status='concluida',
    ).count()

    taxa = round(100 * presentes / total_reservas) if total_reservas else 0

    return {
        'disponivel': total_reservas > 0,
        'taxa': taxa,
        'periodo_dias': periodo_dias,
    }


ORDEM_TIPOS = [codigo for codigo, _ in Refeicao.TIPOS]


def _escolher_refeicao_principal(atual, nova):
    res_atual = getattr(atual, 'reservas_ativas', 0) or 0
    res_nova = getattr(nova, 'reservas_ativas', 0) or 0
    if res_nova != res_atual:
        return nova if res_nova > res_atual else atual
    return nova if nova.criado_em > atual.criado_em else atual


def preparar_dias_semana_painel(dias_semana):
    """Agrupa refeições duplicadas do mesmo tipo em um único card por dia."""
    ordem = {tipo: idx for idx, tipo in enumerate(ORDEM_TIPOS)}
    dias = []
    for dia in dias_semana:
        escolhidas = {}
        for refeicao in dia['refeicoes']:
            if refeicao.tipo not in escolhidas:
                escolhidas[refeicao.tipo] = refeicao
            else:
                escolhidas[refeicao.tipo] = _escolher_refeicao_principal(
                    escolhidas[refeicao.tipo], refeicao,
                )
        refeicoes = sorted(
            escolhidas.values(),
            key=lambda r: ordem.get(r.tipo, 99),
        )
        dias.append({**dia, 'refeicoes': refeicoes})
    return dias


def listar_refeicoes_hoje():
    hoje = timezone.localdate()
    tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}
    ordem_tipos = [codigo for codigo, _ in Refeicao.TIPOS]

    refeicoes = (
        Refeicao.objects.filter(data=hoje, exige_reserva=True)
        .annotate(
            total_reservas=Count(
                'reservas',
                filter=Q(reservas__status__in=['ativa', 'concluida']),
            ),
        )
        .prefetch_related('itens_prato__prato')
        .order_by('tipo', '-total_reservas', '-criado_em')
    )

    escolhidas = {}
    for refeicao in refeicoes:
        if refeicao.tipo not in escolhidas:
            escolhidas[refeicao.tipo] = refeicao

    itens = []
    for tipo in ordem_tipos:
        refeicao = escolhidas.get(tipo)
        if not refeicao:
            continue
        tipo_cfg = tipos_por_nome.get(refeicao.tipo)
        horario = tipo_cfg.horario_inicio_consumo if tipo_cfg else None
        itens.append({
            'refeicao': refeicao,
            'horario': horario,
            'total_reservas': refeicao.total_reservas,
        })

    return itens


def calcular_resumo_hoje():
    """Totais operacionais das refeições com reserva cadastradas para hoje."""
    hoje = timezone.localdate()
    refeicoes = list(
        Refeicao.objects.filter(data=hoje, exige_reserva=True).annotate(
            total_reservas=Count('reservas', filter=RESERVAS_VALIDAS_AGG),
            reservas_ativas=Count('reservas', filter=RESERVAS_ATIVAS_AGG),
        )
    )

    total_reservas = sum(r.total_reservas for r in refeicoes)
    total_vagas = sum(r.limite_vagas for r in refeicoes)
    lotadas = sum(
        1 for r in refeicoes
        if r.limite_vagas > 0 and r.reservas_ativas >= r.limite_vagas
    )

    cancelamentos = Reserva.objects.filter(
        status='cancelada',
        cancelado_em__date=hoje,
    ).count()

    taxa_ocupacao = round(100 * total_reservas / total_vagas) if total_vagas else None

    return {
        'disponivel': bool(refeicoes),
        'total_reservas': total_reservas,
        'total_vagas': total_vagas,
        'taxa_ocupacao': taxa_ocupacao,
        'cancelamentos': cancelamentos,
        'refeicoes_lotadas': lotadas,
        'qtd_refeicoes': len(refeicoes),
    }


def calcular_disciplina(periodo_dias=30):
    inicio, _ = _periodo(periodo_dias)
    bloqueados = Usuario.objects.filter(perfil='aluno', bloqueado=True).count()
    strikes_periodo = Strike.objects.filter(aplicado_em__date__gte=inicio).count()
    return {
        'bloqueados': bloqueados,
        'strikes_periodo': strikes_periodo,
    }


def metricas_painel(periodo_dias=30, usuario=None):
    return {
        'periodo_dias': periodo_dias,
        'resumo_hoje': calcular_resumo_hoje(),
        'disciplina': calcular_disciplina(periodo_dias),
        'ausencias': calcular_ausencias(periodo_dias),
        'dia_pico': calcular_dia_pico_almoco(periodo_dias),
        'pratos_menos_populares': calcular_pratos_menos_populares(periodo_dias),
        'pratos_mais_populares': calcular_pratos_mais_populares(periodo_dias),
        'comparecimento': calcular_taxa_comparecimento(periodo_dias),
        'refeicoes_hoje': listar_refeicoes_hoje(),
    }
