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
    perfil = models.CharField(max_length=20, choices=PERFIS, default='aluno')
    email = models.EmailField(unique=True)
    turma = models.CharField(max_length=50, choices=TURMAS, blank=True, default='')
    bloqueado = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.perfil == 'aluno' and not self.turma:
            raise ValidationError({'turma': 'Turma é obrigatória para alunos.'})

    def __str__(self):
        return self.get_full_name() or self.username
