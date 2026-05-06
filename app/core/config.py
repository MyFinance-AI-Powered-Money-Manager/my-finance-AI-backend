import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Product Categorization API"
    VERSION: str = "1.0.0"
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/product_category_classifier.keras")
    METADATA_PATH: str = os.getenv("METADATA_PATH", "models/model_metadata.json")

settings = Settings()
