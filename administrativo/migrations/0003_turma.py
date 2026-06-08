# Generated manually for Turma model

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administrativo', '0002_delete_notificacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='Turma',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100)),
                ('turno', models.CharField(
                    choices=[('matutino', 'Matutino'), ('vespertino', 'Vespertino'), ('noturno', 'Noturno')],
                    default='matutino',
                    max_length=20,
                )),
                ('dia_contraturno', models.IntegerField(
                    blank=True,
                    choices=[
                        (0, 'Segunda-feira'),
                        (1, 'Terça-feira'),
                        (2, 'Quarta-feira'),
                        (3, 'Quinta-feira'),
                        (4, 'Sexta-feira'),
                        (5, 'Sábado'),
                        (6, 'Domingo'),
                    ],
                    null=True,
                )),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Turma',
                'verbose_name_plural': 'Turmas',
                'ordering': ['nome'],
            },
        ),
    ]
