from pydantic import Field
from pydantic_settings import BaseSettings


class BankConfig(BaseSettings):
    WXSBANK_URL: str = Field(
        description="BankConfig",
        default="https://47.109.146.94:8059/htjx-api/",
    )
