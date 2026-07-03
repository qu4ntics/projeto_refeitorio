from datetime import timedelta
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils import timezone

from reservaif.models import UUIDModel


class Turma(UUIDModel):
    TURNOS = [
        ('matutino', 'Matutino'),
        ('vespertino', 'Vespertino'),
        ('noturno', 'Noturno'),
    ]
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    nome = models.CharField('Nome', max_length=100)
    turno = models.CharField('Turno', max_length=20, choices=TURNOS, default='matutino')
    dias_contraturno = models.JSONField(
        'Dias de contraturno',
        default=list,
        blank=True,
        help_text='Dias da semana (0=segunda … 6=domingo) em que a turma possui contraturno.',
    )
    ativo = models.BooleanField('Ativa', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

    def __str__(self):
        return self.nome

    def dias_contraturno_display(self):
        labels = dict(self.DIAS_SEMANA)
        return ', '.join(labels[d] for d in sorted(self.dias_contraturno or []) if d in labels)


class Presenca(UUIDModel):
    reserva = models.OneToOneField(
        'reservas.Reserva',
        on_delete=models.CASCADE,
        related_name='presenca',
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'perfil': 'refeitorio'},
        related_name='presencas_confirmadas',
    )
    compareceu = models.BooleanField()
    confirmado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Presença de {self.reserva} - {"Sim" if self.compareceu else "Não"}'


class Strike(UUIDModel):
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='strikes',
    )
    presenca = models.OneToOneField(
        Presenca,
        on_delete=models.CASCADE,
        related_name='strike',
    )
    aplicado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            if not self.aplicado_em:
                self.aplicado_em = timezone.now()
            if not self.expira_em:
                self.expira_em = self.aplicado_em + timedelta(days=30)
        super().save(*args, **kwargs)

        if is_new:
            # Notificação para o aluno sobre o novo strike
            Notificacao.objects.create(
                usuario=self.aluno,
                titulo="Novo Strike Recebido",
                mensagem=f"Você recebeu um strike por falta na refeição {self.presenca.reserva.refeicao}. Lembre-se que 2 strikes ativos resultam em bloqueio."
            )

            # Lógica de bloqueio automático
            strikes_ativos = self.aluno.strikes.filter(expira_em__gt=timezone.now()).count()
            if strikes_ativos >= 2:
                self.aluno.bloqueado = True
                self.aluno.save(update_fields=['bloqueado'])
                
                Notificacao.objects.create(
                    usuario=self.aluno,
                    titulo="Sua conta foi bloqueada",
                    mensagem="Devido ao acúmulo de 2 strikes ativos, seu acesso a novas reservas foi suspenso. Procure a nutricionista."
                )


class Notificacao(UUIDModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    titulo = models.CharField(max_length=100)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"


class TipoRefeicao(UUIDModel):
    nome = models.CharField('Nome', max_length=50, unique=True)
    ativo = models.BooleanField('Habilitada', default=False)
    horario_inicio_consumo = models.TimeField(
        'Horário de Início da Refeição',
        null=True,
        blank=True,
    )
    horario_fim_consumo = models.TimeField(
        'Horário de Término da Refeição',
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()
        if (
            self.horario_inicio_consumo
            and self.horario_fim_consumo
            and self.horario_fim_consumo <= self.horario_inicio_consumo
        ):
            raise ValidationError({
                'horario_fim_consumo': (
                    'O término da refeição deve ser posterior ao início.'
                ),
            })

    @classmethod
    def codigos_habilitados(cls):
        return list(
            cls.objects.filter(ativo=True).values_list('nome', flat=True)
        )

    def __str__(self):
        return self.nome


class JanelaReserva(UUIDModel):
    tipo_refeicao = models.OneToOneField(
        TipoRefeicao,
        on_delete=models.PROTECT,
        related_name='janela'
    )
    horario_abertura = models.TimeField('Horário de Abertura (Dia Anterior)')
    horario_fechamento = models.TimeField('Horário de Fechamento (Dia da Refeição)')

    class Meta:
        verbose_name = 'Janela de Reserva'
        verbose_name_plural = 'Janelas de Reserva'

    def clean(self):
        # Validação: Abertura vs Fechamento (Evitar janelas maiores que 24h ou negativas)
        if self.horario_abertura == self.horario_fechamento:
            raise ValidationError({
                'horario_abertura': 'O horário de abertura não pode ser igual ao de fechamento.'
            })

    def __str__(self):
        return f"Janela: {self.tipo_refeicao.nome}"


class ConfigReserva(UUIDModel):
    # Mantido por compatibilidade com as views existentes
    abertura = models.TimeField()
    encerramento = models.TimeField()
    minutos_cancelamento = models.IntegerField(default=60)
    vigente_desde = models.DateTimeField(default=timezone.now)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='configuracoes_criadas'
    )

    @classmethod
    def get_config_ativa(cls):
        return cls.objects.order_by('-vigente_desde').first()