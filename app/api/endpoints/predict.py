from fastapi import APIRouter
from app.schemas.predict import ProductInput, BatchInput
from app.services.predictor_service import ProductCategoryPredictor, MultiHeadSelfAttentionLayer, FocalLoss
from app.core.config import settings

router = APIRouter()

predictor = ProductCategoryPredictor(
    model_path=settings.MODEL_PATH,
    metadata_path=settings.METADATA_PATH,
    custom_objects={
        "MultiHeadSelfAttentionLayer": MultiHeadSelfAttentionLayer,
        "FocalLoss": FocalLoss
    }
)

@router.post("/predick")
def predict(data: ProductInput):
    return predictor.predict(data.name) 

@router.post("/predict-batch")
def predict_batch(data: BatchInput):
    if len(data.names) == 0:
        return []

    df = predictor.predict_batch(data.names)
    return df.to_dict(orient="records")
