from django.contrib import admin

from .models import Categoria, OpcaoVenda, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


class OpcaoVendaInline(admin.TabularInline):
    model = OpcaoVenda
    extra = 1


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "ativo"]
    list_filter = ["ativo", "categoria"]
    search_fields = ["nome", "descricao"]
    list_select_related = ["categoria"]
    inlines = [OpcaoVendaInline]


@admin.register(OpcaoVenda)
class OpcaoVendaAdmin(admin.ModelAdmin):
    list_display = ["produto", "unidade", "preco", "disponivel"]
    list_filter = ["unidade", "disponivel"]
    search_fields = ["produto__nome"]
    list_select_related = ["produto"]
    autocomplete_fields = ["produto"]
