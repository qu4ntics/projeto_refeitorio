from datetime import time

from refeicoes.models import Refeicao

from administrativo.models import JanelaReserva, TipoRefeicao

HORARIOS_INICIO_PADRAO = {
    'cafe': time(7, 0),
    'lanche_manha': time(9, 30),
    'almoco': time(12, 0),
    'lanche_tarde': time(15, 0),
    'jantar': time(19, 0),
}

HORARIOS_FIM_PADRAO = {
    'cafe': time(7, 45),
    'lanche_manha': time(10, 0),
    'almoco': time(13, 30),
    'lanche_tarde': time(15, 30),
    'jantar': time(20, 0),
}

JANELA_ABERTURA_PADRAO = time(15, 0)
JANELA_FECHAMENTO_PADRAO = time(7, 0)
JANELA_FECHAMENTO_PRE_PADRAO = JanelaReserva.HORARIO_FECHAMENTO_PRE_PADRAO

TIPOS_HABILITADOS_PADRAO = {'almoco'}


def garantir_tipos_refeicao():
    """
    Garante que os cinco tipos de refeição existam no banco.
    Retorna (criados, atualizados).
    """
    criados = 0
    atualizados = 0
    tipos_por_nome = {t.nome: t for t in TipoRefeicao.objects.all()}

    for codigo, _ in Refeicao.TIPOS:
        defaults = {
            'ativo': codigo in TIPOS_HABILITADOS_PADRAO,
            'horario_inicio_consumo': HORARIOS_INICIO_PADRAO.get(codigo),
            'horario_fim_consumo': HORARIOS_FIM_PADRAO.get(codigo),
        }

        if codigo not in tipos_por_nome:
            TipoRefeicao.objects.create(nome=codigo, **defaults)
            criados += 1
            continue

        tipo = tipos_por_nome[codigo]
        changed = False
        for field, value in defaults.items():
            if getattr(tipo, field) != value and getattr(tipo, field) in (None, False, ''):
                setattr(tipo, field, value)
                changed = True
        if changed:
            tipo.save()
            atualizados += 1

    garantir_janelas_reserva_padrao()
    return criados, atualizados


def garantir_janelas_reserva_padrao():
    """
    Cria janelas de reserva padrão para tipos habilitados sem janela.
    Retorna quantidade de janelas criadas.
    """
    criadas = 0
    for tipo in TipoRefeicao.objects.filter(ativo=True):
        _, created = JanelaReserva.objects.get_or_create(
            tipo_refeicao=tipo,
            defaults={
                'horario_abertura': JANELA_ABERTURA_PADRAO,
                'horario_fechamento': JANELA_FECHAMENTO_PADRAO,
                'horario_fechamento_pre_reserva': JANELA_FECHAMENTO_PRE_PADRAO,
            },
        )
        if created:
            criadas += 1
    return criadas
