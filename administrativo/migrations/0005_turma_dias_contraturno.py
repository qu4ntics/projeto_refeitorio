from django.db import migrations, models


def migrar_dia_para_dias(apps, schema_editor):
    Turma = apps.get_model('administrativo', 'Turma')
    for turma in Turma.objects.exclude(dia_contraturno__isnull=True):
        turma.dias_contraturno = [turma.dia_contraturno]
        turma.save(update_fields=['dias_contraturno'])


def reverter_dias_para_dia(apps, schema_editor):
    Turma = apps.get_model('administrativo', 'Turma')
    for turma in Turma.objects.all():
        dias = turma.dias_contraturno or []
        turma.dia_contraturno = dias[0] if dias else None
        turma.save(update_fields=['dia_contraturno'])


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0004_seed_turmas'),
    ]

    operations = [
        migrations.AddField(
            model_name='turma',
            name='dias_contraturno',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Dias da semana (0=segunda … 6=domingo) em que a turma possui contraturno.',
                verbose_name='Dias de contraturno',
            ),
        ),
        migrations.RunPython(migrar_dia_para_dias, reverter_dias_para_dia),
        migrations.RemoveField(
            model_name='turma',
            name='dia_contraturno',
        ),
    ]
