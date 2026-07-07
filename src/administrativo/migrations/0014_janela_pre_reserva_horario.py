from datetime import date, datetime, time, timedelta

from django.db import migrations, models


def converter_minutos_para_horario(apps, schema_editor):
    JanelaReserva = apps.get_model('administrativo', 'JanelaReserva')
    data_refeicao = date(2000, 1, 2)

    for janela in JanelaReserva.objects.all():
        abertura = janela.horario_abertura
        fechamento = janela.horario_fechamento
        minutos = janela.minutos_pre_reserva

        inicio_dt = datetime.combine(data_refeicao - timedelta(days=1), abertura)
        fim_dt = datetime.combine(data_refeicao, fechamento)
        max_fim_pre_dt = fim_dt - timedelta(hours=1)

        candidato_dt = inicio_dt + timedelta(minutes=minutos)
        if candidato_dt.time() > abertura:
            fim_pre_dt = datetime.combine(data_refeicao - timedelta(days=1), candidato_dt.time())
        else:
            fim_pre_dt = datetime.combine(data_refeicao, candidato_dt.time())

        if fim_pre_dt <= inicio_dt or fim_pre_dt >= fim_dt or fim_pre_dt > max_fim_pre_dt:
            fim_pre_dt = min(inicio_dt + timedelta(hours=1), max_fim_pre_dt)
            if fim_pre_dt <= inicio_dt:
                fim_pre_dt = max_fim_pre_dt

        janela.horario_fechamento_pre_reserva = fim_pre_dt.time()
        janela.save(update_fields=['horario_fechamento_pre_reserva'])


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0013_pre_reserva_contraturno'),
    ]

    operations = [
        migrations.AddField(
            model_name='janelareserva',
            name='horario_fechamento_pre_reserva',
            field=models.TimeField(
                default=time(6, 0),
                help_text='Prazo para o aluno confirmar ou rejeitar a pré-reserva. Deve ser pelo menos 1 hora antes do fechamento da janela geral.',
                verbose_name='Horário de Fechamento da Pré-reserva',
            ),
        ),
        migrations.RunPython(converter_minutos_para_horario, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='janelareserva',
            name='minutos_pre_reserva',
        ),
    ]
