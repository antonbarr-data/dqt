from dataclasses import dataclass


@dataclass
class SnowflakeConfig:
    account: str = ""        # e.g. "myorg-myaccount" (ORG-ACCOUNT format)
    username: str = ""
    password: str = ""
    database: str = ""
    warehouse: str = ""      # compute warehouse name
    role: str = ""           # optional; defaults to user's default role

    def to_client_kwargs(self) -> dict:
        kwargs: dict = {
            "account": self.account,
            "user": self.username,
            "password": self.password,
            "database": self.database,
        }
        if self.warehouse:
            kwargs["warehouse"] = self.warehouse
        if self.role:
            kwargs["role"] = self.role
        return kwargs
