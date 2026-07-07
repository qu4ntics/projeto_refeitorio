from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import Usuario
from administrativo.models import Notificacao
from refeicoes.models import Refeicao
from reservas.models import PreReserva, Reserva


class PreReservaError(ValidationError):
    pass


def _marcar_pre_reservas_disparadas(refeicao, quando=None):
    refeicao.pre_reservas_disparadas_em = quando or timezone.now()
    refeicao.save(update_fields=['pre_reservas_disparadas_em'])


def ativar_pre_reservas(refeicao):
    if not refeicao.exige_reserva or refeicao.pre_reservas_disparadas_em:
        return

    limites = refeicao.get_janela_reserva()
    if not limites:
        return

    agora = timezone.now()
    if agora < limites['inicio']:
        return

    fim_pre = limites['fim_pre_reserva']
    if agora >= fim_pre:
        _marcar_pre_reservas_disparadas(refeicao, agora)
        return

    weekday = refeicao.data.weekday()
    alunos = Usuario.objects.filter(
        perfil='aluno',
        bloqueado=False,
        turma__dias_contraturno__contains=[weekday],
    ).exclude(
        reservas__refeicao=refeicao,
        reservas__status='ativa',
    )

    pre_reservas = [
        PreReserva(aluno=aluno, refeicao=refeicao, expira_em=fim_pre)
        for aluno in alunos
    ]

    _marcar_pre_reservas_disparadas(refeicao, agora)

    if not pre_reservas:
        return

    PreReserva.objects.bulk_create(pre_reservas, ignore_conflicts=True)

    criadas = PreReserva.objects.filter(
        refeicao=refeicao,
        status='pendente',
        aluno__in=alunos,
    ).select_related('aluno')

    prazo = fim_pre.strftime('%d/%m/%Y às %H:%M')
    tipo = refeicao.get_tipo_display()
    data = refeicao.data.strftime('%d/%m/%Y')
    notificacoes = [
        Notificacao(
            usuario=pr.aluno,
            titulo='Pré-reserva de contra-turno',
            mensagem=(
                f'A janela de reservas abriu e você tem uma pré-reserva para {tipo} em {data}. '
                f'Confirme ou rejeite até {prazo}.'
            ),
        )
        for pr in criadas
    ]
    if notificacoes:
        Notificacao.objects.bulk_create(notificacoes)


def sincronizar_pre_reservas(refeicoes):
    for refeicao in refeicoes:
        expirar_pendentes(refeicao)
        ativar_pre_reservas(refeicao)


def confirmar_pre_reserva(pre_reserva_id, aluno):
    with transaction.atomic():
        pre_reserva = get_object_or_404(
            PreReserva.objects.select_for_update(),
            pk=pre_reserva_id,
        )

        if pre_reserva.aluno_id != aluno.pk:
            raise PreReservaError('Esta pré-reserva não pertence a você.')
        if pre_reserva.status != 'pendente':
            raise PreReservaError('Esta pré-reserva não está mais pendente.')
        if pre_reserva.expira_em <= timezone.now():
            raise PreReservaError('O prazo para confirmar esta pré-reserva expirou.')
        if aluno.bloqueado:
            raise PreReservaError('Sua conta está bloqueada. Contate a nutricionista.')

        refeicao = Refeicao.objects.select_for_update().get(pk=pre_reserva.refeicao_id)

        if refeicao.reservas.filter(status='ativa').count() >= refeicao.limite_vagas:
            raise PreReservaError('Não há mais vagas disponíveis para esta refeição.')

        Reserva.objects.create(
            aluno=aluno,
            refeicao=refeicao,
            status='ativa',
        )
        pre_reserva.status = 'confirmada'
        pre_reserva.save(update_fields=['status'])


def rejeitar_pre_reserva(pre_reserva_id, aluno):
    pre_reserva = get_object_or_404(PreReserva, pk=pre_reserva_id)

    if pre_reserva.aluno_id != aluno.pk:
        raise PreReservaError('Esta pré-reserva não pertence a você.')
    if pre_reserva.status != 'pendente':
        raise PreReservaError('Esta pré-reserva não está mais pendente.')

    pre_reserva.status = 'rejeitada'
    pre_reserva.save(update_fields=['status'])


def expirar_pendentes(refeicao):
    return PreReserva.objects.filter(
        refeicao=refeicao,
        status='pendente',
        expira_em__lte=timezone.now(),
    ).update(status='expirada')
