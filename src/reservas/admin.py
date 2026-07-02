from django.contrib import admin
from .models import Reserva

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'refeicao', 'status', 'reservado_em')
    list_filter = ('status', 'refeicao__data', 'refeicao__tipo')
    search_fields = ('aluno__username', 'aluno__first_name', 'aluno__last_name', 'aluno__turma__nome')
    readonly_fields = ('reservado_em', 'cancelado_em')
    
    def get_queryset(self, request):
        # Otimiza a consulta no admin trazendo os dados relacionados de uma vez
        return super().get_queryset(request).select_related('aluno', 'refeicao')
