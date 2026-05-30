from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'perfil', 'turma', 'is_staff')
    list_filter = ('perfil', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'turma')

    fieldsets = UserAdmin.fieldsets + (
        ('Perfil ReservaIF', {'fields': ('perfil', 'turma')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil ReservaIF', {'fields': ('perfil', 'turma')}),
    )
