from django.contrib import admin

from usuario.models import Usuario

# Register your models here.
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario_id', 'usuario_nome', 'usuario_email', 'usuario_dtCriacao')

admin.site.register(Usuario, UsuarioAdmin)