from pydantic import BaseModel
from typing import List, Literal, Dict
from fastapi import APIRouter, HTTPException
import pandas as pd

router = APIRouter()

class Transaction(BaseModel):
    id: str
    wallet_id: str
    type: str
    total_amount: int
    category: str
    subcategory: str
    description: str
    transaction_date: str

class TransactionItem(BaseModel):
    id: str
    transaction_id: str
    item_name: str
    price: int
    category: str
    subcategory: str

class Budget(BaseModel):
    id: str
    category: str
    limit_amount: int
    month_period: str

class FinancialPayload(BaseModel):
    user_id: str
    month_period: str
    transactions: List[Transaction]
    transaction_items: List[TransactionItem]
    budgets: List[Budget]

@router.post('/budget-calculator')
async def calculate_budget(payload: FinancialPayload):
    try:
        json_data = payload.model_dump()
        budgets = {}
        # Split JSON into variables
        json_transactions = json_data['transactions']
        json_transaction_items = json_data['transaction_items']
        json_budgets = json_data['budgets']
        for budget in json_budgets:
            budgets[budget['category']] = budget['limit_amount']

        # Convert JSON into pandas dataframe
        df_transactions = pd.DataFrame(json_transactions)
        df_transaction_items = pd.DataFrame(json_transaction_items)
        df_joined = pd.merge(df_transactions[['id','transaction_date', 'type']], df_transaction_items[['transaction_id', 'category', 'price', 'subcategory']], left_on='id', right_on='transaction_id')
        df_joined.drop(['transaction_id', 'id'], axis=1, inplace=True)
        df_expense = df_joined[df_joined['type'] == 'EXPENSE']

        for category in budgets:
            for index, row in df_expense.iterrows():
                df_category = row['category']
                df_subcategory = row['subcategory']
                if category == df_category:
                    budgets[category] -= row['price']
                if category == df_subcategory:
                    budgets[category] -= row['price']

        return {"budgets": budgets}
    except Exception as e:
        return {"error": str(e)}