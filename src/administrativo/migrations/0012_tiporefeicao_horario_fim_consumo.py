from datetime import time

from django.db import migrations, models


HORARIOS_FIM_PADRAO = {
    'cafe': time(7, 45),
    'lanche_manha': time(10, 0),
    'almoco': time(13, 30),
    'lanche_tarde': time(15, 30),
    'jantar': time(20, 0),
}


def seed_horarios_fim_consumo(apps, schema_editor):
    TipoRefeicao = apps.get_model('administrativo', 'TipoRefeicao')
    for codigo, horario in HORARIOS_FIM_PADRAO.items():
        TipoRefeicao.objects.filter(nome=codigo).update(horario_fim_consumo=horario)


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0011_tiporefeicao_horario_inicio_consumo'),
    ]

    operations = [
        migrations.AddField(
            model_name='tiporefeicao',
            name='horario_fim_consumo',
            field=models.TimeField(
                blank=True,
                null=True,
                verbose_name='Horário de Término da Refeição',
            ),
        ),
        migrations.RunPython(seed_horarios_fim_consumo, migrations.RunPython.noop),
    ]
