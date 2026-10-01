import re
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from catalogo.models import OpcaoVenda


def gerar_numero():
    return "H-" + uuid.uuid4().hex[:12].upper()


def validar_whatsapp(valor):
    if valor and not re.fullmatch(r"55[1-9][0-9]{9,10}", valor):
        raise ValidationError("Use somente números, incluindo 55 e DDD. Exemplo: 5592999999999.")


class ConfiguracaoLoja(models.Model):
    whatsapp = models.CharField(
        "WhatsApp do vendedor", max_length=13, blank=True, validators=[validar_whatsapp],
        help_text="Somente números: 55 + DDD + telefone.",
    )
    cidade_entrega = models.CharField("cidade atendida", max_length=100, blank=True)
    uf_entrega = models.CharField("UF atendida", max_length=2, blank=True)
    regiao_entrega = models.CharField(
        "informações sobre a região de entrega", max_length=300, blank=True,
        help_text="Texto exibido ao cliente. A disponibilidade será confirmada pelo vendedor.",
    )

    class Meta:
        verbose_name = "configuração da loja"
        verbose_name_plural = "configuração da loja"

    def clean(self):
        super().clean()
        if bool(self.cidade_entrega) != bool(self.uf_entrega):
            raise ValidationError("Preencha a cidade e a UF juntas.")
        if self.uf_entrega:
            self.uf_entrega = self.uf_entrega.upper()
            if self.uf_entrega not in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split():
                raise ValidationError({"uf_entrega": "Informe uma UF valida."})

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Contato e entrega"


class Pedido(models.Model):
    class Modalidade(models.TextChoices):
        ENTREGA = "ENTREGA", "Entrega"
        RETIRADA = "RETIRADA", "Retirada"

    class Pagamento(models.TextChoices):
        CARTAO = "CARTAO", "Cartão"
        PIX = "PIX", "Pix"
        DINHEIRO = "DINHEIRO", "Dinheiro"

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente de confirmação"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        CANCELADO = "CANCELADO", "Cancelado"

    numero = models.CharField("número", max_length=14, unique=True, default=gerar_numero, editable=False)
    chave_checkout = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    sessao_hash = models.CharField(max_length=64, editable=False)
    nome_cliente = models.CharField("nome", max_length=120)
    telefone_cliente = models.CharField("telefone / WhatsApp", max_length=13)
    modalidade = models.CharField("recebimento", max_length=8, choices=Modalidade.choices)
    forma_pagamento = models.CharField("forma de pagamento", max_length=8, choices=Pagamento.choices)
    cep = models.CharField("CEP", max_length=9, blank=True)
    logradouro = models.CharField("rua / avenida", max_length=180, blank=True)
    numero_endereco = models.CharField("número (ou S/N)", max_length=20, blank=True)
    complemento = models.CharField("complemento", max_length=120, blank=True)
    bairro = models.CharField("bairro", max_length=100, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    referencia = models.CharField("ponto de referência", max_length=200, blank=True)
    observacoes = models.TextField("observações do cliente", max_length=1000, blank=True)
    status = models.CharField("status", max_length=10, choices=Status.choices, default=Status.PENDENTE)
    subtotal_produtos = models.DecimalField("subtotal dos produtos", max_digits=20, decimal_places=2)
    taxa_entrega = models.DecimalField(
        "taxa de entrega", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Em branco: a combinar. Zero: sem cobrança de entrega.",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [
            models.CheckConstraint(condition=models.Q(subtotal_produtos__gte=0), name="pedido_subtotal_nao_negativo"),
            models.CheckConstraint(
                condition=models.Q(taxa_entrega__isnull=True) | models.Q(taxa_entrega__gte=0),
                name="pedido_taxa_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(modalidade="ENTREGA") | models.Q(modalidade="RETIRADA", taxa_entrega=0, taxa_entrega__isnull=False),
                name="pedido_retirada_taxa_zero",
            ),
        ]

    def clean(self):
        super().clean()
        if self.modalidade == self.Modalidade.RETIRADA and self.taxa_entrega != Decimal("0"):
            raise ValidationError({"taxa_entrega": "Pedidos para retirada devem ter taxa zero."})
        if self.modalidade == self.Modalidade.ENTREGA:
            campos = ["logradouro", "numero_endereco", "bairro", "cidade", "uf"]
            erros = {campo: "Informe este campo para entrega." for campo in campos if not getattr(self, campo)}
            if erros:
                raise ValidationError(erros)

    @property
    def total(self):
        if self.taxa_entrega is None:
            return None
        return self.subtotal_produtos + self.taxa_entrega

    def __str__(self):
        return self.numero


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    opcao_venda = models.ForeignKey(OpcaoVenda, on_delete=models.PROTECT, related_name="itens_pedidos")
    nome_produto = models.CharField("produto", max_length=150)
    unidade = models.CharField("unidade", max_length=4, choices=OpcaoVenda.Unidade.choices)
    preco_unitario = models.DecimalField("preço unitário", max_digits=10, decimal_places=2)
    quantidade = models.DecimalField("quantidade solicitada", max_digits=9, decimal_places=3)
    subtotal = models.DecimalField("subtotal", max_digits=20, decimal_places=2)

    class Meta:
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="item_quantidade_positiva"),
            models.CheckConstraint(condition=models.Q(preco_unitario__gt=0), name="item_preco_positivo"),
            models.CheckConstraint(condition=models.Q(subtotal__gte=0), name="item_subtotal_nao_negativo"),
        ]

    def __str__(self):
        return self.nome_produto
