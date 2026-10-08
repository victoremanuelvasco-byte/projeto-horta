# Levar o projeto completo para outro computador

O arquivo `horta-completo.zip` contem uma pasta `horta` com o codigo editavel,
modelos, migracoes, templates, CSS, JavaScript, documentacao, configuracoes,
historico Git e o banco `db.sqlite3` com todos os registros existentes no momento
do backup. Fotos e outros arquivos locais tambem sao incluidos quando existem.
O arquivo `backup/manifesto.json` registra hashes dos arquivos e contagens do banco.

O ambiente virtual `.venv` precisa ser recriado, pois depende do computador.
Caches Python e a pasta `dist` (pacotes gerados anteriormente) ficam fora do ZIP.
As dependencias estao fixadas em `requirements.txt`; sua instalacao requer internet.
O computador de origem usa Python 3.14.7. Instale preferencialmente essa mesma
versao do Python no computador de destino, com suporte a `python` no terminal.

## Instalar no outro Windows

1. Copie `horta-completo.zip` para um pendrive ou para o outro computador.
2. Clique com o botao direito no ZIP e use **Extrair tudo**. Nao execute dentro do ZIP.
3. Abra a pasta extraida `horta` no VS Code ou no editor de sua preferencia.
4. Abra um terminal PowerShell nessa pasta (onde esta `manage.py`) e execute:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Se o Windows reconhecer somente `py`, use `py -3.14 -m venv .venv`
no lugar de `python -m venv .venv`.

Abra http://127.0.0.1:8000/ para o catalogo e http://127.0.0.1:8000/admin/
para o painel. As contas e senhas existentes continuam valendo: nao e necessario
criar outro administrador. Use Ctrl+C para encerrar o servidor.
Se esqueceu a senha, use `manage.py changepassword NOME_DO_USUARIO` com o Python
da `.venv`. Produtos, pedidos e configuracao da loja ja estao no banco copiado.

Para editar, altere os arquivos `.py`, `.html`, `.css` e `.js` nas pastas do projeto.
O Git ja esta incluido; instale Git no destino se quiser usar o historico.

## Banco separado e restauracao

A pasta do backup tambem contem `db.sqlite3` separado e `banco-completo.sql`.
Para a transferencia normal, basta o ZIP: ele ja contem o banco no lugar certo.
Guarde os arquivos separados como uma copia adicional.

Para restaurar somente o banco em uma copia existente do projeto: encerre o
servidor, guarde o banco atual com outro nome e copie o `db.sqlite3` do backup
para a mesma pasta de `manage.py`. Nao sobrescreva um banco com dados novos sem
antes guardar uma copia. O SQL e uma alternativa para reconstruir um banco SQLite
vazio; nao precisa ser importado ao usar o arquivo `db.sqlite3`.

## Gerar outro backup

No computador onde estao os dados mais recentes, de preferencia encerre o servidor
e termine suas edicoes para incluir codigo e fotos da mesma etapa. Execute:

```powershell
.\.venv\Scripts\python.exe deploy\backup_completo.py
```

O script cria uma nova pasta em `dist` com data e hora, sem substituir backups
anteriores. Usa a API de backup do SQLite para obter um banco consistente,
confere sua integridade, testa a restauracao SQL e verifica os arquivos do ZIP.
O backup inclui contas, pedidos e eventuais segredos de configuracao: mantenha-o
privado. Alteracoes posteriores ao backup nao sao sincronizadas entre computadores.

Esses passos executam o projeto localmente. Publicacao na internet tem um roteiro
separado em `docs/pythonanywhere.md`.
