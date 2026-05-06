from pydantic import BaseModel
from typing import List

class ProductInput(BaseModel):
    name: str

class BatchInput(BaseModel):
    names: List[str]
