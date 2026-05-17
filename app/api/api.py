from fastapi import APIRouter
from app.api.endpoints import predict, ocr, ai_insight, calculate_budget, category_prediction

api_router = APIRouter()

api_router.include_router(calculate_budget.router, tags=["calculate budget"])
api_router.include_router(category_prediction.router, tags=["category prediction"])
api_router.include_router(predict.router, tags=["predict"])
api_router.include_router(ocr.router, tags=["ocr"])
api_router.include_router(ai_insight.router, tags=["ai-insight"])