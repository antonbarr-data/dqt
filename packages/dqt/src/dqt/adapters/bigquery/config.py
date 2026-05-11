from dataclasses import dataclass, field


@dataclass
class BigQueryConfig:
    project: str = ""
    credentials_path: str = ""  # path to service account JSON; empty = ADC
    location: str = "US"
    max_bytes_billed: int = 50 * 1024 ** 3  # 50 GB cost guard — refuses dry-run estimates above this

    def to_client_kwargs(self) -> dict:
        kwargs: dict = {"project": self.project, "location": self.location}
        if self.credentials_path:
            from google.oauth2 import service_account
            kwargs["credentials"] = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery.readonly"],
            )
        return kwargs
