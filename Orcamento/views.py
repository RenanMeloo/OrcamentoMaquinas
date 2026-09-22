from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Q
import json
from datetime import datetime
from .models import Orcamento, Cliente, Frota, ItemOrcamento


def _orcamento_context_dict(orcamento):
    """Serializa um Orcamento + itens no mesmo formato usado pelo formulário (JS)"""
    itens = orcamento.itens.all()
    return {
        'tipo': orcamento.tipo,
        'data': orcamento.data_pedido.isoformat() if orcamento.data_pedido else '',
        'cliente': orcamento.cliente.nome,
        'maquina': orcamento.maquina or '',
        'placa': orcamento.frota.placa if orcamento.frota else '',
        'horimetro': orcamento.frota.horimetro if orcamento.frota else '',
        'local': orcamento.local or '',
        'observacoes': orcamento.observacoes or '',
        'pecas': [
            {'descricao': item.descricao, 'qtd': float(item.quantidade), 'valorUnit': float(item.valor_unitario)}
            for item in itens if item.tipo == 'peca'
        ],
        'servicos': [
            {'descricao': item.descricao, 'qtd': float(item.quantidade), 'valorUnit': float(item.valor_unitario)}
            for item in itens if item.tipo == 'servico'
        ],
    }


def _renderizar_formulario(request, modo, orcamento=None, numero_edicao=None):
    clientes = list(Cliente.objects.order_by('nome').values_list('nome', flat=True))
    context = {'clientes': clientes, 'pagina_ativa': 'orcamento', 'modo': modo}
    if orcamento is not None:
        context['dados_iniciais'] = _orcamento_context_dict(orcamento)
    if numero_edicao is not None:
        context['numero_edicao'] = numero_edicao
    return render(request, 'orcamento_novo.html', context)


def orcamento_form(request):
    """Renderiza o formulário de novo orçamento"""
    return _renderizar_formulario(request, modo='novo')


def editar_orcamento(request, numero):
    """Renderiza o formulário pré-preenchido para editar um orçamento existente"""
    orcamento = get_object_or_404(Orcamento, numero=numero)
    return _renderizar_formulario(request, modo='editar', orcamento=orcamento, numero_edicao=orcamento.numero)


def duplicar_orcamento(request, numero):
    """Renderiza o formulário pré-preenchido a partir de um orçamento existente, para criar um novo"""
    orcamento = get_object_or_404(Orcamento, numero=numero)
    return _renderizar_formulario(request, modo='duplicar', orcamento=orcamento)


# ========== CLIENTES ==========

def listar_clientes(request):
    """Lista todos os clientes"""
    clientes = Cliente.objects.all().order_by('-data_criacao')
    context = {
        'clientes': clientes,
        'total_clientes': clientes.count(),
        'pagina_ativa': 'clientes'
    }
    return render(request, 'clientes/listar_clientes.html', context)


def criar_cliente(request):
    """Cria um novo cliente"""
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()

        if not nome:
            messages.error(request, 'Nome do cliente é obrigatório!')
            return redirect('orcamento:criar_cliente')

        cliente = Cliente.objects.create(nome=nome)
        
        messages.success(request, f'Cliente "{nome}" criado com sucesso!')
        return redirect('orcamento:listar_clientes')
    
    context = {'pagina_ativa': 'clientes'}
    return render(request, 'clientes/criar_cliente.html', context)


# ========== PEDIDOS ==========

def listar_orcamentos(request):
    """Lista todos os orçamentos com filtro e busca"""
    orcamentos = Orcamento.objects.all().select_related('cliente', 'frota').order_by('-data_criacao')
    clientes = Cliente.objects.all().order_by('nome')
    
    # Filtro por cliente
    cliente_id = request.GET.get('cliente')
    if cliente_id:
        orcamentos = orcamentos.filter(cliente_id=cliente_id)
    
    # Filtro por status
    status = request.GET.get('status')
    if status:
        orcamentos = orcamentos.filter(status=status)
    
    # Busca por número ou cliente
    busca = request.GET.get('busca', '').strip()
    if busca:
        orcamentos = orcamentos.filter(
            Q(numero__icontains=busca) | 
            Q(cliente__nome__icontains=busca)
        )
    
    context = {
        'orcamentos': orcamentos,
        'clientes': clientes,
        'cliente_selecionado': cliente_id,
        'status_selecionado': status,
        'busca': busca,
        'total_orcamentos': orcamentos.count(),
        'pagina_ativa': 'pedidos',
        'status_choices': Orcamento.STATUS_CHOICES,
    }
    return render(request, 'pedidos/listar_orcamentos.html', context)


