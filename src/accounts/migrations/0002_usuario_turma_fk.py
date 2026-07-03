from django.db import migrations, models
import django.db.models.deletion

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


def migrar_turma_legada_para_fk(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    Turma = apps.get_model('administrativo', 'Turma')

    turmas_por_nome = {t.nome: t for t in Turma.objects.all()}

    for usuario in Usuario.objects.exclude(turma_legado='').exclude(turma_legado__isnull=True):
        nome = TURMAS_LEGADAS.get(usuario.turma_legado)
        if nome and nome in turmas_por_nome:
            usuario.turma = turmas_por_nome[nome]
            usuario.save(update_fields=['turma'])


def reverter_turma_fk_para_legada(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    Turma = apps.get_model('administrativo', 'Turma')

    nome_para_codigo = {v: k for k, v in TURMAS_LEGADAS.items()}
    turmas_por_id = {str(t.id): t for t in Turma.objects.all()}

    for usuario in Usuario.objects.exclude(turma__isnull=True):
        turma = turmas_por_id.get(str(usuario.turma_id))
        if turma and turma.nome in nome_para_codigo:
            usuario.turma_legado = nome_para_codigo[turma.nome]
            usuario.save(update_fields=['turma_legado'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('administrativo', '0004_seed_turmas'),
    ]

    operations = [
        migrations.RenameField(
            model_name='usuario',
            old_name='turma',
            new_name='turma_legado',
        ),
        migrations.AddField(
            model_name='usuario',
            name='turma',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='alunos',
                to='administrativo.turma',
            ),
        ),
        migrations.RunPython(migrar_turma_legada_para_fk, reverter_turma_fk_para_legada),
        migrations.RemoveField(
            model_name='usuario',
            name='turma_legado',
        ),
    ]
