from django.contrib import admin
from .models import Cliente, Frota, Orcamento, ItemOrcamento


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'telefone', 'cnpj', 'data_criacao']
    list_filter = ['data_criacao']
    search_fields = ['nome', 'email', 'cnpj']
    ordering = ['-data_criacao']


@admin.register(Frota)
class FrotaAdmin(admin.ModelAdmin):
    list_display = ['placa', 'cliente', 'horimetro', 'data_criacao']
    list_filter = ['cliente', 'data_criacao']
    search_fields = ['placa', 'cliente__nome']
    ordering = ['-data_criacao']


class ItemOrcamentoInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'status', 'valor_total', 'data_criacao']
    list_filter = ['status', 'data_criacao', 'cliente']
    search_fields = ['numero', 'cliente__nome']
    ordering = ['-data_criacao']
    readonly_fields = ['numero', 'data_criacao', 'data_atualizacao']
    inlines = [ItemOrcamentoInline]

