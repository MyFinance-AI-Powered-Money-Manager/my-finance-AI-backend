import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler, MinMaxScaler
from pydantic import BaseModel
from typing import List

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

def to_dataframe(payload: FinancialPayload, type) -> dict:
    try:
        # Turn JSON payload into a format pandas can read with pydantic
        transactions_data = [t.model_dump() for t in payload.transactions]
        items_data = [i.model_dump() for i in payload.transaction_items]
        budgets_data = [b.model_dump() for b in payload.budgets]
        
        # Create dataframe
        df_transactions = pd.DataFrame(transactions_data)
        df_items = pd.DataFrame(items_data)
        df_budgets = pd.DataFrame(budgets_data)
        
        if type == 'df_joined':
            df_items.drop(columns=['id'], inplace=True)
            df_items.rename(columns={'transaction_id': 'id'}, inplace=True)
            print(df_items)
            print('columns: \n', df_items.columns)
            print('---------------------')
            print(df_transactions)
            print('columns: \n', df_transactions.columns)

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
        elif type == 'df_transactions':
            return df_transactions
        elif type == 'df_items':
            return df_items
        elif type == 'df_budgets':
            return df_budgets
        else:
            raise ValueError("Please input the second parameter as df_joined, df_transactions, df_items, or df_budgets")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

