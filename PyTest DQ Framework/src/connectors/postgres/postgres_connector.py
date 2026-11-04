
import pandas as pd


class PostgresConnectorContextManager:
    def __init__(self, db_user, db_password, db_host, db_name, db_port):
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.db_port = db_port
        self.connection = None

    def __enter__(self):
        import psycopg2

        self.connection = psycopg2.connect(
            host=self.db_host,
            dbname=self.db_name,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        return False

    def get_data_sql(self, sql):
        if self.connection is None:
            raise RuntimeError("PostgreSQL connection has not been opened")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                column_names = [column[0] for column in cursor.description or []]
                rows = cursor.fetchall()
        except Exception:
            self.connection.rollback()
            raise
        return pd.DataFrame(rows, columns=column_names)


