from dataclasses import dataclass


@dataclass
class DatabricksConfig:
    server_hostname: str = ""   # e.g. "adb-123456789.azuredatabricks.net"
    http_path: str = ""         # e.g. "/sql/1.0/warehouses/abc123"
    access_token: str = ""      # personal access token or OAuth M2M token
    catalog: str = "hive_metastore"  # Unity Catalog name; "hive_metastore" for legacy
    schema: str = "default"

    def to_client_kwargs(self) -> dict:
        return {
            "server_hostname": self.server_hostname,
            "http_path": self.http_path,
            "access_token": self.access_token,
            "catalog": self.catalog,
            "schema": self.schema,
        }
