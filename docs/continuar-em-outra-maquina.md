# Continuar no notebook

Na pasta do repositório, baixe as alterações com `git pull`. Na primeira execução:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe deploy/sincronizar_catalogo.py aplicar
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://localhost:8000/. O catálogo público e as fotos estão no repositório;
contas, pedidos, bancos e backups privados não estão. Se já tem ambiente virtual,
use-o em vez de recriar. Para criar uma conta local, execute `manage.py createsuperuser`
com o Python do ambiente virtual. Se a importação detectar conflito de cadastros,
ela para antes de modificar o banco: preserve uma cópia e revise o conflito.

# Atualizar o PythonAnywhere

Primeiro faça backup do banco, das fotos e da configuração de produção no servidor.
Envie o código atualizado e as fotos, preservando `db.sqlite3`, `.production.json`
e `.venv`. Se o servidor é um checkout Git, use `git pull`; caso contrário, envie
`dist/horta-pythonanywhere.zip` e extraia sobre o código existente. Não use
`unzip -n`, pois esse comando deixa os arquivos antigos sem atualizar.

No console Bash, dentro de `~/horta`:

```bash
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings_production
python manage.py migrate
python deploy/sincronizar_catalogo.py aplicar
python manage.py collectstatic --noinput
python manage.py check
```

O comando `aplicar` atualiza apenas os cadastros de catálogo exportados; não importa
usuários ou pedidos e não substitui o banco inteiro. Revise eventuais conflitos.
Por último, em **Web**, clique em **Reload** e confira o catálogo no site público.
