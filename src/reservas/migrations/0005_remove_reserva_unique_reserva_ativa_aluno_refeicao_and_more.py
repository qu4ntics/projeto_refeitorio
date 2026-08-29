"""
Fecha a brecha que permitia duas reservas do mesmo aluno para a mesma refeição.

A restrição antiga só valia para status='ativa'. Como marcar presença muda o
status para 'concluida', o aluno voltava a conseguir reservar depois de comer e
aparecia duas vezes na lista de chamada. A nova restrição cobre os dois status.
"""

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def cancelar_duplicatas(apps, schema_editor):
    """
    Deixa uma reserva válida por aluno/refeição antes de criar a restrição.

    Mantém a mais antiga, preferindo uma 'concluida' quando existir — ela tem
    presença registrada e possivelmente strike, então é a que corresponde ao que
    de fato aconteceu. As demais viram 'cancelada'.
    """
    Reserva = apps.get_model('reservas', 'Reserva')
    agora = timezone.now()

    grupos = {}
    validas = Reserva.objects.filter(
        status__in=['ativa', 'concluida'],
    ).order_by('reservado_em')
    for reserva in validas:
        grupos.setdefault((reserva.aluno_id, reserva.refeicao_id), []).append(reserva)

    ids_para_cancelar = []
    for reservas in grupos.values():
        if len(reservas) < 2:
            continue
        concluidas = [r for r in reservas if r.status == 'concluida']
        manter = concluidas[0] if concluidas else reservas[0]
        ids_para_cancelar += [r.id for r in reservas if r.id != manter.id]

    if ids_para_cancelar:
        Reserva.objects.filter(id__in=ids_para_cancelar).update(
            status='cancelada', cancelado_em=agora,
        )


def nao_faz_nada(apps, schema_editor):
    """Não há como saber quais cancelamentos vieram desta limpeza."""


class Migration(migrations.Migration):

    dependencies = [
        ('refeicoes', '0008_remove_refeicao_chamada_aberta'),
        ('reservas', '0004_pre_reserva'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='reserva',
            name='unique_reserva_ativa_aluno_refeicao',
        ),
        migrations.RunPython(cancelar_duplicatas, nao_faz_nada),
        migrations.AddConstraint(
            model_name='reserva',
            constraint=models.UniqueConstraint(condition=models.Q(('status__in', ['ativa', 'concluida'])), fields=('aluno', 'refeicao'), name='unique_reserva_valida_aluno_refeicao'),
        ),
    ]
