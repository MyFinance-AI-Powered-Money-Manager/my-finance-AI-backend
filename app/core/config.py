import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Product Categorization API"
    VERSION: str = "1.0.0"
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/product_category_classifier.keras")
    METADATA_PATH: str = os.getenv("METADATA_PATH", "models/model_metadata.json")

    # AI Insight
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    INTERNAL_SERVICE_KEY: str | None = os.getenv("INTERNAL_SERVICE_KEY")

settings = Settings()
