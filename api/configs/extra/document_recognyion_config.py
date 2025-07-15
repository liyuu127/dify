from pydantic import Field
from pydantic_settings import BaseSettings


class DocumentRecognitionConfig(BaseSettings):
    DOCUMENT_RECOGNITION_URL: str = Field(
        description="Multimodal Document Recognition based on ocr",
        default="https://127.0.0.1:8059/htjx-api/",
    )
