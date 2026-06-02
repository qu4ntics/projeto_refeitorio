from django.db import models


# Modelo de refeição disponível para reserva
class Refeicao(models.Model):
    TIPOS = [
        ('cafe', 'Café'),
        ('lanche_manha', 'Lanche da Manhã'),
        ('almoco', 'Almoço'),
        ('lanche_tarde', 'Lanche da Tarde'),
        ('jantar', 'Jantar'),
    ]

    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descricao = models.TextField()
    limite_vagas = models.IntegerField()
    exige_reserva = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Refeição'
        verbose_name_plural = 'Refeições'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.data}'

    @property
    def vagas_disponiveis(self):
        """Retorna vagas livres com base nas reservas ativas vinculadas."""
        reservas_ativas = self.reservas.filter(status='ativa').count()
        return self.limite_vagas - reservas_ativas
