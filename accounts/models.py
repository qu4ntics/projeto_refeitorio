import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    PERFIS = [
        ('aluno', 'Aluno'),
        ('nutricionista', 'Nutricionista'),
        ('refeitorio', 'Refeitório'),
    ]
    perfil = models.CharField(max_length=20, choices=PERFIS, default='aluno')
    email = models.EmailField(unique=True)
    turma = models.ForeignKey(
        'administrativo.Turma',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='alunos',
    )
    bloqueado = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.perfil == 'aluno' and not self.turma:
            raise ValidationError({'turma': 'Turma é obrigatória para alunos.'})
        if self.perfil != 'aluno' and self.turma:
            raise ValidationError({'turma': 'Apenas alunos podem pertencer a uma turma.'})

    def save(self, *args, **kwargs):
        if self.perfil != 'aluno':
            self.turma = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username
