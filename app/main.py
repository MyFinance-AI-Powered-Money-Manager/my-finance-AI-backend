from fastapi import FastAPI
from pydantic import BaseModel
from app.predictor import (
    ProductCategoryPredictor,
    MultiHeadSelfAttentionLayer,
    FocalLoss
)
from typing import List

app = FastAPI()

predictor = ProductCategoryPredictor(
    model_path="models/product_category_classifier.keras",
    metadata_path="models/model_metadata.json",
    custom_objects={
        "MultiHeadSelfAttentionLayer": MultiHeadSelfAttentionLayer,
        "FocalLoss": FocalLoss
    }
)

class ProductInput(BaseModel):
    name: str

class BatchInput(BaseModel):
    names: List[str]

@app.get("/")
def root():
    return {"message": "API running"}

@app.post("/predict")
def predict(data: ProductInput):
    return predictor.predict(data.name) 

@app.post("/predict-batch")
def predict_batch(data: BatchInput):
    if len(data.names) == 0:
        return []

    df = predictor.predict_batch(data.names)
    return df.to_dict(orient="records")