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
    limite_vagas = models.IntegerField()
    exige_reserva = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
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
    def descricao_exibicao(self):
        pratos = [item.prato for item in self.itens_prato.select_related('prato').all()]
        if not pratos:
            return ''

        ordem = {cat: i for i, cat in enumerate(Prato.ORDEM_CATEGORIAS)}
        pratos.sort(key=lambda p: (ordem.get(p.categoria, 99), p.nome))

        por_categoria = {}
        for prato in pratos:
            texto = (prato.descricao or prato.nome).strip()
            if not texto:
                continue
            por_categoria.setdefault(prato.categoria, []).append(texto)

        partes = []
        for cat in Prato.ORDEM_CATEGORIAS:
            if cat not in por_categoria:
                continue
            label = dict(Prato.CATEGORIAS).get(cat, cat)
            nomes = ', '.join(por_categoria[cat])
            partes.append(f'{label}: {nomes}')
        return ' · '.join(partes)

    @property
    def descricao(self):
        return self.descricao_exibicao

    @property
    def vagas_disponiveis(self):
        return self.limite_vagas - self.reservas_ativas_count

    @property
    def vagas_display(self):
        """Retorna o texto das vagas com o aviso de expiração se necessário."""
        v = self.vagas_disponiveis
        # Pluralização em PT-BR: Apenas 1 é singular. 0 e > 1 são plural.
        v_word = "vaga" if v == 1 else "vagas"
        r_word = "restante" if v == 1 else "restantes"
        texto = f"{v} {v_word} {r_word}"

        if self.exige_reserva:
            if self.reserva_encerrada:
                return f"{texto} (Encerrada)"
            
            limites = self.get_janela_reserva()
            if limites:
                h_abre = limites['hora_abre'].strftime('%H:%M')
                h_fecha = limites['hora_fecha'].strftime('%H:%M')
                # Adiciona o horário ao lado das vagas sem quebrar o layout
                texto += f" | {h_abre} às {h_fecha}"
        return texto

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

        hora_abre = janela.horario_abertura if janela else config.abertura
        hora_fecha = janela.horario_fechamento if janela else config.encerramento
        minutos_cancelamento = config.minutos_cancelamento if config else 60

        # Local helpers para converter para datetime aware
        tz = timezone.get_current_timezone()
        inicio = timezone.make_aware(datetime.combine(self.data - timedelta(days=1), hora_abre), tz)
        fim = timezone.make_aware(datetime.combine(self.data, hora_fecha), tz)

        return {
            'inicio': inicio,
            'fim': fim,
            'hora_abre': hora_abre,
            'hora_fecha': hora_fecha,
            'minutos_cancelamento': minutos_cancelamento
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
