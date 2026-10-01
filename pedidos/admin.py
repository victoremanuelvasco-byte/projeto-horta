from django.contrib import admin

from .models import ConfiguracaoLoja, ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    fields = ["nome_produto", "unidade", "preco_unitario", "quantidade", "subtotal"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["numero", "nome_cliente", "modalidade", "forma_pagamento", "status", "subtotal_produtos", "taxa_entrega", "total", "criado_em"]
    list_filter = ["status", "modalidade", "forma_pagamento", "criado_em"]
    search_fields = ["numero", "nome_cliente", "telefone_cliente"]
    inlines = [ItemPedidoInline]
    readonly_fields = [
        "numero", "nome_cliente", "telefone_cliente", "modalidade", "forma_pagamento",
        "cep", "logradouro", "numero_endereco", "complemento", "bairro", "cidade", "uf",
        "referencia", "observacoes", "subtotal_produtos", "total", "criado_em", "atualizado_em",
    ]
    fields = readonly_fields + ["status", "taxa_entrega"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracaoLoja)
class ConfiguracaoLojaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracaoLoja.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
