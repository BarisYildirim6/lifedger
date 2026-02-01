from datetime import date
from sqlalchemy import func
from statistics import stdev
from app import db
from .models import RecurringTransaction, Expense, Income

def calculate_trend_pct(monthly_totals):
    """
    Compares last 2 months
    """
    if len(monthly_totals) < 2:
        return 0.0

    last = monthly_totals[0]
    prev = monthly_totals[1]

    if prev == 0:
        return 0.0

    return ((last - prev) / prev) * 100

def get_next_month_recurring_total(user_id):
    today = date.today()
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1

    recurring = (
        RecurringTransaction.query
        .filter_by(user_id=user_id)
        .all()
    )

    total = 0.0

    for r in recurring:
        if r.frequency == "monthly":
            total += r.amount
        elif r.frequency == "yearly" and r.start_date.month == next_month:
            total += r.amount

    return float(total)

def generate_forecast_insights(
    forecast,
    recurring_ratio,
    trend_pct
):
    insights = []

    if recurring_ratio > 0.6:
        insights.append(
            "A large portion of your spending is fixed recurring costs."
        )

    if trend_pct > 10:
        insights.append(
            f"Your expenses have increased by {trend_pct:.1f}% recently."
        )

    insights.append(
        "Forecast is based on your last 3 months of spending and active recurring expenses."
    )

    return insights

def forecast_next_month(monthly_totals, recurring_total):
    """
    monthly_totals: list of floats (most recent first)
    recurring_total: float
    """

    if len(monthly_totals) < 3:
        base = sum(monthly_totals) / max(len(monthly_totals), 1)
    else:
        base = (
            monthly_totals[0] * 0.5 +
            monthly_totals[1] * 0.3 +
            monthly_totals[2] * 0.2
        )

    forecast = base + recurring_total

    volatility = stdev(monthly_totals) if len(monthly_totals) >= 2 else 0

    return {
        "forecast": round(forecast, 2),
        "low": round(forecast - volatility, 2),
        "high": round(forecast + volatility, 2),
        "volatility": round(volatility, 2),
    }

def get_last_n_month_totals(user_id, n=6):
    """
    Returns a list of monthly expense totals
    ordered from most recent to oldest
    """

    rows = (
        db.session.query(
            func.date_trunc("month", Expense.date).label("month"),
            func.sum(Expense.amount).label("total"),
        )
        .filter(Expense.user_id == user_id)
        .group_by("month")
        .order_by(func.date_trunc("month", Expense.date).desc())
        .limit(n)
        .all()
    )

    return [float(row.total) for row in rows]

def materialize_recurring(user_id, year, month):
    target_date = date(year, month, 1)

    recurrences = RecurringTransaction.query.filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.start_date <= target_date,
        (RecurringTransaction.end_date == None) |
        (RecurringTransaction.end_date >= target_date)
    ).all()

    for r in recurrences:
        entry_date = date(year, month, min(r.day_of_month, 28))

        exists = (
            Expense.query.filter_by(
                user_id=user_id,
                date=entry_date,
                amount=r.amount,
                category_id=r.category_id,
            ).first()
            if r.type == "expense"
            else
            Income.query.filter_by(
                user_id=user_id,
                date=entry_date,
                amount=r.amount,
            ).first()
        )

        if exists:
            continue

        if r.type == "expense":
            db.session.add(Expense(
                user_id=user_id,
                amount=r.amount,
                date=entry_date,
                category_id=r.category_id,
                description=r.description,
            ))
        else:
            db.session.add(Income(
                user_id=user_id,
                amount=r.amount,
                date=entry_date,
                description=r.description,
            ))

    db.session.commit()

def materialize_recurring_expenses(today: date | None = None):
    if today is None:
        today = date.today()

    rules = RecurringTransaction.query.filter_by(
        is_active=True,
        type="expense"
    ).all()

    for rule in rules:
        if not should_generate(rule, today):
            continue

        exists = Expense.query.filter_by(
            recurring_id=rule.id,
            date=today
        ).first()

        if exists:
            continue

        expense = Expense(
            user_id=rule.user_id,
            category_id=rule.category_id,
            amount=rule.amount,
            description=rule.description,
            date=today,
            recurring_id=rule.id
        )

        db.session.add(expense)

    db.session.commit()

def should_generate(rule, today: date) -> bool:
    # 1. Day of month must match
    if today.day != rule.day_of_month:
        return False

    # 2. Must be after start date
    if today < rule.start_date:
        return False

    # 3. Must be before end date (if defined)
    if rule.end_date and today > rule.end_date:
        return False

    return True

def generate_monthly_insights(
    income_total,
    expense_total,
    net_balance,
    savings_rate,
    category_breakdown
):
    insights = []

    if income_total == 0:
        insights.append("No income recorded for this month.")
        return insights

    if net_balance < 0:
        insights.append("You spent more than you earned this month.")
    else:
        insights.append(
            f"You saved {savings_rate}% of your income this month."
        )

    if savings_rate is not None:
        if savings_rate < 10:
            insights.append("Savings rate is below 10%. Consider reducing expenses.")
        elif savings_rate >= 20:
            insights.append("Great job! Your savings rate is above 20%.")

    if category_breakdown:
        top_category, top_amount = category_breakdown[0]
        insights.append(
            f"Your biggest expense category was '{top_category}'."
        )

    return insights