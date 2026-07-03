from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'perfil', 'turma', 'is_staff')
    list_filter = ('perfil', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'turma__nome')

    fieldsets = UserAdmin.fieldsets + (
        ('Perfil ReservaIF', {'fields': ('perfil', 'turma', 'bloqueado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil ReservaIF', {'fields': ('perfil', 'turma', 'bloqueado')}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.perfil != 'aluno':
            fieldsets = list(fieldsets)
            perfil_fields = list(fieldsets[-1])
            perfil_fields[1]['fields'] = tuple(
                f for f in perfil_fields[1]['fields'] if f != 'turma'
            )
            fieldsets[-1] = tuple(perfil_fields)
        return fieldsets