def standardize_mock_finance_columns(df):
    """
    Mapping kolom mock_finance_df_leak.csv ke format API:
    timestamp       -> transaction_date
    amount          -> total_amount
    macro_category  -> category
    master_category -> subcategory
    title           -> description
    """

    df = df.copy()

    rename_map = {
        "timestamp": "transaction_date",
        "amount": "total_amount",
        "macro_category": "category",
        "master_category": "subcategory",
        "title": "description"
    }

    df = df.rename(columns=rename_map)

    required_cols = [
        "transaction_date",
        "type",
        "total_amount",
        "category",
        "subcategory",
        "description"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Kolom wajib tidak ditemukan: {missing_cols}")

    return df


def clean_transaction_df(df):
    df = df.copy()

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")

    df = df.dropna(subset=[
        "transaction_date",
        "type",
        "total_amount",
        "category",
        "subcategory",
        "description"
    ])

    df["type"] = df["type"].astype(str).str.upper()
    df["category"] = df["category"].astype(str).str.upper()
    df["subcategory"] = df["subcategory"].astype(str)
    df["description"] = df["description"].astype(str)

    df["total_amount"] = df["total_amount"].abs()
    df["date"] = df["transaction_date"].dt.normalize()

    return df

def build_leak_candidate_table(df, small_transaction_threshold, min_frequency, min_total_spending, keywords):
    df_expense_local = df[df["type"] == "EXPENSE"].copy()

    df_small = df_expense_local[
        df_expense_local["total_amount"] <= small_transaction_threshold
    ].copy()

    df_small["description_text"] = df_small["description"].astype(str).str.lower()
    df_small["subcategory_text"] = df_small["subcategory"].astype(str).str.lower()
    df_small["category_text"] = df_small["category"].astype(str).str.lower()

    df_small["is_habit_keyword"] = df_small["description_text"].apply(
        lambda x: any(keyword in x for keyword in keywords['habit'])
    )

    df_small["is_lifestyle_keyword"] = (
        df_small["description_text"].apply(
            lambda x: any(keyword in x for keyword in keywords['lifestyle'])
        ) |
        df_small["subcategory_text"].apply(
            lambda x: any(keyword in x for keyword in keywords['lifestyle'])
        )
    )

    df_small["is_transport_keyword"] = (
        df_small["description_text"].apply(
            lambda x: any(keyword in x for keyword in keywords['transport'])
        ) |
        df_small["subcategory_text"].apply(
            lambda x: any(keyword in x for keyword in keywords['transport'])
        )
    )

    leak_summary = (
        df_small
        .groupby(["description", "category", "subcategory"], as_index=False)
        .agg(
            frequency=("total_amount", "count"),
            total_spending=("total_amount", "sum"),
            avg_spending=("total_amount", "mean"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            habit_keyword_count=("is_habit_keyword", "sum"),
            lifestyle_keyword_count=("is_lifestyle_keyword", "sum"),
            transport_keyword_count=("is_transport_keyword", "sum")
        )
    )

    leak_summary["active_days"] = (
        leak_summary["last_date"] - leak_summary["first_date"]
    ).dt.days + 1

    leak_summary["avg_days_between_purchase"] = (
        leak_summary["active_days"] / leak_summary["frequency"]
    )

    leak_summary["is_repeated_small_spending"] = (
        (leak_summary["frequency"] >= min_frequency) &
        (leak_summary["total_spending"] >= min_total_spending)
    ).astype(int)

    leak_summary["category_text"] = leak_summary["category"].astype(str).str.lower()

    return leak_summary, df_small


def classify_rule_based_leak(row):
    is_repeated = row["is_repeated_small_spending"] == 1

    is_needs = row["category_text"] == "needs"
    is_wants = row["category_text"] == "wants"
    is_others = row["category_text"] == "others"

    is_habit = row["habit_keyword_count"] > 0
    is_lifestyle = row["lifestyle_keyword_count"] > 0
    is_transport = row["transport_keyword_count"] > 0

    if not is_repeated:
        return "Normal"

    if is_transport and is_needs:
        return "Recurring Essential"

    if is_transport and is_wants:
        return "Lifestyle Leak"

    if is_needs:
        return "Recurring Essential"

    if is_habit:
        return "Habit Leak"

    if is_lifestyle or is_wants or is_others:
        return "Lifestyle Leak"

    return "Potential Leak"


def classify_ml_leak(row):
    is_anomaly = row["is_ml_anomaly"] == 1
    is_relevant = row["is_financially_relevant_anomaly"] == 1

    is_needs = row["category_text"] == "needs"
    is_wants = row["category_text"] == "wants"
    is_others = row["category_text"] == "others"
    is_transport = row["transport_keyword_count"] > 0

    if not is_anomaly:
        return "Normal"

    if not is_relevant:
        return "ML Minor Anomaly"

    if is_needs and is_transport:
        return "ML Recurring Essential Anomaly"

    if is_needs:
        return "ML Needs Anomaly"

    if is_wants:
        return "ML Lifestyle Leak Anomaly"

    if is_others:
        return "ML Other Leak Anomaly"

    return "ML Potential Leak Anomaly"


def calculate_financial_score_from_dataframe(df, leak_summary=None, budgets=None):
    df = df.copy()

    df["type"] = df["type"].astype(str).str.upper()
    df["category"] = df["category"].astype(str).str.upper()
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)

    df_expense_local = df[df["type"] == "EXPENSE"].copy()
    df_income_local = df[df["type"] == "INCOME"].copy()

    total_income = df_income_local["total_amount"].sum()
    total_expense = df_expense_local["total_amount"].sum()
    net_cashflow = total_income - total_expense

    savings_rate = net_cashflow / total_income if total_income > 0 else 0

    category_expense = (
        df_expense_local
        .groupby("category", as_index=False)["total_amount"]
        .sum()
    )

    category_dict = dict(zip(category_expense["category"], category_expense["total_amount"]))

    needs_amount = category_dict.get("NEEDS", 0)
    wants_amount = category_dict.get("WANTS", 0)
    others_amount = category_dict.get("OTHERS", 0)

    needs_ratio = needs_amount / total_expense if total_expense > 0 else 0
    wants_ratio = wants_amount / total_expense if total_expense > 0 else 0
    others_ratio = others_amount / total_expense if total_expense > 0 else 0

    daily_expense = (
        df_expense_local
        .groupby("date", as_index=False)["total_amount"]
        .sum()
    )

    daily_mean = daily_expense["total_amount"].mean()
    daily_std = daily_expense["total_amount"].std()

    spending_volatility = daily_std / daily_mean if daily_mean > 0 else 0

    if leak_summary is not None and not leak_summary.empty:
        final_potential_leak_count = int(leak_summary["is_final_potential_leak"].sum())

        final_potential_leak_spending = leak_summary.loc[
            leak_summary["is_final_potential_leak"] == 1,
            "total_spending"
        ].sum()
    else:
        final_potential_leak_count = 0
        final_potential_leak_spending = 0

    potential_leak_ratio = (
        final_potential_leak_spending / total_expense if total_expense > 0 else 0
    )

    budget_used_ratio_total = 0
    overbudget_category_count = 0

    if budgets is not None and len(budgets) > 0:
        budget_df = pd.DataFrame(budgets)

        budget_df["category"] = budget_df["category"].astype(str).str.upper()
        budget_df["limit_amount"] = pd.to_numeric(
            budget_df["limit_amount"], errors="coerce"
        ).fillna(0)

        expense_by_category = (
            df_expense_local
            .groupby("category", as_index=False)["total_amount"]
            .sum()
            .rename(columns={"total_amount": "actual_spending"})
        )

        budget_check = budget_df.merge(
            expense_by_category,
            on="category",
            how="left"
        )

        budget_check["actual_spending"] = budget_check["actual_spending"].fillna(0)

        budget_check["budget_used_ratio"] = np.where(
            budget_check["limit_amount"] > 0,
            budget_check["actual_spending"] / budget_check["limit_amount"],
            0
        )

        total_budget = budget_check["limit_amount"].sum()
        total_budget_spending = budget_check["actual_spending"].sum()

        budget_used_ratio_total = (
            total_budget_spending / total_budget if total_budget > 0 else 0
        )

        overbudget_category_count = int(
            (budget_check["budget_used_ratio"] > 1).sum()
        )

    financial_score = 100
    score_reasons = []

    if net_cashflow < 0:
        financial_score -= 25
        score_reasons.append("Cashflow negatif karena pengeluaran lebih besar dari pemasukan.")
    elif savings_rate < 0.10:
        financial_score -= 8
        score_reasons.append("Savings rate masih rendah.")

    if wants_ratio > 0.35:
        financial_score -= 15
        score_reasons.append("Proporsi pengeluaran WANTS cukup tinggi.")
    elif wants_ratio > 0.25:
        financial_score -= 8
        score_reasons.append("Proporsi pengeluaran WANTS perlu dipantau.")

    if others_ratio > 0.15:
        financial_score -= 10
        score_reasons.append("Proporsi pengeluaran OTHERS cukup tinggi.")

    if final_potential_leak_count >= 5:
        financial_score -= 20
        score_reasons.append("Terdapat banyak potensi leak.")
    elif final_potential_leak_count >= 1:
        financial_score -= 10
        score_reasons.append("Terdapat beberapa potensi leak.")

    if potential_leak_ratio > 0.15:
        financial_score -= 10
        score_reasons.append("Total leak cukup besar dibanding total pengeluaran.")

    if budget_used_ratio_total > 1:
        financial_score -= 15
        score_reasons.append("Total pengeluaran melewati budget.")
    elif budget_used_ratio_total > 0.85:
        financial_score -= 8
        score_reasons.append("Pemakaian budget sudah mendekati batas.")

    if spending_volatility > 1:
        financial_score -= 10
        score_reasons.append("Pengeluaran harian cukup fluktuatif.")

    financial_score = max(0, min(100, financial_score))

    if financial_score >= 80:
        score_category = "Excellent"
    elif financial_score >= 65:
        score_category = "Good"
    elif financial_score >= 50:
        score_category = "Fair"
    else:
        score_category = "Needs Attention"

    if len(score_reasons) == 0:
        score_reasons.append("Kondisi keuangan relatif stabil dan tidak banyak risiko terdeteksi.")

    return {
        "financial_score": int(financial_score),
        "score_category": score_category,
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "net_cashflow": float(net_cashflow),
        "savings_rate": float(savings_rate),
        "needs_ratio": float(needs_ratio),
        "wants_ratio": float(wants_ratio),
        "others_ratio": float(others_ratio),
        "final_potential_leak_count": int(final_potential_leak_count),
        "final_potential_leak_spending": float(final_potential_leak_spending),
        "potential_leak_ratio": float(potential_leak_ratio),
        "budget_used_ratio_total": float(budget_used_ratio_total),
        "overbudget_category_count": int(overbudget_category_count),
        "spending_volatility": float(spending_volatility),
        "score_reason": " ".join(score_reasons)
    }

def leak_and_financial_score(df):

    df_raw = df

    df_standardized = standardize_mock_finance_columns(df_raw)
    df_clean = clean_transaction_df(df_standardized)

    df_expense = df_clean[df_clean["type"] == "EXPENSE"].copy()
    df_income = df_clean[df_clean["type"] == "INCOME"].copy()

    # ==============================
    # CELL 3 - BUILD LEAK CANDIDATE + RULE-BASED LEAK
    # ==============================

    small_transaction_threshold = 50000
    min_frequency = 3
    min_total_spending = 100000

    habit_keywords = [
        "kopi", "coffee", "rokok", "snack", "jajan",
        "boba", "minuman", "es teh", "cafe", "nongkrong"
    ]

    lifestyle_keywords = [
        "hobi", "self", "reward", "main", "game",
        "top up", "topup", "hiburan", "nongkrong",
        "shopping", "belanja"
    ]

    transport_keywords = [
        "gojek", "grab", "ojek", "transport",
        "angkot", "bus", "kereta"
    ]

    keywords = {
        'habit': habit_keywords,
        'lifestyle': lifestyle_keywords,
        'transport': transport_keywords
    }

    leak_summary, df_small = build_leak_candidate_table(df_clean,
                                                        small_transaction_threshold,
                                                        min_frequency,
                                                        min_total_spending,
                                                        keywords)

    leak_summary["rule_leak_type"] = leak_summary.apply(classify_rule_based_leak, axis=1)

    leak_summary["is_rule_potential_leak"] = leak_summary["rule_leak_type"].isin([
        "Habit Leak",
        "Lifestyle Leak",
        "Potential Leak"
    ]).astype(int)

    score_feature_columns = [
        "frequency",
        "total_spending",
        "avg_spending",
        "habit_keyword_count",
        "lifestyle_keyword_count"
    ]

    score_features = leak_summary[score_feature_columns].copy()
    score_features = score_features.replace([np.inf, -np.inf], np.nan).fillna(0)

    for col in ["frequency", "total_spending", "avg_spending"]:
        score_features[col] = np.log1p(score_features[col])

    leak_score_scaler = MinMaxScaler()
    scaled_score_features = leak_score_scaler.fit_transform(score_features)

    leak_score_weights = np.array([0.30, 0.35, 0.10, 0.15, 0.10])

    leak_score_raw = scaled_score_features @ leak_score_weights

    leak_summary["leak_score"] = leak_score_raw * 100
    leak_summary.loc[leak_summary["category_text"] == "needs", "leak_score"] *= 0.65
    leak_summary["leak_score"] = leak_summary["leak_score"].clip(0, 100).round(2)

    # ML anomaly features
    leak_summary["is_needs"] = (leak_summary["category_text"] == "needs").astype(int)
    leak_summary["is_wants"] = (leak_summary["category_text"] == "wants").astype(int)
    leak_summary["is_others"] = (leak_summary["category_text"] == "others").astype(int)

    ml_features = [
        "frequency",
        "total_spending",
        "avg_spending",
        "active_days",
        "avg_days_between_purchase",
        "habit_keyword_count",
        "lifestyle_keyword_count",
        "transport_keyword_count",
        "leak_score",
        "is_needs",
        "is_wants",
        "is_others"
    ]

    X = leak_summary[ml_features].copy()
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

    log_cols = [
        "frequency",
        "total_spending",
        "avg_spending",
        "active_days",
        "avg_days_between_purchase"
    ]

    for col in log_cols:
        X[col] = np.log1p(X[col])

    ml_scaler = RobustScaler()
    X_scaled = ml_scaler.fit_transform(X)

    isolation_model = IsolationForest(
        n_estimators=300,
        contamination=0.10,
        random_state=42
    )

    leak_summary["ml_anomaly_label"] = isolation_model.fit_predict(X_scaled)
    leak_summary["is_ml_anomaly"] = (leak_summary["ml_anomaly_label"] == -1).astype(int)

    raw_score = -isolation_model.decision_function(X_scaled)

    training_score_min = raw_score.min()
    training_score_max = raw_score.max()

    if training_score_max - training_score_min == 0:
        leak_summary["ml_anomaly_score"] = 0
    else:
        leak_summary["ml_anomaly_score"] = (
            (raw_score - training_score_min) /
            (training_score_max - training_score_min) * 100
        )

    leak_summary["ml_anomaly_score"] = leak_summary["ml_anomaly_score"].clip(0, 100).round(2)

    leak_summary["is_financially_relevant_anomaly"] = (
        (leak_summary["frequency"] >= min_frequency) |
        (leak_summary["total_spending"] >= min_total_spending) |
        (leak_summary["leak_score"] >= 40)
    ).astype(int)

    leak_summary["ml_leak_type"] = leak_summary.apply(classify_ml_leak, axis=1)

    leak_summary["is_ml_potential_leak"] = (
        (leak_summary["is_ml_anomaly"] == 1) &
        (leak_summary["is_financially_relevant_anomaly"] == 1) &
        (leak_summary["category_text"].isin(["wants", "others"]))
    ).astype(int)

    leak_summary["is_final_potential_leak"] = (
        (leak_summary["is_rule_potential_leak"] == 1) |
        (leak_summary["is_ml_potential_leak"] == 1)
    ).astype(int)

    leak_summary = leak_summary.sort_values(
        by=[
            "is_final_potential_leak",
            "is_ml_anomaly",
            "ml_anomaly_score",
            "leak_score",
            "total_spending"
        ],
        ascending=False
    ).reset_index(drop=True)

    # ==============================
    # CELL 5 - FINANCIAL SCORE
    # ==============================

    financial_score_result = calculate_financial_score_from_dataframe(
        df_clean,
        leak_summary=leak_summary,
        budgets=None
    )

    leak_products = leak_summary[leak_summary["is_final_potential_leak"] == 1]
    leak_products_list = leak_products['description'].to_list()

    result = {"financial summary":financial_score_result,
            "leak_products": leak_products_list
    }
    return result

@router.post('/leak-and-financial-score')
async def get_leak_and_financial_score(payload: FinancialPayload):
    try:
        df = to_dataframe(payload, 'df_joined')
        result = leak_and_financial_score(df)
        return result
    except Exception as e:
        return f"Error: {e}"