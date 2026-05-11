import sqlite3
from pathlib import Path

db_path = Path('app/modules/asistente_inteligente/artifacts/alertas_viales.db')
if not db_path.exists():
    print(f'DB not found at {db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT fuente, categoria, length(detalle_completo) as len FROM alertas_viales')
rows = cursor.fetchall()
print(f'Total alertas en BD: {len(rows)}')
for r in rows:
    print(f"- {r['fuente']}: {r['categoria']} (length: {r['len']})")
