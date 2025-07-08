from django.contrib import admin
from .models import Fazenda, UsuarioFazenda, Talhao, Plantio, Cultura

@admin.register(Fazenda)
class FazendaAdmin(admin.ModelAdmin):
    list_display = ('id_fazenda', 'nome', 'proprietario', 'uf', 'cidade', 'email', 'telefone', 'tamanho')
    search_fields = ('nome', 'proprietario', 'cidade', 'email')

@admin.register(UsuarioFazenda)
class UsuarioFazendaAdmin(admin.ModelAdmin):
    list_display = ('fazenda', 'usuario', 'nivel_acesso')
    search_fields = ('fazenda__nome', 'usuario__usuario_nome',)

admin.site.register(Talhao)
admin.site.register(Plantio)
admin.site.register(Cultura)