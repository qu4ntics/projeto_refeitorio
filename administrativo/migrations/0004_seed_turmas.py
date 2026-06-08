from django.db import migrations

TURMAS_LEGADAS = {
    '1': '1º ano Administração',
    '2': '2º ano Administração',
    '3': '3º ano Administração',
    '4': '1º ano Agropecuária',
    '5': '2º ano Agropecuária',
    '6': '3º ano Agropecuária',
    '7': '1º ano Informática',
    '8': '2º ano Informática',
    '9': '3º ano Informática',
    '10': '1º ano Mineração',
    '11': '2º ano Mineração',
    '12': '3º ano Mineração',
}


def seed_turmas(apps, schema_editor):
    Turma = apps.get_model('administrativo', 'Turma')
    for codigo, nome in TURMAS_LEGADAS.items():
        Turma.objects.get_or_create(
            nome=nome,
            defaults={
                'turno': 'matutino',
                'dia_contraturno': None,
                'ativo': True,
            },
        )


def unseed_turmas(apps, schema_editor):
    Turma = apps.get_model('administrativo', 'Turma')
    Turma.objects.filter(nome__in=TURMAS_LEGADAS.values()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0003_turma'),
    ]

    operations = [
        migrations.RunPython(seed_turmas, unseed_turmas),
    ]