def _salvar_itens(orcamento, pecas, servicos):
    """Substitui os itens do orçamento pela lista atual de peças e serviços"""
    orcamento.itens.all().delete()
    novos_itens = [
        ItemOrcamento(orcamento=orcamento, tipo=tipo, descricao=item['descricao'],
                      quantidade=item['qtd'], valor_unitario=item['valorUnit'], ordem=ordem)
        for tipo, lista in (('peca', pecas), ('servico', servicos))
        for ordem, item in enumerate(lista)
    ]
    if novos_itens:
        ItemOrcamento.objects.bulk_create(novos_itens)


@csrf_exempt
@require_http_methods(["POST"])
def api_salvar_orcamento(request):
    """API para criar ou atualizar orçamento via AJAX"""
    try:
        data = json.loads(request.body)

        # Validar dados obrigatórios
        cliente_nome = data.get('cliente', '').strip()
        if not cliente_nome:
            return JsonResponse({'erro': 'Cliente é obrigatório'}, status=400)

        # Criar ou obter cliente
        cliente, created = Cliente.objects.get_or_create(
            nome=cliente_nome,
            defaults={'email': data.get('email', '')}
        )

        # Tentar obter frota se placa foi fornecida
        horimetro = None
        if data.get('horimetro') not in (None, ''):
            try:
                horimetro = int(float(data.get('horimetro')))
            except (TypeError, ValueError):
                return JsonResponse({'erro': 'Horímetro deve ser um número'}, status=400)

        frota = None
        if data.get('placa', '').strip():
            frota, _ = Frota.objects.get_or_create(
                placa=data.get('placa'),
                cliente=cliente,
                defaults={
                    'horimetro': horimetro or 0,
                    'descricao': data.get('maquina', '')
                }
            )
            # Mantém a frota atualizada com os dados mais recentes informados no pedido
            if horimetro is not None:
                frota.horimetro = horimetro
            if data.get('maquina', '').strip():
                frota.descricao = data.get('maquina')
            frota.save()

        # Data do pedido (campo "data" do formulário, formato YYYY-MM-DD)
        data_pedido = None
        if data.get('data'):
            try:
                data_pedido = datetime.strptime(data.get('data'), '%Y-%m-%d').date()
            except ValueError:
                data_pedido = None

        # Calcular valor total
        pecas = data.get('pecas', [])
        servicos = data.get('servicos', [])
        valor_total = sum(item['qtd'] * item['valorUnit'] for item in pecas + servicos)

        campos_comuns = {
            'cliente': cliente,
            'frota': frota,
            'tipo': data.get('tipo', 'ORÇAMENTO'),
            'data_pedido': data_pedido,
            'maquina': data.get('maquina', ''),
            'local': data.get('local', ''),
            'observacoes': data.get('observacoes', ''),
            'valor_total': valor_total,
        }

        numero_edicao = data.get('numero_edicao')
        if numero_edicao:
            # Modo edição: atualiza o orçamento existente
            orcamento = get_object_or_404(Orcamento, numero=numero_edicao)
            for campo, valor in campos_comuns.items():
                setattr(orcamento, campo, valor)
            orcamento.save()
            numero = orcamento.numero
        else:
            # Gerar número único para o orçamento
            # Formato: ORC-DDMMYYYY-XXXX (ORC-03092026-0001)
            data_fmt = datetime.now().strftime('%d%m%Y')
            count = Orcamento.objects.filter(numero__startswith=f'ORC-{data_fmt}').count()
            numero = f'ORC-{data_fmt}-{count + 1:04d}'

            orcamento = Orcamento.objects.create(numero=numero, status='rascunho', **campos_comuns)

        _salvar_itens(orcamento, pecas, servicos)

        return JsonResponse({
            'sucesso': True,
            'numero': numero,
            'url': f'/orcamento/{numero}/'
        })

    except json.JSONDecodeError:
        return JsonResponse({'erro': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


def visualizar_orcamento(request, numero):
    """Exibe um orçamento salvo"""
    orcamento = get_object_or_404(Orcamento, numero=numero)
    itens = orcamento.itens.all()

    context = {
        'orcamento': orcamento,
        'cliente': orcamento.cliente,
        'frota': orcamento.frota,
        'pecas': [item for item in itens if item.tipo == 'peca'],
        'servicos': [item for item in itens if item.tipo == 'servico'],
    }

    return render(request, 'visualizar_orcamento.html', context)

