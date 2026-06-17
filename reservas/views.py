from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import perfil_required
from accounts.models import Usuario
from administrativo.models import Notificacao
from refeicoes.models import Refeicao
from .models import Reserva

@login_required
@perfil_required('aluno')
@require_POST
@transaction.atomic
def criar_reserva(request, refeicao_id):
    """
    Implementa a lógica de criação de reserva com validações obrigatórias.
    """
    # select_for_update bloqueia a linha da refeição para evitar race conditions
    refeicao = get_object_or_404(Refeicao.objects.select_for_update(), pk=refeicao_id)
    usuario = request.user

    # 1. Validação: Aluno bloqueado
    if usuario.bloqueado:
        messages.error(request, "Sua conta está bloqueada. Por favor, contate a nutricionista para regularizar.")
        return redirect('refeicoes:homepage')

    # 2. Validação: Refeição exige reserva
    if not refeicao.exige_reserva:
        messages.error(request, "Esta refeição é apenas informativa e não requer reserva.")
        return redirect('refeicoes:homepage')

    # 3. Validação: Data e Janela de reserva
    hoje = timezone.localdate()
    
    # Bloqueio imediato para datas passadas
    if refeicao.data < hoje:
        messages.error(request, "Não é possível realizar reservas para datas que já passaram.")
        return redirect('refeicoes:homepage')

    # 3. Validação: Janela de reserva unificada com o Model
    if not refeicao.reserva_aberta:
        status_msg = refeicao.get_status_reserva()
        if refeicao.reserva_futura:
            messages.info(request, f"Reserva ainda não disponível. {status_msg}")
        else:
            messages.warning(request, f"Não foi possível reservar: {status_msg}")
        return redirect('refeicoes:homepage')

    # 4. Validação: Vagas disponíveis
    if refeicao.vagas_disponiveis <= 0:
        messages.error(request, "Infelizmente as vagas para esta refeição estão esgotadas.")
        return redirect('refeicoes:homepage')

    # 5. Validação: Reserva duplicada
    reserva_existente = Reserva.objects.filter(
        aluno=usuario, 
        refeicao=refeicao, 
        status='ativa'
    ).exists()
    
    if reserva_existente:
        messages.info(request, "Você já possui uma reserva ativa para esta refeição.")
        return redirect('refeicoes:homepage')

    # Se passar por tudo, persiste no banco
    Reserva.objects.create(aluno=usuario, refeicao=refeicao, status='ativa')

    # Notificação para Nutricionistas se as vagas esgotarem
    if refeicao.vagas_disponiveis == 0:
        nutris = Usuario.objects.filter(perfil='nutricionista')
        notificacoes = [
            Notificacao(
                usuario=nutri,
                titulo="Vagas Esgotadas!",
                mensagem=f"As vagas para a refeição {refeicao.get_tipo_display()} do dia {refeicao.data} acabaram de esgotar."
            ) for nutri in nutris
        ]
        Notificacao.objects.bulk_create(notificacoes)

    messages.success(request, f"Reserva para {refeicao.get_tipo_display()} realizada com sucesso!")
    return redirect('refeicoes:homepage')

@login_required
@perfil_required('aluno')
@require_POST
@transaction.atomic
def cancelar_reserva(request, reserva_id):
    """
    Permite ao aluno cancelar sua própria reserva ativa, validando o prazo configurado.
    """
    # select_for_update evita race conditions se o aluno clicar rápido demais
    reserva = get_object_or_404(Reserva.objects.select_for_update(), pk=reserva_id, aluno=request.user)
    
    if reserva.status == 'cancelada':
        messages.info(request, "Esta reserva já foi cancelada.")
        return redirect('refeicoes:homepage')
        
    if reserva.status != 'ativa':
        messages.error(request, "Apenas reservas ativas podem ser canceladas.")
        return redirect('refeicoes:homepage')

    refeicao = reserva.refeicao
    
    if not refeicao.pode_cancelar:
        messages.error(
            request, 
            "O prazo para cancelamento desta refeição já expirou."
        )
        return redirect('refeicoes:homepage')

    reserva.status = 'cancelada'
    reserva.cancelado_em = timezone.now()
    reserva.save()
    
    messages.success(request, f"Reserva para {refeicao.get_tipo_display()} cancelada com sucesso.")
    return redirect('refeicoes:homepage')

@login_required
@perfil_required('refeitorio')
def lista_presenca(request):
    """
    Redireciona para a view centralizada em refeicoes para evitar duplicidade de código
    e garantir que o trabalho de todos os integrantes seja preservado em um único lugar.
    """
    from refeicoes.views import lista_presenca as lista_centralizada
    return lista_centralizada(request)