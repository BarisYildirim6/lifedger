import torch
import numpy as np
from sqlalchemy import func, text
from .services import get_last_n_month_totals, get_next_month_recurring_total
from .models import Income
from ml.model import ExpenseLSTM
from ml.predict import predict_next
from ml.datasets import build_sequences

from app import db

def ml_forecast_next_month(user_id):
    data = get_monthly_ml_features(user_id)

    if len(data) < 7:
        return None  # not enough data

    X, _ = build_sequences(np.array(data), window=6)
    last_sequence = torch.tensor(X[-1:]).float().cuda()

    model = ExpenseLSTM(input_size=last_sequence.shape[-1]).cuda()
    model.load_state_dict(torch.load("ml/checkpoints/expense_lstm.pt"))

    prediction = predict_next(model, last_sequence)

    return round(prediction, 2)

def get_monthly_ml_features(user_id, n=12):
    expense_totals = get_last_n_month_totals(user_id, n)
    
    income_rows = (
        db.session.query(
            func.date_trunc("month", Income.date).label("month"),
            func.sum(Income.amount).label("total"),
        )
        .filter(Income.user_id == user_id)
        .group_by(text('month'))
        .order_by(text('month DESC'))
        .limit(n)
        .all()
    )
    income_totals = [float(r[1]) for r in income_rows]

    recurring = get_next_month_recurring_total(user_id)

    # align lengths (very important)
    min_len = min(len(expense_totals), len(income_totals))
    expense_totals = expense_totals[:min_len]
    income_totals = income_totals[:min_len]

    data = []
    for e, i in zip(expense_totals, income_totals):
        data.append([e, i, recurring])

    return list(reversed(data))  # oldest → newest