"""Monta o ZIP de código e dados públicos, sem banco, contas ou pedidos."""
import io
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

raiz = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(raiz))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.core.management import call_command
from catalogo.models import Produto

saida = raiz / "dist" / "horta-pythonanywhere.zip"
saida.parent.mkdir(exist_ok=True)
dados = io.StringIO()
call_command("dumpdata", "catalogo", "pedidos.configuracaoloja", indent=2, stdout=dados)
modelos = {item["model"] for item in json.loads(dados.getvalue())}
assert modelos <= {"catalogo.categoria", "catalogo.produto", "catalogo.opcaovenda", "pedidos.configuracaoloja"}

with ZipFile(saida, "w", ZIP_DEFLATED) as pacote:
    for pasta in ["config", "catalogo", "pedidos", "docs", "deploy"]:
        for caminho in (raiz / pasta).rglob("*"):
            if not caminho.is_file() or "__pycache__" in caminho.parts:
                continue
            if caminho.suffix not in {".py", ".html", ".css", ".js", ".md", ".jpg", ".jpeg", ".png", ".webp"}:
                continue
            pacote.write(caminho, "horta/" + caminho.relative_to(raiz).as_posix())
    for nome in ["manage.py", "requirements.txt", "README.md", ".gitignore"]:
        pacote.write(raiz / nome, "horta/" + nome)
    pacote.writestr("horta/deploy/catalogo_inicial.json", dados.getvalue().encode("utf-8"))
    publico = raiz / "deploy" / "catalogo_publico.json"
    if publico.exists():
        pacote.write(publico, "horta/deploy/catalogo_publico.json")
    media = (raiz / "media").resolve()
    for nome in set(Produto.objects.exclude(foto="").values_list("foto", flat=True)):
        caminho = (media / nome).resolve()
        if not caminho.is_relative_to(media):
            raise ValueError("Foto fora da pasta media.")
        if caminho.is_file():
            pacote.write(caminho, "horta/media/" + caminho.relative_to(media).as_posix())

with ZipFile(saida) as pacote:
    assert pacote.testzip() is None
    assert not any(nome.endswith((".sqlite3", ".production.json", ".env")) for nome in pacote.namelist())
print(f"Pacote criado: {saida}")
print(f"Tamanho: {saida.stat().st_size / 1024:.1f} KiB")
print("Inclui apenas código, catálogo, contato da loja e fotos cadastradas.")
