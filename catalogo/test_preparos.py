from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from .models import Categoria, Produto, OpcaoVenda
from .cesta import resumo_cesta
from pedidos.services import cotar


class PreparoTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Legumes')
        self.produto = Produto.objects.create(nome='Mandioca branca', categoria=categoria)
        self.casca = OpcaoVenda.objects.create(produto=self.produto, unidade='KG', preparo='com casca', preco='5.00')
        self.descascada = OpcaoVenda.objects.create(produto=self.produto, unidade='KG', preparo='descascada', preco='6.00')

    def test_catalogo_exibe_um_cartao_com_as_duas_escolhas(self):
        resposta = self.client.get(reverse('catalogo:inicio'))
        self.assertContains(resposta, '<article class="product">', count=1)
        self.assertContains(resposta, 'Com casca — R$ 5,00/kg')
        self.assertContains(resposta, 'Descascada — R$ 6,00/kg')

    def test_escolhas_ficam_separadas_na_cesta_com_precos_corretos(self):
        for opcao in [self.casca, self.descascada]:
            self.client.post(reverse('catalogo:adicionar_produto', args=[self.produto.pk]), {'opcao': opcao.pk, 'quantidade': '0.5'})
        resumo = resumo_cesta(self.client.session)
        self.assertEqual(len(resumo['itens']), 2)
        self.assertEqual(resumo['subtotal'], Decimal('5.50'))
        resposta = self.client.get(reverse('catalogo:cesta'))
        self.assertContains(resposta, 'Mandioca branca com casca')
        self.assertContains(resposta, 'Mandioca branca descascada')
        itens, subtotal, _ = cotar(self.client.session['cesta'])
        self.assertEqual(subtotal, Decimal('5.50'))
        self.assertEqual({item['nome_produto'] for item in itens}, {'Mandioca branca com casca', 'Mandioca branca descascada'})

    def test_nao_aceita_opcao_de_outro_produto(self):
        outro = Produto.objects.create(nome='Outra mandioca', categoria=self.produto.categoria)
        resposta = self.client.post(reverse('catalogo:adicionar_produto', args=[outro.pk]), {'opcao': self.casca.pk, 'quantidade': '1'})
        self.assertEqual(resposta.status_code, 404)
