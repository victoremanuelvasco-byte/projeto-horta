# Sistema de vendas de verduras

Projeto de aprendizado: construir uma aplicação web responsiva, do levantamento de requisitos à publicação, aproveitando conhecimentos básicos de Python.

## Escopo acordado

- Clientes consultam o catálogo e selecionam produtos e quantidades.
- Um produto pode ser oferecido por maço, por quilo ou nas duas opções, cada uma com seu preço.
- O cliente pode solicitar qualquer peso. O valor é calculado pelo peso solicitado e não é reajustado se a pesagem real for diferente.
- Produtos comprados em caixaria são vendidos por quilo; não haverá opção de caixa no catálogo inicial.
- Clientes escolhem entrega ou retirada.
- A taxa de entrega é combinada pelo WhatsApp. Até sua definição, o catálogo e o pedido mostram o subtotal dos produtos e a indicação de entrega a combinar.
- O pedido fica registrado no sistema e pode ser encaminhado ao WhatsApp do vendedor.
- O vendedor confirma o pedido com o cliente.
- Formas de pagamento aceitas: cartão, Pix e dinheiro. O sistema registra a escolha; o pagamento acontece fora do site nesta primeira versão.

## Proposta técnica

Python com Django, páginas HTML/CSS e JavaScript para interações. Usar inicialmente o painel administrativo do Django para gerenciar catálogo e pedidos. A implementação e a configuração do ambiente serão feitas em etapas explicadas.

## Etapas de aprendizado

1. Requisitos e modelagem: entidades, relacionamentos e regras.
2. Ambiente e projeto Django: configuração, Git e dependências.
3. Banco: modelos, migrações e painel administrativo.
4. Catálogo responsivo e cesta.
5. Registro de pedidos e encaminhamento ao WhatsApp.
6. Validação, testes dos fluxos essenciais e segurança.
7. Publicação, backups e manutenção.

Veja [a modelagem inicial](docs/modelagem.md).

## Executar no Windows (PowerShell)

Na pasta do projeto, prepare o ambiente na primeira execução:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

O ambiente `.venv` isola as bibliotecas do projeto. Usamos seu Python diretamente,
sem precisar ativar scripts no PowerShell. O arquivo `requirements.txt` registra
as versões instaladas. O banco SQLite local é criado pelo comando `migrate`.

Para iniciar o servidor de desenvolvimento:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://127.0.0.1:8000/ no navegador. Use Ctrl+C no terminal para encerrar.
A página inicial exibe o catálogo público com os produtos disponíveis.

Para verificar a configuração:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

`manage.py` executa os comandos do projeto; `config/settings.py` contém as
configurações e `config/urls.py` define as rotas. As configurações iniciais são
para desenvolvimento local, com `DEBUG=True`; a publicação terá configuração própria.

O Git acompanha código e documentação. O `.gitignore` exclui ambiente virtual,
banco local e arquivos de segredos. Para consultar alterações, use `git status`.

## Cadastrar produtos no painel administrativo

O aplicativo `catalogo` contém Categoria, Produto e OpcaoVenda. Os modelos ficam
em `catalogo/models.py`, o painel em `catalogo/admin.py` e a estrutura do banco
é versionada em `catalogo/migrations/`.

Para uma instalação existente, atualize as dependências e aplique as migrações:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

Crie sua conta de administrador uma única vez, informando usuário e senha no terminal:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

A senha não aparece enquanto você digita. Abra http://127.0.0.1:8000/admin/ e entre
com essa conta. Cadastre uma categoria (por exemplo, Folhagens), depois um produto
(por exemplo, Couve). Na mesma tela do produto, adicione as opções de venda:
Maço a R$ 4,50 e Quilo a R$ 12,00, por exemplo. Cada unidade pode aparecer apenas
uma vez por produto, e o preço deve ser positivo. Desmarque Disponível para
suspender uma opção ou Ativo para suspender o produto inteiro.

A descrição e a foto são opcionais. As fotos ficam na pasta local `media/`, fora
do Git, e são servidas pelo Django somente no ambiente de desenvolvimento.
Categorias com produtos não podem ser excluídas. Produtos e opções referenciados
em pedidos também ficam protegidos contra exclusão; use Ativo e Disponível para
suspender ofertas preservando o histórico.

