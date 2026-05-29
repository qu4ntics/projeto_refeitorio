from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    PERFIS = [
        ('aluno', 'Aluno'),
        ('nutricionista', 'Nutricionista'),
        ('refeitorio', 'Refeitório'),
    ]
    perfil = models.CharField(max_length=20, choices=PERFIS, default='aluno')
    turma = models.CharField(max_length=100, blank=True)