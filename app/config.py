from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    # Paperwise API key
    api_key: str = ""

    # Llm settings
    openai_api_key: SecretStr = SecretStr("")
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Ocr provider
    ocr: str = "onnxtr"

    # Papyrus settings (optional)
    papyrus_url: str = "https://api.papyrusai.de"
    papyrus_api_key: str = ""
    papyrus_api_secret: str = ""

    # Database
    db_path: str = "./paperwise.db"
    chroma: str = "./chroma"

    # Set thresholds and retries
    classify_threshold: float = 0.8
    max_retries: int = 2


settings = Settings()


def get_model() -> ChatOpenAI:
    return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key)
