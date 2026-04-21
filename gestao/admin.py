from django.contrib import admin

from .models import Cliente, Vendedor, Funcionario, Atividade, Reserva, ClienteReserva, Pagamento, Caixa

# Registrando as tabelas básicas
admin.site.register(Cliente)
admin.site.register(Vendedor)
admin.site.register(Funcionario)
admin.site.register(Atividade)
admin.site.register(Pagamento)
admin.site.register(Caixa)

# Essa estrutura abaixo permite ver os clientes DENTRO da tela da Reserva (Inline)
class ClienteReservaInline(admin.TabularInline):
    model = ClienteReserva
    extra = 1 # Quantidade de linhas em branco que aparecem por padrão

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('data', 'embarcacao', 'vendedor', 'situacao')
    list_filter = ('data', 'vendedor', 'situacao')
    inlines = [ClienteReservaInline]