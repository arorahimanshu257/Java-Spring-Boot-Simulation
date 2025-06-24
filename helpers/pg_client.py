import psycopg2
from psycopg2 import pool
import os
from helpers.logger_config import logger
import urllib.parse


# os.environ["PERSISTENT_LOGGING"] = "True"
# os.environ["DB_URL"] = "57.152.8.175:5432/postgres"
# os.environ["DB_PASSWORD"] = "AvaPlusDADb%%.1"
# os.environ["DB_USER"] = "postgres"

class PostgresClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_connection_pool()
        return cls._instance

    def _initialize_connection_pool(self):

        try:
            db_url = os.getenv('DB_URL')
            db_username = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')

            if not all([db_url, db_username, db_password]):
                raise ValueError("Missing required database connection parameters")

            encoded_password = urllib.parse.quote_plus(db_password)

            self.connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=f"postgresql://{db_username}:{encoded_password}@{db_url}"
            )
        except (Exception, psycopg2.Error) as error:
            logger.error(f"Error while connecting to PostgreSQL {error}")
            raise Exception(f"Error while connecting to PostgreSQL {error}")

    def get_connection(self):
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        self.connection_pool.putconn(conn)

    def close_all_connections(self):
        self.connection_pool.closeall()

postgres_client = PostgresClient() if os.getenv("PERSISTENT_LOGGING") else None