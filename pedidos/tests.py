from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from catalogo.models import Categoria, OpcaoVenda, Produto
from .forms import CheckoutForm
from .models import ConfiguracaoLoja, ItemPedido, Pedido
from .services import link_whatsapp, mensagem_whatsapp


class PedidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nome="Folhagens")
        cls.produto = Produto.objects.create(nome="Couve", categoria=categoria)
        cls.opcao = OpcaoVenda.objects.create(produto=cls.produto, unidade="KG", preco="10.05")
        ConfiguracaoLoja.objects.create(whatsapp="5569999999999")

    def preparar(self):
        self.client.post(reverse("catalogo:adicionar", args=[self.opcao.pk]), {"quantidade": "0.100"})
        response = self.client.get(reverse("pedidos:checkout"))
        self.assertEqual(response.status_code, 200)
        return response.context["form"]["confirmacao"].value()

    def dados(self, token, **extras):
        return {
            "confirmacao": token, "nome_cliente": "Cliente Teste",
            "telefone_cliente": "(69) 99999-9999", "modalidade": "RETIRADA",
            "forma_pagamento": "PIX", "revisar": "on", **extras,
        }

    def enviar(self, dados):
        return self.client.post(reverse("pedidos:checkout"), dados, follow=True)

    def test_retirada_grava_itens_e_limpa_cesta(self):
        response = self.enviar(self.dados(self.preparar()))
        self.assertEqual(Pedido.objects.count(), 1)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.subtotal_produtos, Decimal("1.01"))
        self.assertEqual(pedido.taxa_entrega, Decimal("0.00"))
        self.assertEqual(pedido.status, "PENDENTE")
        self.assertEqual(pedido.itens.count(), 1)
        self.assertEqual(pedido.telefone_cliente, "5569999999999")
        self.assertEqual(self.client.session["cesta"], {})
        self.assertContains(response, "Abrir pedido no WhatsApp")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_entrega_exige_endereco_e_frete_fica_a_combinar(self):
        dados = self.dados(self.preparar(), modalidade="ENTREGA")
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertIn("logradouro", response.context["form"].errors)
        dados.update(logradouro="Rua Teste", numero_endereco="S/N", bairro="Centro", cidade="Cidade Teste", uf="RO")
        response = self.enviar(dados)
        pedido = Pedido.objects.get()
        self.assertIsNone(pedido.taxa_entrega)
        self.assertIsNone(pedido.total)
        self.assertContains(response, "Entrega a combinar")
        self.assertNotIn("Total:", mensagem_whatsapp(pedido))

    def test_reenvio_nao_duplica_e_nao_apaga_nova_cesta(self):
        dados = self.dados(self.preparar())
        self.enviar(dados)
        self.client.post(reverse("catalogo:adicionar", args=[self.opcao.pk]), {"quantidade": "1"})
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(self.client.session["cesta"][str(self.opcao.pk)], "1")
        self.assertContains(response, Pedido.objects.get().numero)

    def test_preco_alterado_exige_nova_confirmacao(self):
        dados = self.dados(self.preparar())
        self.opcao.preco = Decimal("20.00")
        self.opcao.save()
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(response, "preços mudaram")
        self.assertFalse(response.context["form"]["revisar"].value())
        dados["confirmacao"] = response.context["form"]["confirmacao"].value()
        self.enviar(dados)
        self.assertEqual(Pedido.objects.get().subtotal_produtos, Decimal("2.00"))

    def test_cesta_alterada_exige_revisao(self):
        dados = self.dados(self.preparar())
        self.client.post(reverse("catalogo:adicionar", args=[self.opcao.pk]), {"quantidade": "1"})
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(response, "Revise os valores")

    def test_indisponivel_impede_pedido(self):
        dados = self.dados(self.preparar())
        self.opcao.disponivel = False
        self.opcao.save()
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(response, "indisponíveis")

    def test_valores_enviados_pelo_cliente_sao_ignorados(self):
        dados = self.dados(self.preparar(), subtotal_produtos="0", taxa_entrega="999", status="CONCLUIDO")
        self.enviar(dados)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.subtotal_produtos, Decimal("1.01"))
        self.assertEqual(pedido.taxa_entrega, Decimal("0.00"))
        self.assertEqual(pedido.status, "PENDENTE")

    def test_token_adulterado_e_de_outra_sessao_sao_rejeitados(self):
        token = self.preparar()
        response = self.enviar(self.dados(token + "alterado"))
        self.assertContains(response, "inválida")
        outro = Client()
        outro.post(reverse("catalogo:adicionar", args=[self.opcao.pk]), {"quantidade": "0.100"})
        response = outro.post(reverse("pedidos:checkout"), self.dados(token), follow=True)
        self.assertContains(response, "inválida")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_confirmacao_privada(self):
        response = self.enviar(self.dados(self.preparar()))
        url = response.redirect_chain[-1][0]
        self.assertEqual(Client().get(url).status_code, 404)
        outro = Client()
        outro.get(reverse("pedidos:checkout"))
        self.assertEqual(outro.get(url).status_code, 404)

    def test_historico_preservado_e_exclusao_protegida(self):
        self.enviar(self.dados(self.preparar()))
        self.opcao.preco = Decimal("50.00")
        self.opcao.save()
        self.produto.nome = "Novo nome"
        self.produto.save()
        item = ItemPedido.objects.get()
        self.assertEqual(item.nome_produto, "Couve")
        self.assertEqual(item.preco_unitario, Decimal("10.05"))
        with self.assertRaises(ProtectedError):
            self.opcao.delete()
        with self.assertRaises(ProtectedError):
            self.produto.delete()

    def test_erro_no_item_reverte_pedido(self):
        dados = self.dados(self.preparar())
        with patch("pedidos.services.ItemPedido.save", side_effect=ValidationError("Falha simulada")):
            response = self.enviar(dados)
        self.assertContains(response, "Falha simulada")
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(ItemPedido.objects.count(), 0)
        self.assertTrue(self.client.session["cesta"])

    def test_whatsapp_usa_snapshot_e_nao_envia_automaticamente(self):
        self.enviar(self.dados(self.preparar(), observacoes="Sem sacola & obrigado"))
        pedido = Pedido.objects.get()
        url = urlparse(link_whatsapp(pedido))
        self.assertEqual(url.netloc, "wa.me")
        self.assertEqual(url.path, "/5569999999999")
        texto = parse_qs(url.query)["text"][0]
        self.assertIn("0,1 kg", texto)
        self.assertIn("Pix", texto)
        self.assertIn("Sem sacola & obrigado", texto)
        self.assertIn("R$ 1,01", texto)
        ConfiguracaoLoja.objects.update(whatsapp="")
        self.assertIsNone(link_whatsapp(pedido))

    def test_admin_altera_status_e_frete_sem_editar_itens(self):
        self.enviar(self.dados(self.preparar()))
        user = get_user_model().objects.create_superuser(username="vendedor", password="senha-teste")
        self.client.force_login(user)
        pedido = Pedido.objects.get()
        url = reverse("admin:pedidos_pedido_change", args=[pedido.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Couve")
        self.assertFalse(response.context["has_delete_permission"])
        self.assertNotIn("subtotal_produtos", response.context["adminform"].form.fields)
        self.assertEqual(Client().get(url).status_code, 302)

    def test_taxa_retirada_nao_pode_ser_alterada(self):
        self.enviar(self.dados(self.preparar()))
        pedido = Pedido.objects.get()
        pedido.taxa_entrega = Decimal("2.00")
        with self.assertRaises(ValidationError):
            pedido.full_clean()

    def test_sem_revisao_ou_dados_invalidos_nao_registra(self):
        token = self.preparar()
        for extras in [
            {"revisar": ""}, {"telefone_cliente": "123"},
            {"forma_pagamento": "BOLETO"}, {"modalidade": "OUTRO"}, {"nome_cliente": ""},
        ]:
            self.enviar(self.dados(token, **extras))
            self.assertEqual(Pedido.objects.count(), 0)

    def test_vazia_redireciona_e_csrf_obrigatorio(self):
        self.assertRedirects(self.client.get(reverse("pedidos:checkout")), reverse("catalogo:cesta"))
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse("pedidos:checkout"), {}).status_code, 403)

    def test_entregas_restritas_a_ji_parana(self):
        ConfiguracaoLoja.objects.update(cidade_entrega="Ji-Paraná", uf_entrega="RO")
        token = self.preparar()
        dados = self.dados(token, modalidade="ENTREGA", logradouro="Rua Teste",
                           numero_endereco="10", bairro="Centro", cidade="Porto Velho", uf="RO")
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertIn("cidade", response.context["form"].errors)
        dados["cidade"] = "Ji Parana"
        dados["uf"] = "AM"
        response = self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertIn("uf", response.context["form"].errors)
        dados["uf"] = "RO"
        self.enviar(dados)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_post_vazio_nao_falha(self):
        self.preparar()
        response = self.enviar({})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_novo_checkout_apos_pedido_gera_outro_numero(self):
        self.enviar(self.dados(self.preparar()))
        self.enviar(self.dados(self.preparar()))
        self.assertEqual(Pedido.objects.count(), 2)

    def test_maços_inteiros_e_quantidade_invalida_na_finalizacao(self):
        maco = OpcaoVenda.objects.create(produto=self.produto, unidade="MACO", preco="4.50")
        self.client.post(reverse("catalogo:adicionar", args=[maco.pk]), {"quantidade": "2"})
        response = self.client.get(reverse("pedidos:checkout"))
        token = response.context["form"]["confirmacao"].value()
        self.enviar(self.dados(token))
        self.assertEqual(Pedido.objects.get().subtotal_produtos, Decimal("9.00"))
        session = self.client.session
        session["cesta"] = {str(maco.pk): "1.5"}
        session.save()
        response = self.client.get(reverse("pedidos:checkout"), follow=True)
        self.assertContains(response, "quantidade inteira")
        self.assertEqual(Pedido.objects.count(), 1)

    def test_admin_registra_frete_e_status(self):
        self.enviar(self.dados(self.preparar(), modalidade="ENTREGA", logradouro="Rua Teste",
                               numero_endereco="10", bairro="Centro", cidade="Cidade Teste", uf="RO"))
        pedido = Pedido.objects.get()
        item = pedido.itens.get()
        user = get_user_model().objects.create_superuser(username="operador", password="senha-teste")
        self.client.force_login(user)
        response = self.client.post(reverse("admin:pedidos_pedido_change", args=[pedido.pk]), {
            "status": "CONFIRMADO", "taxa_entrega": "5.00",
            "itens-TOTAL_FORMS": "1", "itens-INITIAL_FORMS": "1",
            "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "0",
            "itens-0-id": str(item.pk), "itens-0-pedido": str(pedido.pk), "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, "CONFIRMADO")
        self.assertEqual(pedido.total, Decimal("6.01"))
        self.assertIn("Taxa de entrega: R$ 5,00", mensagem_whatsapp(pedido))
