import re
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError

from .models import OpcaoVenda

CHAVE_CESTA = "cesta"
LIMITE_QUANTIDADE = Decimal("999999.999")


def validar_quantidade(valor, unidade):
    texto = str(valor).strip().replace(",", ".")
    if len(texto) > 16 or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,3})?", texto):
        raise ValidationError("Informe uma quantidade válida, com até três casas decimais.")
    quantidade = Decimal(texto)
    if quantidade <= 0 or quantidade > LIMITE_QUANTIDADE:
        raise ValidationError("A quantidade deve ser maior que zero e no máximo 999999,999.")
    if unidade == OpcaoVenda.Unidade.MACO and quantidade != quantidade.to_integral_value():
        raise ValidationError("Para maços, informe uma quantidade inteira.")
    return quantidade


def resumo_cesta(session):
    cesta = session.get(CHAVE_CESTA, {})
    opcoes = {
        str(opcao.pk): opcao
        for opcao in OpcaoVenda.objects.select_related("produto").filter(pk__in=cesta)
    }
    itens = []
    subtotal = Decimal("0.00")
    for chave, valor in cesta.items():
        opcao = opcoes.get(chave)
        disponivel = bool(opcao and opcao.disponivel and opcao.produto.ativo)
        quantidade = Decimal(valor)
        total = (
            (quantidade * opcao.preco).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if disponivel else None
        )
        if total is not None:
            subtotal += total
        itens.append({
            "id": chave, "opcao": opcao, "quantidade": quantidade,
            "quantidade_input": format(quantidade, "f"), "subtotal": total,
            "disponivel": disponivel,
        })
    return {"itens": itens, "subtotal": subtotal, "cesta_contagem": len(cesta)}
