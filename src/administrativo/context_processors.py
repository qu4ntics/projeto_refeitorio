from django.utils import timezone

from .models import Notificacao

NAV_SECTION_BY_URL = {
    'homepage': 'cardapio',
    'strikes_aluno': 'strikes',
    'notificacoes_aluno': 'notificacoes',
    'configuracoes_aluno': 'configuracoes',
    'painel_nutricionista': 'painel',
    'cardapio_semana': 'refeicoes',
    'criar': 'refeicoes',
    'nutricionista_lista': 'refeicoes',
    'nutricionista_nova': 'refeicoes',
    'nutricionista_editar': 'refeicoes',
    'nutricionista_deletar': 'refeicoes',
    'pratos_lista': 'pratos',
    'prato_criar': 'pratos',
    'prato_editar': 'pratos',
    'prato_excluir': 'pratos',
    'alunos_turmas': 'alunos',
    'alunos_turmas_arquivadas': 'alunos',
    'alunos_turma': 'alunos',
    'turma_criar': 'alunos',
    'turma_editar': 'alunos',
    'turma_excluir': 'alunos',
    'turma_atualizar_contraturno': 'alunos',
    'alunos_bloqueados': 'bloqueados',
    'desbloquear_aluno': 'bloqueados',
    'configuracoes': 'config',
    'janela_horarios_lista': 'config',
    'janela_horarios_detalhe': 'config',
    'painel_refeitorio': 'painel_ref',
    'lista-presenca': 'presenca',
    'chamada': 'presenca',
    'chamada_resumo': 'presenca',
    'abrir_chamada': 'presenca',
    'atualizar_status_reserva': 'presenca',
    'encerrar_chamada': 'presenca',
    'reabrir_chamada': 'presenca',
}


def _resolve_nav_section(request):
    match = getattr(request, 'resolver_match', None)
    if not match or not match.url_name:
        return None
    return NAV_SECTION_BY_URL.get(match.url_name)


def global_context(request):
    """
    Popula variáveis globais para o base.html: notificações e status de strikes.
    """
    context = {}
    if request.user.is_authenticated:
        context['notificacoes_nao_lidas'] = Notificacao.objects.filter(
            usuario=request.user, lida=False,
        ).count()
        context['nav_section'] = _resolve_nav_section(request)

        if request.user.perfil == 'aluno':
            agora = timezone.now()
            context['strikes_ativos'] = request.user.strikes.filter(
                expira_em__gt=agora,
            ).count()
            context['proximo_strike_expira'] = (
                request.user.strikes
                .filter(expira_em__gt=agora)
                .order_by('expira_em')
                .values_list('expira_em', flat=True)
                .first()
            )

    return context
