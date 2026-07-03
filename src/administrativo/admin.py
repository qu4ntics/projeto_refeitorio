from django.contrib import admin

from .models import ConfigReserva, Presenca, Strike, Turma


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'turno', 'dias_contraturno', 'ativo')
    list_filter = ('turno', 'ativo')
    search_fields = ('nome',)


@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'compareceu', 'confirmado_por', 'confirmado_em')


@admin.register(Strike)
class StrikeAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'expira_em', 'aplicado_em')


@admin.register(ConfigReserva)
class ConfigReservaAdmin(admin.ModelAdmin):
    list_display = ('vigente_desde', 'abertura', 'encerramento', 'minutos_cancelamento', 'criado_por')
