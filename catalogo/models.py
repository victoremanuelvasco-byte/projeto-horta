from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos",
        verbose_name="categoria",
    )
    nome = models.CharField("nome", max_length=150)
    descricao = models.TextField("descrição", blank=True)
    foto = models.ImageField("foto", upload_to="produtos/", blank=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"

    def __str__(self):
        return self.nome


class OpcaoVenda(models.Model):
    class Unidade(models.TextChoices):
        MACO = "MACO", "Maço"
        KG = "KG", "Quilo"

    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="opcoes_venda",
        verbose_name="produto",
    )
    unidade = models.CharField("unidade", max_length=4, choices=Unidade.choices)
    preco = models.DecimalField(
        "preço (R$)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Preço por maço ou por quilo, conforme a unidade selecionada.",
    )
    disponivel = models.BooleanField("disponível", default=True)

    class Meta:
        ordering = ["produto__nome", "unidade"]
        verbose_name = "opção de venda"
        verbose_name_plural = "opções de venda"
        constraints = [
            models.UniqueConstraint(
                fields=["produto", "unidade"], name="catalogo_produto_unidade_unicos",
            ),
            models.CheckConstraint(
                condition=models.Q(preco__gt=0), name="catalogo_preco_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(unidade__in=["MACO", "KG"]),
                name="catalogo_unidade_valida",
            ),
        ]

    def __str__(self):
        return f"{self.produto} — {self.get_unidade_display()}"
