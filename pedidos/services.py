from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from catalogo.cesta import validar_quantidade
from catalogo.models import OpcaoVenda, Produto

from .models import ConfiguracaoLoja, ItemPedido, Pedido


def cotar(cesta, bloquear=False):
    if not cesta:
        raise ValidationError("Sua cesta está vazia.")
    consulta = OpcaoVenda.objects.select_related("produto").filter(pk__in=cesta).order_by("pk")
    if bloquear:
        # Bloqueia também os produtos para impedir desativação durante a gravação.
        list(Produto.objects.select_for_update().filter(opcoes_venda__pk__in=cesta).order_by("pk"))
        consulta = consulta.select_for_update()
    opcoes = list(consulta)
    if len(opcoes) != len(cesta) or any(not o.disponivel or not o.produto.ativo for o in opcoes):
        raise ValidationError("Há itens indisponíveis. Volte à cesta e remova esses itens antes de continuar.")
    itens = []
    subtotal = Decimal("0.00")
    for opcao in opcoes:
        quantidade = validar_quantidade(cesta[str(opcao.pk)], opcao.unidade)
        valor = (quantidade * opcao.preco).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += valor
        itens.append({
            "opcao": opcao, "quantidade": quantidade, "subtotal": valor,
            "nome_produto": opcao.produto.nome, "unidade": opcao.unidade,
            "preco_unitario": opcao.preco,
        })
    resumo = [
        [str(i["opcao"].pk), str(i["quantidade"]), str(i["preco_unitario"]), i["nome_produto"], i["unidade"]]
        for i in itens
    ]
    return itens, subtotal, resumo


def registrar_pedido(dados, cesta, confirmacao, sessao_hash):
    chave = confirmacao["chave"]
    existente = Pedido.objects.filter(chave_checkout=chave, sessao_hash=sessao_hash).first()
    if existente:
        return existente
    try:
        with transaction.atomic():
            itens, subtotal, resumo = cotar(cesta, bloquear=True)
            if resumo != confirmacao["resumo"]:
                raise ValidationError("Sua cesta ou os preços mudaram. Revise os valores atualizados e confirme novamente.")
            pedido = Pedido(
                **dados, chave_checkout=chave, sessao_hash=sessao_hash,
                subtotal_produtos=subtotal,
                taxa_entrega=Decimal("0.00") if dados["modalidade"] == "RETIRADA" else None,
            )
            pedido.full_clean()
            pedido.save()
            for item in itens:
                linha = ItemPedido(
                    pedido=pedido, opcao_venda=item["opcao"],
                    nome_produto=item["nome_produto"], unidade=item["unidade"],
                    preco_unitario=item["preco_unitario"], quantidade=item["quantidade"],
                    subtotal=item["subtotal"],
                )
                linha.full_clean()
                linha.save()
            return pedido
    except (IntegrityError, ValidationError):
        existente = Pedido.objects.filter(chave_checkout=chave, sessao_hash=sessao_hash).first()
        if existente:
            return existente
        raise


def dinheiro(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


def mensagem_whatsapp(pedido):
    linhas = [
        f"Olá! Meu pedido é {pedido.numero}.",
        f"Cliente: {pedido.nome_cliente}",
        f"Contato: {pedido.telefone_cliente}", "",
    ]
    for item in pedido.itens.all():
        quantidade = format(item.quantidade, "f").rstrip("0").rstrip(".").replace(".", ",")
        unidade = "kg" if item.unidade == "KG" else "maço(s)"
        linhas.append(f"- {item.nome_produto}: {quantidade} {unidade} x {dinheiro(item.preco_unitario)} = {dinheiro(item.subtotal)}")
    linhas += ["", f"Subtotal dos produtos: {dinheiro(pedido.subtotal_produtos)}", f"Recebimento: {pedido.get_modalidade_display()}"]
    if pedido.modalidade == "ENTREGA":
        linhas.append(f"Endereço: {pedido.logradouro}, {pedido.numero_endereco}; {pedido.bairro}; {pedido.cidade}/{pedido.uf}")
        for rotulo, campo in [("CEP", "cep"), ("Complemento", "complemento"), ("Referência", "referencia")]:
            if getattr(pedido, campo):
                linhas.append(f"{rotulo}: {getattr(pedido, campo)}")
        if pedido.taxa_entrega is None:
            linhas.append("Entrega a combinar pelo WhatsApp.")
        else:
            linhas.append(f"Taxa de entrega: {dinheiro(pedido.taxa_entrega)}")
    if pedido.total is not None:
        linhas.append(f"Total: {dinheiro(pedido.total)}")
    linhas.append(f"Forma de pagamento: {pedido.get_forma_pagamento_display()} (pagamento fora do site).")
    if pedido.observacoes:
        linhas.append(f"Observações: {pedido.observacoes}")
    linhas.append("Aguardo a confirmação do vendedor.")
    return "\n".join(linhas)


def link_whatsapp(pedido):
    config = ConfiguracaoLoja.objects.filter(pk=1).first()
    if not config or not config.whatsapp:
        return None
    return f"https://wa.me/{config.whatsapp}?" + urlencode({"text": mensagem_whatsapp(pedido)})
