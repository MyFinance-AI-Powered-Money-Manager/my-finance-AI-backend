from fastapi import APIRouter, HTTPException
from sklearn.ensemble import RandomForestRegressor
from typing import List
from pydantic import BaseModel
import pandas as pd

router = APIRouter()

PAYDAY_DAYS = [25, 26, 27, 28] 
MIN_DAYS_FOR_TRAINING = 30

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

def makeModel(df, category: str, current_date):
    """
    Trains the model to predict the FINAL TOTAL for the month,
    based strictly on historical, completed months.
    """
    first_of_month = current_date.replace(day=1)
    
    features = [
        'day_of_month', 'days_until_month_end', 'is_payday', 
        'rolling_mean_7', 'rolling_sum_7', 'month_to_date_amount_before_today'
    ]
    
    try:
        cat_df = df[df['master_category'] == category].sort_values('date').reset_index(drop=True)
        
        train_df = cat_df[cat_df['date'] < first_of_month].dropna(subset=features + ['actual_month_total'])
        
        if len(train_df) < MIN_DAYS_FOR_TRAINING:
            return None

        X_train = train_df[features]
        y_train = train_df['actual_month_total']

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train) 

        return model
    except Exception as e:
        print(f"Failed to train model for {category}: {e}")
        return None

def predict(current_data, model):
    """
    Makes a ONE-SHOT prediction for the end of the month. No loops.
    """
    latest_data = current_data.iloc[-1]
    
    current_mtd_spend = latest_data['month_to_date_amount_before_today'] + latest_data['target_daily_category_amount']

    if model is None:
        return current_mtd_spend

    # Setup the feature array for "today"
    X_pred = pd.DataFrame([{
        'day_of_month': latest_data['day_of_month'],
        'days_until_month_end': latest_data['days_until_month_end'],
        'is_payday': latest_data['is_payday'],
        'rolling_mean_7': latest_data['rolling_mean_7'],
        'rolling_sum_7': latest_data['rolling_sum_7'],
        'month_to_date_amount_before_today': latest_data['month_to_date_amount_before_today']
    }])

    total_month_forecast = model.predict(X_pred)[0]

    return max(total_month_forecast, current_mtd_spend)

def predict_categories(df):
    categories = ['Hobi & Self-Reward','Jajan & Nongkrong', 'Kebutuhan Rumah & Mandi',
              'Lain-lain & Darurat', 'Makan & Minum Harian', 'Tagihan & Kewajiban',
              'Transportasi & Rutinitas']
    
    current_date = pd.Timestamp.now().normalize()
    result = {}
    
    for category in categories:
        model = makeModel(df, category=category, current_date=current_date)
        
        cat_df = df[df['master_category'] == category].sort_values('date').reset_index(drop=True)
        current_data = cat_df[cat_df['date'] <= current_date]
        
        if current_data.empty:
            result[category] = 0
            continue
            
        result[category] = predict(current_data, model)
        
    result['total'] = sum(result.values())
    return result

def to_features(df):
    df_clean = df.copy()
    required_columns = ["timestamp", "type", "amount", "master_category"]
    missing_columns = [col for col in required_columns if col not in df_clean.columns]

    if missing_columns:
        raise ValueError(f"Kolom wajib tidak ditemukan: {missing_columns}")

    df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], errors="coerce").dt.tz_localize(None)
    df_clean["amount"] = pd.to_numeric(df_clean["amount"], errors="coerce")
    df_clean = df_clean.dropna(subset=["timestamp", "type", "amount", "master_category"])
    df_clean["amount"] = df_clean["amount"].abs()
    df_clean["date"] = df_clean["timestamp"].dt.normalize()

    df_expense = df_clean[df_clean["type"].str.lower() == "expense"].copy()

    df_daily = (
        df_expense
        .groupby(["date", "master_category"], as_index=False)
        .agg(
            target_daily_category_amount=("amount", "sum"),
            transaction_count=("amount", "count"),
            avg_transaction_amount=("amount", "mean")
        )
    )

    all_dates = pd.date_range(
        start=df_expense["date"].min(),
        end=df_expense["date"].max(),
        freq="D"
    )
    all_categories = sorted(df_expense["master_category"].unique())

    full_grid = pd.MultiIndex.from_product(
        [all_dates, all_categories],
        names=["date", "master_category"]
    ).to_frame(index=False)

    df_features = full_grid.merge(df_daily, on=["date", "master_category"], how="left")

    fill_zero_cols = ["target_daily_category_amount", "transaction_count", "avg_transaction_amount"]
    df_features[fill_zero_cols] = df_features[fill_zero_cols].fillna(0)
    df_features = df_features.sort_values(["master_category", "date"]).reset_index(drop=True)

    df_features["day_of_week"] = df_features["date"].dt.dayofweek
    df_features["day_of_month"] = df_features["date"].dt.day
    df_features["year_month"] = df_features["date"].dt.to_period("M").astype(str)

    df_features["is_weekend"] = df_features["day_of_week"].isin([5, 6]).astype(int)
    df_features["is_payday"] = df_features["day_of_month"].isin(PAYDAY_DAYS).astype(int) 
    
    df_features["days_until_month_end"] = df_features["date"].dt.days_in_month - df_features["day_of_month"]

    target_col = "target_daily_category_amount"

    df_features["rolling_mean_7"] = (
        df_features.groupby("master_category")[target_col]
        .transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
    )

    df_features["rolling_sum_7"] = (
        df_features.groupby("master_category")[target_col]
        .transform(lambda x: x.shift(1).rolling(7, min_periods=1).sum())
    )

    df_features["month_to_date_amount_before_today"] = (
        df_features.groupby(["master_category", "year_month"])[target_col]
        .transform(lambda x: x.shift(1).cumsum())
    )

    df_features["actual_month_total"] = (
        df_features.groupby(["master_category", "year_month"])[target_col]
        .transform("sum")
    )

    feature_fill_cols = ["rolling_mean_7", "rolling_sum_7", "month_to_date_amount_before_today"]
    df_features[feature_fill_cols] = df_features[feature_fill_cols].fillna(0)

    return df_features

def to_dataframe(payload: FinancialPayload, type) -> dict:
    try:
        transactions_data = [t.model_dump() for t in payload.transactions]
        items_data = [i.model_dump() for i in payload.transaction_items]
        
        df_transactions = pd.DataFrame(transactions_data)
        df_items = pd.DataFrame(items_data)
        
        if type == 'df_joined':
            df_items.drop(columns=['id'], inplace=True)
            df_items.rename(columns={'transaction_id': 'id'}, inplace=True)

            df_joined = pd.merge(
                df_items, 
                df_transactions[['id', 'type', 'transaction_date']], 
                left_on='id', 
                right_on='id', 
                how='inner'
            )

            df_joined.drop(columns=['id'], inplace=True)
            df_joined.rename(columns=
                            {
                                'transaction_date': 'timestamp',
                                'item_name': 'title',
                                'subcategory': 'master_category',
                                'category': 'macro_category',
                                'price': 'amount',
                            }, inplace=True)
            return df_joined
        else:
            raise ValueError("Please input df_joined")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@router.post('/category-prediction')
async def category_prediction(payload: FinancialPayload):
    try:
      df = to_dataframe(payload, 'df_joined')
      feature_ready_df = to_features(df)
      predicted_categories = predict_categories(feature_ready_df)
      return predicted_categories
    except Exception as e:
        return f"Error: {e}"