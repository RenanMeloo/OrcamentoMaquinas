from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    nome = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    cnpj = models.CharField(max_length=18, unique=True, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['nome']
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
    
    def __str__(self):
        return self.nome


class Frota(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='frota')
    placa = models.CharField(max_length=10, unique=True)
    horimetro = models.IntegerField(default=0, help_text="Horímetro em horas")
    descricao = models.CharField(max_length=255, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['placa']
        verbose_name = "Frota"
        verbose_name_plural = "Frota"
    
    def __str__(self):
        return f"{self.placa} - {self.cliente.nome}"


class Orcamento(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('enviado', 'Enviado'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('concluido', 'Concluído'),
    ]

    TIPO_CHOICES = [
        ('ORÇAMENTO', 'Orçamento'),
        ('OS', 'Ordem de Serviço'),
    ]

    numero = models.CharField(max_length=50, unique=True, db_index=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='orcamentos')
    frota = models.ForeignKey(Frota, on_delete=models.SET_NULL, null=True, blank=True, related_name='orcamentos')

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='ORÇAMENTO')
    data_pedido = models.DateField(null=True, blank=True)
    maquina = models.CharField(max_length=255, blank=True, null=True)
    local = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    observacoes = models.TextField(blank=True, null=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        indexes = [
            models.Index(fields=['cliente', '-data_criacao']),
            models.Index(fields=['numero']),
        ]
    
    def __str__(self):
        return f"Orcamento #{self.numero} - {self.cliente.nome}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('orcamento:visualizar', kwargs={'numero': self.numero})


class ItemOrcamento(models.Model):
    TIPO_CHOICES = [
        ('peca', 'Peça/Produto'),
        ('servico', 'Serviço'),
    ]

    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=500)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['tipo', 'ordem', 'id']
        verbose_name = "Item do Orçamento"
        verbose_name_plural = "Itens do Orçamento"

    def __str__(self):
        return f"{self.descricao} ({self.orcamento.numero})"

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario

