from fastapi import APIRouter
from app.api.endpoints import predict, ocr

api_router = APIRouter()
api_router.include_router(predict.router, tags=["predict"])
api_router.include_router(ocr.router, tags=["ocr"])
