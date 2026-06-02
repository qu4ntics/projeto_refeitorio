from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser): # A classe Usuario herda todos os atributos e métodos de AbstractUser
    PERFIS = [
        ('aluno', 'Aluno'), #CRIA O PERFIL PARA ALUNO
        ('nutricionista', 'Nutricionista'), #CRIA O PERFIL DO NUTRICIONISTA
        ('refeitorio', 'Refeitório'),       #PERFIL DO REFEITORIO
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
    turma = models.CharField(max_length=50, choices=TURMAS)
    bloqueado = models.BooleanField(default=False)
