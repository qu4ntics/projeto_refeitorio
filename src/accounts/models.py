import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

CODIGO_DIGITOS = 6
CODIGO_TTL = timedelta(minutes=15)
MAX_TENTATIVAS = 5
REENVIO_COOLDOWN = timedelta(seconds=60)


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


class CodigoConfirmacaoEmail(models.Model):
    """Código numérico enviado por e-mail para o aluno ativar a conta no cadastro."""

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='codigo_confirmacao',
    )
    codigo_hash = models.CharField(max_length=128)
    criado_em = models.DateTimeField(auto_now_add=True)
    enviado_em = models.DateTimeField(default=timezone.now)
    expira_em = models.DateTimeField()
    tentativas = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'Código de {self.usuario.email}'

    @classmethod
    def gerar_para(cls, usuario):
        """Cria (ou substitui) o código do usuário e devolve o valor em claro."""
        codigo = f'{secrets.randbelow(10 ** CODIGO_DIGITOS):0{CODIGO_DIGITOS}d}'
        agora = timezone.now()
        cls.objects.update_or_create(
            usuario=usuario,
            defaults={
                'codigo_hash': make_password(codigo),
                'criado_em': agora,
                'enviado_em': agora,
                'expira_em': agora + CODIGO_TTL,
                'tentativas': 0,
            },
        )
        return codigo

    @property
    def expirado(self):
        return timezone.now() >= self.expira_em

    @property
    def bloqueado(self):
        return self.tentativas >= MAX_TENTATIVAS

    def pode_reenviar(self):
        return timezone.now() - self.enviado_em >= REENVIO_COOLDOWN

    def segundos_para_reenviar(self):
        restante = REENVIO_COOLDOWN - (timezone.now() - self.enviado_em)
        return max(0, int(restante.total_seconds()))

    def conferir(self, codigo):
        if self.expirado or self.bloqueado:
            return False
        if check_password((codigo or '').strip(), self.codigo_hash):
            return True
        self.tentativas += 1
        self.save(update_fields=['tentativas'])
        return False
