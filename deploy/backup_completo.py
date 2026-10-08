"""Cria uma copia portatil do projeto e um snapshot consistente do SQLite."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {'.venv', '__pycache__', 'dist', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def main():
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output = ROOT / 'dist' / ('backup-completo-' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    database = output / 'db.sqlite3'
    source = ROOT / 'db.sqlite3'
    if not source.is_file():
        raise FileNotFoundError('Banco db.sqlite3 nao encontrado; backup cancelado.')
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
        with closing(sqlite3.connect(database)) as snapshot:
            original.backup(snapshot)
    with closing(sqlite3.connect(database)) as snapshot:
        result = snapshot.execute('PRAGMA integrity_check').fetchall()
        if result != [('ok',)]:
            raise RuntimeError('Falha na integridade do banco: ' + repr(result))
        tables = [row[0] for row in snapshot.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = {name: snapshot.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                  for name in tables}
        sql = output / 'banco-completo.sql'
        with sql.open('w', encoding='utf-8', newline='\n') as handle:
            for line in snapshot.iterdump():
                handle.write(line + '\n')
    # Confere tambem se a exportacao SQL consegue reconstruir o banco.
    with closing(sqlite3.connect(':memory:')) as restored:
        restored.executescript(sql.read_text(encoding='utf-8'))
        restored_counts = {name: restored.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                           for name in tables}
        if restored_counts != counts or restored.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError('A restauracao SQL nao passou na verificacao.')
    archive = output / 'horta-completo.zip'
    hashes = {}
    with ZipFile(archive, 'w', ZIP_DEFLATED) as package:
        for current, dirs, files in os.walk(ROOT, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
            for name in sorted(files):
                item = Path(current) / name
                relative = item.relative_to(ROOT).as_posix()
                if relative == 'db.sqlite3' or name.startswith('db.sqlite3-') or item.suffix in {'.pyc', '.pyo'}:
                    continue
                content = item.read_bytes()
                package.writestr('horta/' + relative, content)
                hashes[relative] = hashlib.sha256(content).hexdigest()
        for item, relative in [(database, 'db.sqlite3'), (sql, 'backup/banco-completo.sql')]:
            content = item.read_bytes()
            package.writestr('horta/' + relative, content)
            hashes[relative] = hashlib.sha256(content).hexdigest()
        manifest = {'created_at': datetime.now().astimezone().isoformat(),
                    'database_integrity': 'ok', 'table_counts': counts,
                    'excluded_directories': sorted(EXCLUDED), 'sha256': hashes}
        package.writestr('horta/backup/manifesto.json', json.dumps(manifest, indent=2, ensure_ascii=False))
    with ZipFile(archive) as package:
        if package.testzip() is not None:
            raise RuntimeError('Falha na verificacao do ZIP.')
        for relative, expected in hashes.items():
            if hashlib.sha256(package.read('horta/' + relative)).hexdigest() != expected:
                raise RuntimeError('Arquivo divergente: ' + relative)
        with tempfile.TemporaryDirectory(prefix='horta-verificar-') as temporary:
            restored_db = Path(temporary) / 'db.sqlite3'
            restored_db.write_bytes(package.read('horta/db.sqlite3'))
            with closing(sqlite3.connect(restored_db)) as restored:
                if restored.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise RuntimeError('Banco extraido invalido.')
    (output / 'manifesto.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'COMO-USAR.md').write_text((ROOT / 'docs' / 'migrar-computador.md').read_text(encoding='utf-8'), encoding='utf-8')
    (output / 'SHA256.txt').write_text('\n'.join(
        hashlib.sha256(item.read_bytes()).hexdigest() + '  ' + item.name
        for item in [archive, database, sql]) + '\n', encoding='utf-8')
    print('Backup completo: ' + str(output))
    print('ZIP: ' + str(archive))
    print('Arquivos no ZIP: ' + str(len(hashes)))
    print('Tamanho do ZIP: ' + str(archive.stat().st_size) + ' bytes')
    print('Integridade SQLite, restauracao SQL e hashes do ZIP: OK')
    print('Contagem por tabela: ' + json.dumps(counts, ensure_ascii=False))


if __name__ == '__main__':
    main()

