from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_usuario_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='bloqueado',
            field=models.BooleanField(default=False),
        ),
    ]
