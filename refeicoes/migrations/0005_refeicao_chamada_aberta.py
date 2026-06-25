from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refeicoes', '0004_refeicao_chamada_finalizada_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='refeicao',
            name='chamada_aberta',
            field=models.BooleanField(default=False, verbose_name='Chamada Aberta'),
        ),
    ]
