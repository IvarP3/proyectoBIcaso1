from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class AsistenteSQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_schema(self) -> None:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alertas_viales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_ingesta TEXT NOT NULL,
                    fuente TEXT NOT NULL,
                    url TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    confianza_pct REAL NOT NULL,
                    ubicacion TEXT,
                    detalle_completo TEXT NOT NULL,
                    modo_ingesta TEXT NOT NULL
                )
                """
            )
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_categoria ON alertas_viales (categoria)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_fecha ON alertas_viales (fecha_ingesta)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alertas_fuente ON alertas_viales (fuente)')
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS assistant_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def replace_alerts(self, rows: list[dict[str, Any]], mode: str, ingested_at: str) -> None:
        self.initialize_schema()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute('DELETE FROM alertas_viales')
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO alertas_viales (
                        fecha_ingesta, fuente, url, categoria,
                        confianza_pct, ubicacion, detalle_completo, modo_ingesta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row['fecha_ingesta'],
                        row['fuente'],
                        row['url'],
                        row['categoria'],
                        row['confianza_pct'],
                        row['ubicacion'],
                        row['detalle_completo'],
                        mode,
                    ),
                )
            cursor.execute('DELETE FROM assistant_meta WHERE key IN (?, ?, ?)', ('last_mode', 'last_ingested_at', 'documents_indexed'))
            cursor.executemany(
                'INSERT OR REPLACE INTO assistant_meta (key, value) VALUES (?, ?)',
                [
                    ('last_mode', mode),
                    ('last_ingested_at', ingested_at),
                    ('documents_indexed', str(len(rows))),
                ],
            )
            connection.commit()

    def count_documents(self) -> int:
        self.initialize_schema()
        with self.connect() as connection:
            return int(connection.execute('SELECT COUNT(*) FROM alertas_viales').fetchone()[0])

    def get_meta(self, key: str, default: str = '—') -> str:
        self.initialize_schema()
        with self.connect() as connection:
            row = connection.execute('SELECT value FROM assistant_meta WHERE key = ?', (key,)).fetchone()
            return str(row['value']) if row else default

    def fetch_alerts(self, limit: int | None = None) -> list[dict[str, Any]]:
        self.initialize_schema()
        sql = 'SELECT * FROM alertas_viales ORDER BY confianza_pct DESC, id ASC'
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += ' LIMIT ?'
            params = (limit,)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def fetch_active_alerts(self, limit: int = 5) -> list[dict[str, Any]]:
        self.initialize_schema()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM alertas_viales
                WHERE categoria != 'Tránsito Normal'
                ORDER BY confianza_pct DESC, id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_by_category(self, category: str, limit: int = 5) -> list[dict[str, Any]]:
        self.initialize_schema()
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT * FROM alertas_viales WHERE categoria = ? ORDER BY confianza_pct DESC, id ASC LIMIT ?',
                (category, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_by_location(self, location: str, limit: int = 5) -> list[dict[str, Any]]:
        self.initialize_schema()
        pattern = f'%{location}%'
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM alertas_viales
                WHERE LOWER(ubicacion) LIKE LOWER(?)
                   OR LOWER(detalle_completo) LIKE LOWER(?)
                ORDER BY confianza_pct DESC, id ASC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_by_keywords(self, keywords: list[str], limit: int = 5) -> list[dict[str, Any]]:
        self.initialize_schema()
        if not keywords:
            return []
        conditions = ' OR '.join('LOWER(detalle_completo) LIKE LOWER(?)' for _ in keywords)
        params = [f'%{keyword}%' for keyword in keywords]
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f'SELECT * FROM alertas_viales WHERE {conditions} ORDER BY confianza_pct DESC, id ASC LIMIT ?',
                params,
            ).fetchall()
            return [dict(row) for row in rows]
