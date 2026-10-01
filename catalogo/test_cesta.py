from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from .models import Categoria, OpcaoVenda, Produto


class CestaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        categoria = Categoria.objects.create(nome="Folhagens")
        cls.produto = Produto.objects.create(nome="Couve", categoria=categoria)
        cls.kg = OpcaoVenda.objects.create(produto=cls.produto, unidade="KG", preco="10.00")
        cls.maco = OpcaoVenda.objects.create(produto=cls.produto, unidade="MACO", preco="4.50")

    def adicionar(self, opcao=None, quantidade="0,300", **extra):
        return self.client.post(
            reverse("catalogo:adicionar", args=[(opcao or self.kg).pk]),
            {"quantidade": quantidade, **extra},
            follow=True,
        )

    def test_catalogo_exibe_somente_ofertas_ativas(self):
        self.assertContains(self.client.get(reverse("catalogo:inicio")), "Couve")
        self.produto.ativo = False
        self.produto.save()
        self.assertNotContains(self.client.get(reverse("catalogo:inicio")), "Couve")

    def test_catalogo_sem_ofertas_tem_estado_vazio(self):
        OpcaoVenda.objects.update(disponivel=False)
        response = self.client.get(reverse("catalogo:inicio"))
        self.assertNotContains(response, "Couve")
        self.assertContains(response, "Em breve")

    def test_cesta_vazia(self):
        response = self.client.get(reverse("catalogo:cesta"))
        self.assertContains(response, "Sua cesta está esperando")

    def test_peso_e_preco_sao_calculados_no_servidor(self):
        response = self.adicionar(preco="0.01", subtotal="0.00")
        self.assertEqual(response.context["subtotal"], Decimal("3.00"))
        self.assertEqual(response.context["itens"][0]["quantidade"], Decimal("0.300"))

    def test_soma_atualiza_e_remove(self):
        self.adicionar()
        response = self.adicionar(quantidade="0.200")
        self.assertEqual(response.context["subtotal"], Decimal("5.00"))
        response = self.client.post(reverse("catalogo:atualizar", args=[self.kg.pk]),
                                    {"quantidade": "1,250"}, follow=True)
        self.assertEqual(response.context["subtotal"], Decimal("12.50"))
        response = self.client.post(reverse("catalogo:remover", args=[self.kg.pk]), follow=True)
        self.assertEqual(response.context["itens"], [])

    def test_validacao_rejeita_quantidades_invalidas(self):
        for valor in ["", "0", "-1", "0.0001", "NaN", "Infinity", "1e3", "abc", "1000000"]:
            with self.subTest(valor=valor):
                self.adicionar(quantidade=valor)
                self.assertEqual(self.client.session.get("cesta", {}), {})
        self.adicionar(opcao=self.maco, quantidade="1,5")
        self.assertEqual(self.client.session.get("cesta", {}), {})

    def test_atualizacao_invalida_preserva_quantidade(self):
        self.adicionar()
        response = self.client.post(reverse("catalogo:atualizar", args=[self.kg.pk]),
                                    {"quantidade": "0"}, follow=True)
        self.assertEqual(response.context["subtotal"], Decimal("3.00"))
        self.assertContains(response, "maior que zero")

    def test_unidades_separadas_e_arredondamento_por_item(self):
        self.kg.preco = Decimal("10.05")
        self.kg.save()
        self.adicionar(quantidade="0.100")
        response = self.adicionar(opcao=self.maco, quantidade="2")
        self.assertEqual(len(response.context["itens"]), 2)
        self.assertEqual(response.context["subtotal"], Decimal("10.01"))

    def test_disponibilidade_e_preco_atualizados(self):
        self.adicionar()
        self.kg.preco = Decimal("20.00")
        self.kg.save()
        self.assertEqual(self.client.get(reverse("catalogo:cesta")).context["subtotal"], Decimal("6.00"))
        self.kg.disponivel = False
        self.kg.save()
        response = self.client.get(reverse("catalogo:cesta"))
        self.assertEqual(response.context["subtotal"], Decimal("0.00"))
        self.assertContains(response, "Indisponível")
        self.assertEqual(self.client.post(reverse("catalogo:adicionar", args=[self.kg.pk]),
                                         {"quantidade": "1"}).status_code, 404)

    def test_produto_desativado_e_opcao_excluida(self):
        self.adicionar()
        self.produto.ativo = False
        self.produto.save()
        response = self.client.get(reverse("catalogo:cesta"))
        self.assertEqual(response.context["subtotal"], Decimal("0.00"))
        opcao_id = self.kg.pk
        self.kg.delete()
        response = self.client.get(reverse("catalogo:cesta"))
        self.assertContains(response, "Produto removido do catálogo")
        response = self.client.post(reverse("catalogo:remover", args=[opcao_id]), follow=True)
        self.assertEqual(response.context["itens"], [])

    def test_cestas_isoladas_entre_clientes(self):
        self.adicionar()
        outro = Client()
        self.assertEqual(outro.get(reverse("catalogo:cesta")).context["itens"], [])

    def test_mutacoes_exigem_post_e_csrf(self):
        for acao in ["adicionar", "atualizar", "remover"]:
            url = reverse(f"catalogo:{acao}", args=[self.kg.pk])
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(Client(enforce_csrf_checks=True).post(url, {"quantidade": "1"}).status_code, 403)
