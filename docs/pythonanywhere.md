# Publicar a versão de teste no PythonAnywhere

Este roteiro usa uma conta gratuita, SQLite e o domínio fornecido pela plataforma.
A conta precisa oferecer Python 3.13 (ou 3.12). Use a MESMA versão no ambiente
virtual e na aplicação Web. Não use o Python 3.10 dos exemplos antigos: as versões
de algumas dependências deste projeto podem exigir Python mais recente.

## 1. Enviar o pacote

No computador local, o pacote pode ser atualizado com:

```powershell
.\.venv\Scripts\python.exe deploy/empacotar.py
```

No PythonAnywhere, abra **Files** e envie `dist/horta-pythonanywhere.zip` para sua
pasta pessoal. O ZIP contém uma pasta `horta`, código, catálogo e contato público
da loja. Não contém senhas, contas de administrador, pedidos, sessões ou banco local.

## 2. Preparar no console Bash

Abra **Consoles → Bash**. Os comandos abaixo são para Linux no PythonAnywhere,
não para o PowerShell do computador:

```bash
cd ~
unzip -n horta-pythonanywhere.zip
cd ~/horta
python3.13 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
python deploy/configurar.py SEUUSUARIO.pythonanywhere.com
export DJANGO_SETTINGS_MODULE=config.settings_production
python manage.py migrate
python manage.py loaddata deploy/catalogo_inicial.json
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Substitua SEUUSUARIO pelo seu usuário. Use o domínio exato da aba Web; na região
europeia ele contém `.eu.pythonanywhere.com`. Se a conta oferecer Python 3.12,
substitua `python3.13` por `python3.12` e selecione essa versão também na aba Web.

O script gera uma chave aleatória privada em `.production.json`. Não compartilhe
esse arquivo. Ele é usado tanto pelo site quanto pelos comandos de administração.
Executar o script novamente preserva a chave existente.

O `loaddata` é somente para o primeiro banco vazio: repeti-lo pode sobrescrever
produtos e configuração já editados no site. Os preços do catálogo inicial são
exemplos, para teste. A senha de administrador é definida diretamente no terminal.

## 3. Criar a aplicação Web

Na aba **Web → Add a new web app**, selecione o domínio gratuito,
**Manual configuration** e Python **3.13** (ou a versão usada acima).

Preencha:

- Source code e Working directory: `/home/SEUUSUARIO/horta`
- Virtualenv: `/home/SEUUSUARIO/horta/.venv`

Abra o arquivo **WSGI configuration file** pelo link da aba Web. Substitua seu
conteúdo pelo arquivo gerado `/home/SEUUSUARIO/horta/deploy/wsgi_pythonanywhere.txt`.
Você pode visualizar o conteúdo no console:

```bash
cat ~/horta/deploy/wsgi_pythonanywhere.txt
```

Não é necessário iniciar `runserver` na hospedagem.

## 4. Estilos e fotos

Em **Web → Static files**, configure:

| URL | Directory |
| --- | --- |
| /static/ | /home/SEUUSUARIO/horta/staticfiles |
| /media/ | /home/SEUUSUARIO/horta/media |

Mapeie somente essas duas pastas, nunca a pasta inteira do projeto.
Ative Force HTTPS se disponível e clique em **Reload**.

## 5. Verificar a publicação

Abra `https://SEUUSUARIO.pythonanywhere.com/` e confira:

1. Catálogo e estilos, inclusive no celular.
2. Login em `/admin/` com a conta criada no servidor.
3. Fotos, cadastro de produtos e configuração da loja.
4. Cesta, retirada e entrega em Ji-Paraná/RO.
5. Registro de um pedido de teste e abertura da mensagem no WhatsApp.
6. Status e taxa de entrega no painel.
7. A confirmação do pedido não abre em uma janela anônima.
8. HTTP redireciona para HTTPS e páginas inexistentes não expõem erros internos.

Se houver erro 500, consulte **Web → Error log**. Não ative DEBUG no site público.
Em novos consoles Bash, ative o ambiente e selecione as configurações de produção:

```bash
cd ~/horta
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_production
```

## Dados e manutenção

A cópia online tem seu próprio banco: alterações e pedidos não voltam para o PC.
Antes de atualizar o site, faça backup do banco SQLite e das fotos. Não substitua
o banco do servidor por um banco vazio ou pelo banco local. Guarde também a chave
de produção em local privado. O limite de disco gratuito inclui código, ambiente,
banco e fotos; comprima as fotos antes de enviar.

Renove a aplicação pelo painel antes do vencimento indicado na aba Web. O plano
gratuito tem recursos limitados e serve para esta avaliação inicial.

Referências oficiais:
- [Publicar um projeto Django](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/)
- [Arquivos estáticos](https://help.pythonanywhere.com/pages/StaticFiles/)
- [Versões de Python](https://help.pythonanywhere.com/pages/PythonVersions)

O check --deploy pode mostrar os avisos security.W005 e security.W021: nesta
versão de teste, HSTS vale somente para o domínio configurado, por uma hora, sem
abranger subdomínios nem solicitar inclusão permanente na lista dos navegadores.
Os avisos são esperados; outros avisos devem ser investigados.
