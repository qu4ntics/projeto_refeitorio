from django.utils import timezone
from .models import Notificacao

def global_context(request):
    """
    Popula variáveis globais para o base.html: notificações e status de strikes.
    """
    context = {}
    if request.user.is_authenticated:
        # Contagem de notificações não lidas (solicitado)
        context['notificacoes_nao_lidas'] = Notificacao.objects.filter(usuario=request.user, lida=False).count()
        
        # Dados para a sidebar do aluno
        if request.user.perfil == 'aluno':
            agora = timezone.now()
            context['strikes_ativos'] = request.user.strikes.filter(expira_em__gt=agora).count()
            context['proximo_strike_expira'] = request.user.strikes.filter(expira_em__gt=agora).order_by('expira_em').values_list('expira_em', flat=True).first()
            
    return context