Para executar os testes do catálogo:

```powershell
.\.venv\Scripts\python.exe manage.py test catalogo
```
## Catálogo público e cesta

Abra http://127.0.0.1:8000/ para visualizar os produtos ativos com opções disponíveis.
Cada opção tem seu próprio campo de quantidade. Para quilos, informe por exemplo
`0,300` ou `0.300` para 300 g. Para maços, informe números inteiros.

Ao adicionar, a quantidade é somada à mesma opção na cesta. Em `/cesta/`, use
Atualizar para substituir a quantidade ou Remover para excluir um item.
A cesta pertence à sessão do navegador e não exige cadastro do cliente.

Os preços vêm do banco, e os subtotais são calculados no servidor com Decimal,
arredondando cada item para centavos com ROUND_HALF_UP. A precisão mínima do peso
é de 1 g; valores inválidos são rejeitados. O limite técnico por opção na cesta
é de 999999,999 unidades. Os formulários funcionam sem JavaScript.

Alterações de preço no painel aparecem ao consultar a cesta. Produtos desativados,
opções indisponíveis e opções excluídas deixam de participar do subtotal, com aviso
na cesta. Produtos sem foto usam uma apresentação alternativa no catálogo.

Use Finalizar pedido na cesta para informar seus dados e registrar a compra.

## Finalizar e acompanhar pedidos

1. Adicione produtos à cesta e clique em **Finalizar pedido**.
2. Informe nome, telefone com DDD, entrega ou retirada e pagamento (cartão, Pix ou dinheiro).
3. Para entrega, informe rua, número (ou S/N), bairro, cidade e UF. CEP, complemento
   e referência são opcionais. A loja atende **Ji-Paraná/RO**, e o frete depende do
   endereço e será combinado pelo WhatsApp. Para retirada, a taxa é zero.
4. Revise os itens e valores, marque a confirmação e clique em **Registrar pedido**.
5. Na página do pedido, clique em **Abrir pedido no WhatsApp**, confira a mensagem
   e envie pelo aplicativo. Abrir o link não envia a mensagem automaticamente.

O pedido fica salvo como pendente mesmo que o cliente não abra o WhatsApp. O botão
pode ser usado novamente sem gerar outro pedido. A escolha de pagamento não marca
o pedido como pago, e não há cobrança online.

No painel `/admin/`, acesse **Pedidos → Pedidos** para consultar os itens, alterar
o status e registrar a taxa de entrega combinada. Em branco significa frete ainda
não definido; zero significa entrega gratuita. O subtotal preserva os preços e
quantidades do momento da compra; o painel não permite alterar esses itens.

Em **Pedidos → Configuração da loja**, configure o WhatsApp (55 + DDD + número),
a cidade, a UF atendida e o texto sobre entrega. Esses dados já foram configurados
no banco local. Em uma nova instalação, configure-os novamente pelo painel.

A confirmação só pode ser consultada pela sessão do navegador que criou o pedido.
Compartilhar sua URL não concede acesso em outro navegador. O vendedor consulta
os pedidos autenticado no painel. A sessão pode expirar; guarde o número do pedido
para atendimento.

## Verificações do fluxo

```powershell
.\.venv\Scripts\python.exe manage.py test catalogo pedidos
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Os testes usam um banco separado. Cobrem cálculos, disponibilidade, validação de
endereço, confirmação de alterações de preço, reenvios, acesso por sessão,
preservação do histórico e atualização do frete e status no painel.

Pedido e itens são gravados numa única transação. Uma chave única identifica cada
finalização para impedir pedidos duplicados em reenvios. A confirmação assinada
compara os itens, quantidades e preços exibidos com os valores atuais do servidor.
Alterações exigem nova revisão. SQLite atende aos testes locais; concorrência sob
carga e configurações de produção ainda serão avaliadas antes da publicação.


## Publicação de teste

Veja [o roteiro do PythonAnywhere](docs/pythonanywhere.md). O pacote para upload
é gerado por deploy/empacotar.py e fica em dist/horta-pythonanywhere.zip.
