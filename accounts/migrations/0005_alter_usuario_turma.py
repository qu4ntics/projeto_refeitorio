from django.db import migrations, models


TURMAS = [
    ('1', '1º ano Administração'),
    ('2', '2º ano Administração'),
    ('3', '3º ano Administração'),
    ('4', '1º ano Agropecuária'),
    ('5', '2º ano Agropecuária'),
    ('6', '3º ano Agropecuária'),
    ('7', '1º ano Informática'),
    ('8', '2º ano Informática'),
    ('9', '3º ano Informática'),
    ('10', '1º ano Mineração'),
    ('11', '2º ano Mineração'),
    ('12', '3º ano Mineração'),
]

TURMA_POR_NOME = {label: key for key, label in TURMAS}


def normalizar_turmas(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    for usuario in Usuario.objects.exclude(turma=''):
        if usuario.turma in TURMA_POR_NOME:
            usuario.turma = TURMA_POR_NOME[usuario.turma]
            usuario.save(update_fields=['turma'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_usuario_bloqueado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='turma',
            field=models.CharField(choices=TURMAS, max_length=50),
        ),
        migrations.RunPython(normalizar_turmas, migrations.RunPython.noop),
    ]
