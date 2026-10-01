import uuid

from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from catalogo.cesta import CHAVE_CESTA
from .forms import CheckoutForm
from .models import ConfiguracaoLoja, Pedido
from .services import cotar, link_whatsapp, registrar_pedido

SALT = "pedidos.confirmacao"


def dono(request):
    if not request.session.session_key:
        request.session.create()
    return salted_hmac("pedidos.sessao", request.session.session_key, algorithm="sha256").hexdigest()


def assinar(request, resumo, sessao_hash):
    chave = request.session.get("chave_checkout")
    if not chave or Pedido.objects.filter(chave_checkout=chave).exists():
        chave = str(uuid.uuid4())
        request.session["chave_checkout"] = chave
    return signing.dumps({"chave": chave, "dono": sessao_hash, "resumo": resumo}, salt=SALT, compress=True)


@never_cache
@require_http_methods(["GET", "POST"])
def checkout(request):
    sessao_hash = dono(request)
    cesta = request.session.get(CHAVE_CESTA, {})
    form = CheckoutForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        try:
            confirmacao = signing.loads(request.POST.get("confirmacao", ""), salt=SALT, max_age=86400)
            if confirmacao["dono"] != sessao_hash:
                raise signing.BadSignature()
        except (signing.BadSignature, KeyError, TypeError):
            form.is_valid()
            form.add_error(None, "A confirmação expirou ou é inválida. Revise os dados e tente novamente.")
        else:
            existente = Pedido.objects.filter(chave_checkout=confirmacao["chave"], sessao_hash=sessao_hash).first()
            if existente:
                return redirect("pedidos:confirmacao", chave=existente.chave_checkout)
            if form.is_valid():
                dados = {campo: form.cleaned_data[campo] for campo in CheckoutForm.Meta.fields}
                try:
                    pedido = registrar_pedido(dados, cesta, confirmacao, sessao_hash)
                except ValidationError as erro:
                    form.add_error(None, " ".join(erro.messages))
                except OperationalError:
                    form.add_error(None, "O sistema está ocupado. Aguarde um instante e tente novamente.")
                else:
                    request.session[CHAVE_CESTA] = {}
                    return redirect("pedidos:confirmacao", chave=pedido.chave_checkout)
    try:
        itens, subtotal, resumo = cotar(cesta)
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
        return redirect("catalogo:cesta")
    token = assinar(request, resumo, sessao_hash)
    if form.is_bound:
        # Renova a confirmação com os valores agora mostrados, preservando os dados.
        dados_form = form.data.copy()
        dados_form["confirmacao"] = token
        dados_form["revisar"] = ""
        form.data = dados_form
    else:
        form.initial["confirmacao"] = token
    return render(request, "pedidos/checkout.html", {
        "form": form, "itens": itens, "subtotal": subtotal,
        "cesta_contagem": len(cesta), "loja": ConfiguracaoLoja.objects.filter(pk=1).first(),
    })


@never_cache
@require_GET
def confirmacao(request, chave):
    if not request.session.session_key:
        raise Http404
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("itens"), chave_checkout=chave, sessao_hash=dono(request),
    )
    return render(request, "pedidos/confirmacao.html", {
        "pedido": pedido, "whatsapp_url": link_whatsapp(pedido),
        "cesta_contagem": len(request.session.get(CHAVE_CESTA, {})),
    })
