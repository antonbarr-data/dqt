from dataclasses import dataclass


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "postgres"
    username: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"

    def to_conn_str(self) -> str:
        return (
            f"postgresql+psycopg2://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
        )
