from pydantic import Field
from pydantic_settings import BaseSettings


class BankConfig(BaseSettings):
    WXSBANK_URL: str = Field(
        description="BankConfig",
        default="https://127.0.0.1:8059/htjx-api/",
    )
