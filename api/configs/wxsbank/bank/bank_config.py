from pydantic import Field
from pydantic_settings import BaseSettings


class BankConfig(BaseSettings):
    WXSBANK_URL: str = Field(
        description="BankConfig",
        default=False,
    )
