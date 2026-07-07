from datetime import datetime, timedelta, time
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from reservaif.models import UUIDModel


class PratoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class PratoAtivoManager(models.Manager):
    def get_queryset(self):
        return PratoQuerySet(self.model, using=self._db).ativos()


class PratoTodosManager(models.Manager):
    def get_queryset(self):
        return PratoQuerySet(self.model, using=self._db)


class Prato(UUIDModel):
    CATEGORIAS = [
        ('principal', 'Principal'),
        ('complemento', 'Complemento'),
        ('salada', 'Salada'),
        ('sobremesa', 'Sobremesa'),
    ]
    ORDEM_CATEGORIAS = [c[0] for c in CATEGORIAS]

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = PratoAtivoManager()
    all_objects = PratoTodosManager()

    class Meta:
        verbose_name = 'Prato'
        verbose_name_plural = 'Pratos'
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.get_categoria_display()})'

    def excluir_logicamente(self):
        self.ativo = False
        self.save(update_fields=['ativo'])


class Refeicao(UUIDModel):
    TIPOS = [
        ('cafe', 'Café'),
        ('lanche_manha', 'Lanche da Manhã'),
        ('almoco', 'Almoço'),
        ('lanche_tarde', 'Lanche da Tarde'),
        ('jantar', 'Jantar'),
    ]

    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    limite_vagas = models.PositiveIntegerField()
    exige_reserva = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    chamada_aberta = models.BooleanField(default=False, verbose_name='Chamada Aberta')
    chamada_finalizada = models.BooleanField(default=False, verbose_name="Chamada Finalizada")
    pre_reservas_disparadas_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Pré-reservas disparadas em',
    )
    pratos = models.ManyToManyField(Prato, through='RefeicaoPrato', related_name='refeicoes')

    class Meta:
        verbose_name = 'Refeição'
        verbose_name_plural = 'Refeições'
        ordering = ['data', 'tipo']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.data}'

    @property
    def reservas_ativas_count(self):
        if hasattr(self, 'reservas_ativas'):
            return self.reservas_ativas
        return self.reservas.filter(status='ativa').count()

    @property
    def cardapio_por_categoria(self):
        pratos = [item.prato for item in self.itens_prato.all()]
        if not pratos:
            return []

        ordem = {cat: i for i, cat in enumerate(Prato.ORDEM_CATEGORIAS)}
        pratos.sort(key=lambda p: (ordem.get(p.categoria, 99), p.nome))

        por_categoria = {}
        for prato in pratos:
            texto = (prato.descricao or prato.nome).strip()
            if not texto:
                continue
            por_categoria.setdefault(prato.categoria, []).append(texto)

        categorias_labels = dict(Prato.CATEGORIAS)
        return [
            {
                'categoria': cat,
                'label': categorias_labels.get(cat, cat),
                'itens': por_categoria[cat],
            }
            for cat in Prato.ORDEM_CATEGORIAS
            if cat in por_categoria
        ]

    @property
    def descricao_exibicao(self):
        grupos = self.cardapio_por_categoria
        if not grupos:
            return ''
        partes = [f'{g["label"]}: {", ".join(g["itens"])}' for g in grupos]
        return ' · '.join(partes)

    @property
    def descricao(self):
        return self.descricao_exibicao

    @property
    def vagas_disponiveis(self):
        ocupadas = (
            self.reservas.filter(status='ativa').count()
            + self.pre_reservas.filter(status='pendente').count()
        )
        return max(0, self.limite_vagas - ocupadas)

    @property
    def vagas_ocupadas(self):
        return max(0, self.limite_vagas - self.vagas_disponiveis)

    @property
    def vagas_display(self):
        """Retorna o texto das vagas com o aviso de expiração se necessário."""
        v = self.vagas_disponiveis
        # Pluralização em PT-BR: Apenas 1 é singular. 0 e > 1 são plural.
        v_word = "vaga" if v == 1 else "vagas"
        r_word = "restante" if v == 1 else "restantes"
        texto = f"{v} {v_word} {r_word}"
        return texto

    @property
    def inicio_consumo_datetime(self):
        """Datetime aware do início da refeição, se configurado no tipo."""
        from administrativo.models import TipoRefeicao

        tipo = TipoRefeicao.objects.filter(nome__iexact=self.tipo).first()
        if not tipo or not tipo.horario_inicio_consumo:
            return None
        tz = timezone.get_current_timezone()
        return timezone.make_aware(
            datetime.combine(self.data, tipo.horario_inicio_consumo),
            tz,
        )

    @property
    def refeicao_ainda_nao_iniciou(self):
        inicio = self.inicio_consumo_datetime
        if not inicio:
            return True
        return timezone.localtime() < inicio

    @property
    def janela_encerrada_aguardando_refeicao(self):
        """Janela de reserva fechou, mas o horário da refeição ainda não chegou."""
        return (
            self.exige_reserva
            and self.reserva_encerrada
            and self.refeicao_ainda_nao_iniciou
        )

    @property
    def aviso_reserva_encerrada(self):
        if not self.janela_encerrada_aguardando_refeicao:
            return ''
        fechamento = self.fechamento_reserva_display
        inicio = self.inicio_consumo_datetime
        if inicio:
            return (
                f'O prazo encerrou em {fechamento}. '
                f'A refeição começa às {inicio.strftime("%H:%M")}.'
            )
        return f'O prazo de reservas encerrou em {fechamento}.'

    def get_janela_reserva(self):
        """
        Retorna os limites de abertura e fechamento da reserva.
        Evita importação circular importando models de administrativo internamente.
        """
        from administrativo.models import JanelaReserva, ConfigReserva
        
        janela = JanelaReserva.objects.filter(tipo_refeicao__nome__iexact=self.tipo).first()
        config = ConfigReserva.get_config_ativa()

        if not janela and not config:
            return None

        from administrativo.models import JanelaReserva as JanelaReservaModel

        hora_abre = janela.horario_abertura if janela else config.abertura
        hora_fecha = janela.horario_fechamento if janela else config.encerramento
        hora_fecha_pre = (
            janela.horario_fechamento_pre_reserva
            if janela
            else JanelaReservaModel.HORARIO_FECHAMENTO_PRE_PADRAO
        )
        minutos_cancelamento = config.minutos_cancelamento if config else 60

        inicio, fim_pre_reserva, fim = JanelaReservaModel.calcular_limites(
            self.data,
            hora_abre,
            hora_fecha,
            hora_fecha_pre,
        )

        return {
            'inicio': inicio,
            'inicio_pre_reserva': inicio,
            'fim': fim,
            'fim_pre_reserva': fim_pre_reserva,
            'hora_abre': hora_abre,
            'hora_fecha': hora_fecha,
            'hora_fecha_pre': hora_fecha_pre,
            'minutos_cancelamento': minutos_cancelamento,
        }

    @property
    def abertura_reserva_display(self):
        limites = self.get_janela_reserva()
        if not limites: return "Não definida"
        return f"{limites['inicio'].strftime('%d/%m')} às {limites['hora_abre'].strftime('%H:%M')}"

    @property
    def fechamento_reserva_display(self):
        limites = self.get_janela_reserva()
        if not limites: return "Não definida"
        return f"{limites['fim'].strftime('%d/%m')} às {limites['hora_fecha'].strftime('%H:%M')}"

    def get_status_reserva(self):
        """Retorna uma string descritiva do status atual para o aluno."""
        if not self.exige_reserva:
            return "Informativa"
        
        limites = self.get_janela_reserva()
        if not limites:
            return "Disponível"

        agora = timezone.localtime()
        abertura_str = self.abertura_reserva_display
        fechamento_str = self.fechamento_reserva_display

        if agora < limites['inicio']:
            return f"Reservas abrem em {abertura_str}"
        elif limites['inicio'] <= agora <= limites['fim']:
            return f"Aberta! Fecha em {fechamento_str}"
        else:
            return f"Encerrada (Prazo: {fechamento_str})"

    @property
    def reserva_aberta(self):
        """Retorna True se a janela de reserva está aberta no momento."""
        limites = self.get_janela_reserva()
        if not limites: return True
        return limites['inicio'] <= timezone.localtime() <= limites['fim']

    @property
    def periodo_pre_reserva_ativo(self):
        """True enquanto houver pré-reservas pendentes dentro do prazo de confirmação."""
        if not self.pre_reservas_disparadas_em:
            return False
        limites = self.get_janela_reserva()
        if not limites:
            return False
        agora = timezone.now()
        if agora >= limites['fim_pre_reserva']:
            return False
        return self.pre_reservas.filter(
            status='pendente',
            expira_em__gt=agora,
        ).exists()

    def get_limite_cancelamento(self):
        """
        Retorna o datetime limite para cancelamento pelo aluno.
        Usa o início da refeição como referência; se não configurado, cai no
        fechamento da janela de reserva.
        """
        from administrativo.models import TipoRefeicao

        limites = self.get_janela_reserva()
        if not limites:
            return None

        minutos = limites['minutos_cancelamento']
        tz = timezone.get_current_timezone()
        tipo = TipoRefeicao.objects.filter(nome__iexact=self.tipo).first()
        if tipo and tipo.horario_inicio_consumo:
            inicio_refeicao = timezone.make_aware(
                datetime.combine(self.data, tipo.horario_inicio_consumo),
                tz,
            )
            return inicio_refeicao - timedelta(minutes=minutos)

        return limites['fim'] - timedelta(minutes=minutos)

    @property
    def pode_cancelar(self):
        """Verifica se ainda é permitido cancelar a reserva baseado no prazo de minutos."""
        limite_cancelamento = self.get_limite_cancelamento()
        if limite_cancelamento is None:
            return True
        return timezone.localtime() <= limite_cancelamento

    @property
    def reserva_futura(self):
        """Retorna True se a reserva ainda não abriu."""
        limites = self.get_janela_reserva()
        if not limites: return False
        return timezone.localtime() < limites['inicio']

    @property
    def reserva_encerrada(self):
        """Retorna True se o prazo de reserva já expirou."""
        limites = self.get_janela_reserva()
        if not limites: return False
        return timezone.localtime() > limites['fim']
    
    @property
    def refeicao_iniciada(self):
        """Retorna true se alguma presença foi registrada para esta refeição."""
        from administrativo.models import Presenca
        return Presenca.objects.filter(
            reserva__refeicao=self
        ).exists()

    def clean(self):
        super().clean()
        if self.pk:
            reservas_ativas = self.reservas_ativas_count
            if self.limite_vagas < reservas_ativas:
                raise ValidationError({
                    'limite_vagas': (
                        f'O limite não pode ser menor que {reservas_ativas} '
                        f'(número de reservas ativas).'
                    ),
                })


class RefeicaoPrato(UUIDModel):
    refeicao = models.ForeignKey(Refeicao, on_delete=models.CASCADE, related_name='itens_prato')
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE, related_name='refeicoes_vinculadas')

    class Meta:
        verbose_name = 'Prato da refeição'
        verbose_name_plural = 'Pratos da refeição'
        constraints = [
            models.UniqueConstraint(fields=['refeicao', 'prato'], name='unique_refeicao_prato'),
        ]

    def __str__(self):
        return f'{self.refeicao} — {self.prato}'
