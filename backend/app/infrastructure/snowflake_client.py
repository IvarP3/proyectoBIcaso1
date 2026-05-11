from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import snowflake.connector

from app.core.config import Settings


@dataclass
class SnowflakeClient:
    settings: Settings

    def connect(self):
        if not self.settings.has_snowflake_credentials():
            raise ValueError('Snowflake credentials are incomplete.')

        return snowflake.connector.connect(
            account=self.settings.snowflake_account,
            user=self.settings.snowflake_user,
            password=self.settings.snowflake_password,
            warehouse=self.settings.snowflake_warehouse,
            database=self.settings.snowflake_database,
            schema=self.settings.snowflake_schema,
            role=self.settings.snowflake_role,
            client_session_keep_alive=True,
        )

    def test_connection(self) -> bool:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                _ = cursor.fetchone()
            return True
        finally:
            connection.close()

    def fetch_dataframe(self, query: str) -> pd.DataFrame:
        connection = self.connect()
        try:
            return pd.read_sql(query, connection)
        finally:
            connection.close()
