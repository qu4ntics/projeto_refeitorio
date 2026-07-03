from datetime import time

from django.db import migrations, models


HORARIOS_PADRAO = {
    'cafe': time(7, 0),
    'lanche_manha': time(9, 30),
    'almoco': time(12, 0),
    'lanche_tarde': time(15, 0),
    'jantar': time(19, 0),
}


def seed_horarios_consumo(apps, schema_editor):
    TipoRefeicao = apps.get_model('administrativo', 'TipoRefeicao')
    for codigo, horario in HORARIOS_PADRAO.items():
        TipoRefeicao.objects.filter(nome=codigo).update(horario_inicio_consumo=horario)


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0010_tiporefeicao_ativo_seed'),
    ]

    operations = [
        migrations.AddField(
            model_name='tiporefeicao',
            name='horario_inicio_consumo',
            field=models.TimeField(
                blank=True,
                null=True,
                verbose_name='Horário de Início da Refeição',
            ),
        ),
        migrations.RunPython(seed_horarios_consumo, migrations.RunPython.noop),
    ]
