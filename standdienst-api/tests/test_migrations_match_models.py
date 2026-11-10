"""Modelle und Alembic-Migrationen dürfen nicht auseinanderlaufen.

Läuft in einem eigenen Prozess gegen eine frische SQLite-Datei (die
sitzungsweite Test-App nutzt create_all() und sieht Migrationen nie):
alle Migrationen anwenden, dann Modell-Metadaten mit dem Schema vergleichen.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent

# Bewusst bestehende Abweichungen (Additive-only-Regel, siehe CLAUDE.md):
# Spalte aus dem Modell entfernt (#69), in der DB stehen gelassen.
EXPECTED = [
    ['remove_column', 'global_settings', 'landing_impressum_html'],
]

_SCRIPT = r'''
import json
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from app import create_app
from app.config import TestingConfig
from app.extensions import db

class Cfg(TestingConfig):
    SQLALCHEMY_DATABASE_URI = __URI__

app = create_app(Cfg)
with app.app_context():
    db.drop_all()  # create_app() legt im Testmodus per create_all() an
    upgrade()
    with db.engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={'compare_type': False})
        diff = compare_metadata(ctx, db.metadata)

def describe(op):
    if isinstance(op, list):  # Spaltenänderungen kommen gruppiert
        return [describe(o) for o in op]
    kind = op[0]
    if kind in ('add_column', 'remove_column'):
        return [kind, op[2], op[3].name]
    if kind in ('add_fk', 'remove_fk'):
        fk = op[1]
        return [kind, fk.parent.name, [c.name for c in fk.columns], fk.ondelete]
    if kind in ('add_table', 'remove_table'):
        return [kind, op[1].name]
    if kind in ('add_index', 'remove_index'):
        return [kind, op[1].table.name, op[1].name]
    return [kind, repr(op[1:])[:200]]

print('DIFF=' + json.dumps([describe(o) for o in diff]))
'''


def test_models_match_migrations(tmp_path):
    uri = f'sqlite:///{tmp_path / "schema.db"}'
    env = {**os.environ, 'DATABASE_URL': uri}
    proc = subprocess.run(
        [sys.executable, '-c', _SCRIPT.replace('__URI__', repr(uri))],
        cwd=API_DIR, env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    line = next(l for l in proc.stdout.splitlines() if l.startswith('DIFF='))
    diff = json.loads(line[len('DIFF='):])
    unexpected = [d for d in diff if d not in EXPECTED]
    assert unexpected == [], f'Modell und Migrationen weichen ab: {unexpected}'
