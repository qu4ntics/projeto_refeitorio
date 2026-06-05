from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from accounts.decorators import perfil_required
from administrativo.models import ConfigReserva
from refeicoes.models import Refeicao
from .models import Reserva

@login_required
@perfil_required('aluno')
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

    # 3. Validação: Janela de reserva
    config = ConfigReserva.get_config_ativa()
    if config:
        agora = timezone.now()
        data_abertura = refeicao.data - timezone.timedelta(days=1)
        inicio_janela = timezone.make_aware(datetime.combine(data_abertura, config.abertura))
        fim_janela = timezone.make_aware(datetime.combine(refeicao.data, config.encerramento))

        if not (inicio_janela <= agora <= fim_janela):
            messages.warning(
                request, 
                f"Fora da janela de reserva. O horário limite para esta refeição é às {config.encerramento.strftime('%H:%M')}."
            )
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
    messages.success(request, f"Reserva para {refeicao.get_tipo_display()} realizada com sucesso!")
    return redirect('refeicoes:homepage')

@login_required
@perfil_required('aluno')
def cancelar_reserva(request, reserva_id):
    """
    Permite ao aluno cancelar sua própria reserva ativa, validando o prazo configurado.
    """
    reserva = get_object_or_404(Reserva, pk=reserva_id, aluno=request.user, status='ativa')
    refeicao = reserva.refeicao
    
    config = ConfigReserva.get_config_ativa()
    if config:
        agora = timezone.now()
        # Prazo limite: encerramento da janela menos os minutos de cancelamento configurados
        encerramento = timezone.make_aware(datetime.combine(refeicao.data, config.encerramento))
        limite_cancelamento = encerramento - timedelta(minutes=config.minutos_cancelamento)
        
        if agora > limite_cancelamento:
            messages.error(
                request, 
                f"Não é mais possível cancelar. O prazo expirou às {limite_cancelamento.strftime('%H:%M')}."
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
    hoje = timezone.now().date()
    
    # Busca reservas ativas ou concluídas de hoje, trazendo o Usuário e a Refeição juntos
    reservas = Reserva.objects.filter(
        refeicao__data=hoje
    ).exclude(status='cancelada').select_related('aluno', 'refeicao')

    # Filtro de pesquisa por Nome, Sobrenome ou código da Turma
    pesquisa = request.GET.get('search')
    if pesquisa:
        reservas = reservas.filter(
            Q(aluno__first_name__icontains=pesquisa) | 
            Q(aluno__last_name__icontains=pesquisa) |
            Q(aluno__turma__icontains=pesquisa)
        )

    return render(request, 'refeitorio/lista_presenca.html', {
        'reservas': reservas, 
        'pesquisa': pesquisa
    })