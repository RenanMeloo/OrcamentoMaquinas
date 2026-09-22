from django.urls import path
from . import views

app_name = 'orcamento'

urlpatterns = [
    # Rotas específicas primeiro (mais específicas que <str:numero>/)
    path('api/salvar/', views.api_salvar_orcamento, name='api_salvar'),
    path('pedidos/', views.listar_orcamentos, name='listar_pedidos'),
    path('clientes/novo/', views.criar_cliente, name='criar_cliente'),
    path('clientes/', views.listar_clientes, name='listar_clientes'),

    # Rotas genéricas por último
    path('<str:numero>/editar/', views.editar_orcamento, name='editar'),
    path('<str:numero>/duplicar/', views.duplicar_orcamento, name='duplicar'),
    path('<str:numero>/', views.visualizar_orcamento, name='visualizar'),
    path('', views.orcamento_form, name='form'),
]
