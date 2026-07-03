import uuid

from django.db import migrations, models


TIPOS_REFEICAO = [
    'cafe',
    'lanche_manha',
    'almoco',
    'lanche_tarde',
    'jantar',
]


def seed_tipos_refeicao(apps, schema_editor):
    TipoRefeicao = apps.get_model('administrativo', 'TipoRefeicao')
    existentes = {t.nome for t in TipoRefeicao.objects.all()}

    for codigo in TIPOS_REFEICAO:
        if codigo in existentes:
            TipoRefeicao.objects.filter(nome=codigo).update(ativo=True)
        else:
            TipoRefeicao.objects.create(
                id=uuid.uuid4(),
                nome=codigo,
                ativo=False,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0009_alter_janelareserva_tipo_refeicao_alter_strike_aluno'),
    ]

    operations = [
        migrations.AddField(
            model_name='tiporefeicao',
            name='ativo',
            field=models.BooleanField(default=False, verbose_name='Habilitada'),
        ),
        migrations.RunPython(seed_tipos_refeicao, migrations.RunPython.noop),
    ]
