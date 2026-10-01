from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, OpcaoVenda, Produto


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nome="Folhagens")
        cls.produto = Produto.objects.create(nome="Couve", categoria=cls.categoria)

    def test_produto_com_duas_unidades_e_precos_independentes(self):
        OpcaoVenda.objects.create(produto=self.produto, unidade="MACO", preco="4.50")
        OpcaoVenda.objects.create(produto=self.produto, unidade="KG", preco="12.00")
        self.assertEqual(self.produto.opcoes_venda.count(), 2)
        self.assertEqual(
            self.produto.opcoes_venda.get(unidade="MACO").preco, Decimal("4.50"),
        )

    def test_preco_invalido_rejeitado_na_validacao_e_no_banco(self):
        for preco in ["0.00", "-1.00"]:
            with self.subTest(preco=preco):
                opcao = OpcaoVenda(produto=self.produto, unidade="KG", preco=preco)
                with self.assertRaises(ValidationError):
                    opcao.full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    opcao.save()

    def test_unidade_duplicada_rejeitada(self):
        OpcaoVenda.objects.create(produto=self.produto, unidade="KG", preco="10.00")
        duplicada = OpcaoVenda(produto=self.produto, unidade="KG", preco="15.00")
        with self.assertRaises(ValidationError):
            duplicada.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicada.save()

    def test_unidade_invalida_rejeitada(self):
        opcao = OpcaoVenda(produto=self.produto, unidade="CX", preco="10.00")
        with self.assertRaises(ValidationError):
            opcao.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            opcao.save()

    def test_categoria_em_uso_nao_pode_ser_excluida(self):
        with self.assertRaises(ProtectedError):
            self.categoria.delete()

    def test_admin_exige_login(self):
        response = self.client.get(reverse("admin:catalogo_produto_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_admin_cadastra_produto_com_opcoes(self):
        user = get_user_model().objects.create_superuser(
            username="vendedor_teste", password="senha-apenas-para-teste",
        )
        self.client.force_login(user)
        response = self.client.post(reverse("admin:catalogo_produto_add"), {
            "nome": "Alface",
            "categoria": self.categoria.pk,
            "descricao": "",
            "ativo": "on",
            "opcoes_venda-TOTAL_FORMS": "2",
            "opcoes_venda-INITIAL_FORMS": "0",
            "opcoes_venda-MIN_NUM_FORMS": "0",
            "opcoes_venda-MAX_NUM_FORMS": "1000",
            "opcoes_venda-0-unidade": "MACO",
            "opcoes_venda-0-preco": "3.50",
            "opcoes_venda-0-disponivel": "on",
            "opcoes_venda-1-unidade": "KG",
            "opcoes_venda-1-preco": "9.00",
            "opcoes_venda-1-disponivel": "on",
            "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302)
        produto = Produto.objects.get(nome="Alface")
        self.assertEqual(produto.opcoes_venda.count(), 2)
        for model in ["categoria", "produto", "opcaovenda"]:
            page = self.client.get(reverse(f"admin:catalogo_{model}_changelist"))
            self.assertEqual(page.status_code, 200)
