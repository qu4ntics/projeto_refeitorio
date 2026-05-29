from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser): # A classe Usuario herda todos os atributos e métodos de AbstractUser
    PERFIS = [
        ('aluno', 'Aluno'), #CRIA O PERFIL PARA ALUNO
        ('nutricionista', 'Nutricionista'), #CRIA O PERFIL DO NUTRICIONISTA
        ('refeitorio', 'Refeitório'),       #PERFIL DO REFEITORIO
    ]
    perfil = models.CharField(max_length=20, choices=PERFIS, default='aluno')
    email = models.EmailField(unique=True)
    turma = models.CharField(max_length=50)