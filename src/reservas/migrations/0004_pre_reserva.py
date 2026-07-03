import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refeicoes', '0005_refeicao_chamada_aberta'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservas', '0003_alter_reserva_aluno'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreReserva',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[
                        ('pendente', 'Pendente'),
                        ('confirmada', 'Confirmada'),
                        ('rejeitada', 'Rejeitada'),
                        ('expirada', 'Expirada'),
                    ],
                    default='pendente',
                    max_length=12,
                )),
                ('expira_em', models.DateTimeField()),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('aluno', models.ForeignKey(
                    limit_choices_to={'perfil': 'aluno'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pre_reservas',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('refeicao', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pre_reservas',
                    to='refeicoes.refeicao',
                )),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('aluno', 'refeicao'),
                        name='unique_pre_reserva',
                    ),
                ],
            },
        ),
    ]
