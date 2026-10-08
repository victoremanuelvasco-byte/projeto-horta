from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.views.decorators.http import require_GET, require_POST

from .cesta import CHAVE_CESTA, resumo_cesta, validar_quantidade
from .models import OpcaoVenda, Produto


@require_GET
def catalogo(request):
    produtos = Produto.objects.filter(
        ativo=True, opcoes_venda__disponivel=True,
    ).distinct().select_related("categoria").prefetch_related(
        Prefetch("opcoes_venda", queryset=OpcaoVenda.objects.filter(disponivel=True))
    )
    for produto in produtos:
        produto.escolher_preparo = any(opcao.preparo for opcao in produto.opcoes_venda.all())
    return render(request, "catalogo/catalogo.html", {
        "produtos": produtos,
        "cesta_contagem": len(request.session.get(CHAVE_CESTA, {})),
    })


@require_GET
def cesta(request):
    return render(request, "catalogo/cesta.html", resumo_cesta(request.session))


@require_POST
def adicionar(request, opcao_id):
    opcao = get_object_or_404(OpcaoVenda, pk=opcao_id, disponivel=True, produto__ativo=True)
    itens = request.session.get(CHAVE_CESTA, {}).copy()
    try:
        quantidade = validar_quantidade(request.POST.get("quantidade", ""), opcao.unidade)
        anterior = itens.get(str(opcao.pk), "0")
        quantidade = validar_quantidade(quantidade + Decimal(anterior), opcao.unidade)
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
        return redirect("catalogo:inicio")
    itens[str(opcao.pk)] = str(quantidade)
    request.session[CHAVE_CESTA] = itens
    messages.success(request, f"{opcao.nome_produto} adicionado à cesta.")
    return redirect("catalogo:cesta")


@require_POST
def adicionar_produto(request, produto_id):
    try:
        opcao_id = int(request.POST.get('opcao', ''))
    except (TypeError, ValueError):
        raise Http404('Opção inválida.')
    opcao = get_object_or_404(OpcaoVenda, pk=opcao_id, produto_id=produto_id, disponivel=True, produto__ativo=True)
    return adicionar(request, opcao.pk)


@require_POST
def atualizar(request, opcao_id):
    itens = request.session.get(CHAVE_CESTA, {}).copy()
    if str(opcao_id) not in itens:
        return redirect("catalogo:cesta")
    opcao = get_object_or_404(OpcaoVenda, pk=opcao_id, disponivel=True, produto__ativo=True)
    try:
        quantidade = validar_quantidade(request.POST.get("quantidade", ""), opcao.unidade)
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
    else:
        itens[str(opcao_id)] = str(quantidade)
        request.session[CHAVE_CESTA] = itens
        messages.success(request, "Quantidade atualizada.")
    return redirect("catalogo:cesta")


@require_POST
def remover(request, opcao_id):
    itens = request.session.get(CHAVE_CESTA, {}).copy()
    itens.pop(str(opcao_id), None)
    request.session[CHAVE_CESTA] = itens
    messages.success(request, "Item removido da cesta.")
    return redirect("catalogo:cesta")
