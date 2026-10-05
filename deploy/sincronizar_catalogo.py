"""Exporta/aplica somente catálogo público e fotos; preserva contas e pedidos."""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import sys

raiz = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(raiz))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from catalogo.models import Categoria, Produto, OpcaoVenda

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('acao', choices=['exportar', 'aplicar'])
args = parser.parse_args()
fixture = raiz / 'deploy' / 'catalogo_publico.json'
fotos = raiz / 'deploy' / 'catalogo_fotos'
if args.acao == 'exportar':
    dados = io.StringIO()
    call_command('dumpdata', 'catalogo', indent=2, stdout=dados)
    fixture.write_text(dados.getvalue(), encoding='utf-8')
    for nome in Produto.objects.exclude(foto='').values_list('foto', flat=True).distinct():
        origem = (Path(settings.MEDIA_ROOT) / nome).resolve()
        if not origem.is_relative_to(Path(settings.MEDIA_ROOT).resolve()):
            raise ValueError('Foto fora da pasta media.')
        destino = fotos / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
    print('Catálogo público e fotos exportados. Nenhuma conta ou pedido incluído.')
else:
    dados = json.loads(fixture.read_text(encoding='utf-8'))
    modelos = {'catalogo.categoria': Categoria, 'catalogo.produto': Produto, 'catalogo.opcaovenda': OpcaoVenda}
    with transaction.atomic():
        for item in dados:
            modelo = modelos[item['model']]
            existente = modelo.objects.filter(pk=item['pk']).first()
            if existente:
                campos = ['nome'] if modelo in (Categoria, Produto) else ['produto_id', 'unidade']
                for campo in campos:
                    chave = 'produto' if campo == 'produto_id' else campo
                    if getattr(existente, campo) != item['fields'][chave]:
                        raise ValueError(f'Conflito no cadastro {item["model"]} #{item["pk"]}. Importação cancelada para preservar os dados.')
        call_command('loaddata', str(fixture))
    if fotos.exists():
        shutil.copytree(fotos, settings.MEDIA_ROOT, dirs_exist_ok=True)
    print('Catálogo aplicado e fotos copiadas. Contas e pedidos preservados.')
