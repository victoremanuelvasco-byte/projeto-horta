"""Execute no PythonAnywhere: python deploy/configurar.py usuario.pythonanywhere.com."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets

parser = argparse.ArgumentParser(description="Prepara a configuração privada de produção.")
parser.add_argument("dominio", help="Domínio exibido na aba Web, sem https://.")
args = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9_-]+\.(?:eu\.)?pythonanywhere\.com", args.dominio):
    parser.error("Informe seu domínio usuario.pythonanywhere.com (ou usuario.eu.pythonanywhere.com).")

raiz = Path(__file__).resolve().parent.parent
arquivo = raiz / ".production.json"
if arquivo.exists():
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    if dados.get("ALLOWED_HOSTS") != [args.dominio]:
        parser.error("Já existe configuração para outro domínio. Revise .production.json manualmente.")
    print("Configuração existente preservada.")
else:
    dados = {"SECRET_KEY": secrets.token_urlsafe(64), "ALLOWED_HOSTS": [args.dominio]}
    descritor = os.open(arquivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as destino:
        json.dump(dados, destino, indent=2)
    print("Configuração privada criada. Não compartilhe .production.json.")

(raiz / "media").mkdir(exist_ok=True)
wsgi = (
    "import os\nimport sys\n\n"
    f"sys.path.insert(0, {str(raiz)!r})\n"
    "os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'\n\n"
    "from django.core.wsgi import get_wsgi_application\n"
    "application = get_wsgi_application()\n"
)
(raiz / "deploy" / "wsgi_pythonanywhere.txt").write_text(wsgi, encoding="utf-8")
print("Copie deploy/wsgi_pythonanywhere.txt para o arquivo WSGI indicado na aba Web.")
