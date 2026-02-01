from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from dateutil.relativedelta import relativedelta
from datetime import date
from sqlalchemy import func

from app.extensions import db
from app.utils.files import save_temp_file
from ai.ocr.service import scan_file
from . import finance_bp
from .models import Expense, Category, Income, CategoryBudget, RecurringTransaction
from .services import generate_monthly_insights, materialize_recurring

@finance_bp.route("/")
@login_required
def dashboard():
    return render_template("finance/dashboard.html")

@finance_bp.route("/expenses")
@login_required
def expense_list():
    expenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .all()
    )
    return render_template("finance/expenses/list.html", expenses=expenses)

@finance_bp.route("/expenses/new", methods=["GET", "POST"])
@login_required
def expense_create():
    categories = Category.query.filter_by(
        user_id=current_user.id
    ).order_by(Category.parent_id, Category.name).all()

    if request.method == "POST":
        expense = Expense(
            user_id=current_user.id,
            category_id=request.form["category_id"],
            amount=request.form["amount"],
            merchant=request.form.get("merchant"),
            description=request.form.get("description"),
            payment_method=request.form.get("payment_method"),
            date=request.form["date"],
        )
        db.session.add(expense)
        db.session.commit()

        flash("Expense added", "success")
        return redirect(url_for("finance.expense_list"))

    return render_template(
        "finance/expenses/form.html",
        categories=categories,
        expense=None,
        today=date.today()
    )

@finance_bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def expense_edit(expense_id):
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    categories = Category.query.filter_by(
        user_id=current_user.id
    ).order_by(Category.parent_id, Category.name).all()

    if request.method == "POST":
        expense.category_id = request.form["category_id"]
        expense.amount = request.form["amount"]
        expense.merchant = request.form.get("merchant")
        expense.description = request.form.get("description")
        expense.payment_method = request.form.get("payment_method")
        expense.date = request.form["date"]

        db.session.commit()
        flash("Expense updated", "success")
        return redirect(url_for("finance.expense_list"))

    return render_template(
        "finance/expenses/form.html",
        categories=categories,
        expense=expense,
        today=expense.date
    )

@finance_bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def expense_delete(expense_id):
    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted", "success")
    return redirect(url_for("finance.expense_list"))

@finance_bp.route("/summary/monthly")
@login_required
def monthly_summary():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))

    materialize_recurring(
        current_user.id,
        year=year,
        month=month
    )

    # Current month range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Previous month
    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year

    prev_start = date(prev_year, prev_month, 1)
    prev_end = start_date

    # Total expenses
    total = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_date,
            Expense.date < end_date,
        )
        .scalar()
    )

    prev_total = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= prev_start,
            Expense.date < prev_end,
        )
        .scalar()
    )

    # Category breakdown
    by_category = (
        db.session.query(
            Category.name,
            func.sum(Expense.amount).label("total")
        )
        .join(Expense)
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_date,
            Expense.date < end_date,
        )
        .group_by(Category.name)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    delta = total - prev_total

    income_total = (
        db.session.query(func.coalesce(func.sum(Income.amount), 0))
        .filter(
            Income.user_id == current_user.id,
            Income.date >= start_date,
            Income.date < end_date,
        )
        .scalar()
    )

    net_balance = income_total - total

    savings_rate = None
    if income_total > 0:
        savings_rate = round((net_balance / income_total) * 100, 1)

    insights = generate_monthly_insights(
        income_total=income_total,
        expense_total=total,
        net_balance=net_balance,
        savings_rate=savings_rate,
        category_breakdown=by_category,
    )

    chart_labels = [name for name, _ in by_category]
    chart_values = [float(total) for _, total in by_category]

    months = []
    trend_labels = []
    trend_values = []

    cursor = start_date - relativedelta(months=5)

    for _ in range(6):
        next_month = cursor + relativedelta(months=1)

        month_total = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.user_id == current_user.id,
                Expense.date >= cursor,
                Expense.date < next_month,
            )
            .scalar()
        )

        trend_labels.append(cursor.strftime("%Y-%m"))
        trend_values.append(float(month_total))
        cursor = next_month

    budget_vs_actual = (
        db.session.query(
            Category.name,
            func.coalesce(func.sum(Expense.amount), 0).label("actual"),
            func.coalesce(CategoryBudget.amount, 0).label("budget"),
        )
        .join(Expense, Expense.category_id == Category.id)
        .outerjoin(
            CategoryBudget,
            (CategoryBudget.category_id == Category.id) &
            (CategoryBudget.user_id == current_user.id) &
            (CategoryBudget.year == year) &
            (CategoryBudget.month == month)
        )
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_date,
            Expense.date < end_date,
        )
        .group_by(Category.name, CategoryBudget.amount)
        .order_by(Category.name)
        .all()
    )

    budget_labels = [row[0] for row in budget_vs_actual]
    actual_values = [float(row.actual) for row in budget_vs_actual]
    budget_values = [float(row.budget) for row in budget_vs_actual]

    return render_template(
        "finance/summary/monthly.html",
        year=year,
        month=month,
        total=total,
        prev_total=prev_total,
        delta=delta,
        by_category=by_category,
        income_total=income_total,
        net_balance=net_balance,
        savings_rate=savings_rate,
        insights=insights,
        chart_labels=chart_labels,
        chart_values=chart_values,
        trend_labels=trend_labels,
        trend_values=trend_values,
        budget_labels=budget_labels,
        actual_values=actual_values,
        budget_values=budget_values
    )

@finance_bp.route("/income")
@login_required
def income_list():
    income_entries = (
        Income.query
        .filter_by(user_id=current_user.id)
        .order_by(Income.date.desc())
        .all()
    )
    return render_template(
        "finance/income/list.html",
        income_entries=income_entries
    )

@finance_bp.route("/income/new", methods=["GET", "POST"])
@login_required
def income_create():
    if request.method == "POST":
        income = Income(
            user_id=current_user.id,
            amount=request.form["amount"],
            source=request.form["source"],
            date=request.form["date"],
            is_recurring=bool(request.form.get("is_recurring")),
        )
        db.session.add(income)
        db.session.commit()

        flash("Income added", "success")
        return redirect(url_for("finance.income_list"))

    return render_template("finance/income/form.html", income=None)

@finance_bp.route("/income/<int:income_id>/edit", methods=["GET", "POST"])
@login_required
def income_edit(income_id):
    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        income.amount = request.form["amount"]
        income.source = request.form["source"]
        income.date = request.form["date"]
        income.is_recurring = bool(request.form.get("is_recurring"))

        db.session.commit()
        flash("Income updated", "success")
        return redirect(url_for("finance.income_list"))

    return render_template("finance/income/form.html", income=income)

@finance_bp.route("/income/<int:income_id>/delete", methods=["POST"])
@login_required
def income_delete(income_id):
    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(income)
    db.session.commit()

    flash("Income deleted", "success")
    return redirect(url_for("finance.income_list"))

@finance_bp.route("/categories")
@login_required
def category_list():
    categories = (
        Category.query
        .filter_by(user_id=current_user.id)
        .order_by(Category.parent_id, Category.name)
        .all()
    )
    return render_template(
        "finance/categories/list.html",
        categories=categories
    )

@finance_bp.route("/categories/new", methods=["GET", "POST"])
@login_required
def category_create():
    parents = Category.query.filter_by(
        user_id=current_user.id
    ).all()

    if request.method == "POST":
        category = Category(
            user_id=current_user.id,
            name=request.form["name"],
            parent_id=request.form.get("parent_id") or None,
        )
        db.session.add(category)
        db.session.commit()

        flash("Category created", "success")
        return redirect(url_for("finance.category_list"))

    return render_template(
        "finance/categories/form.html",
        category=None,
        parents=parents
    )

@finance_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def category_edit(category_id):
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first_or_404()

    parents = Category.query.filter(
        Category.user_id == current_user.id,
        Category.id != category.id
    ).all()

    if request.method == "POST":
        category.name = request.form["name"]
        category.parent_id = request.form.get("parent_id") or None

        db.session.commit()
        flash("Category updated", "success")
        return redirect(url_for("finance.category_list"))

    return render_template(
        "finance/categories/form.html",
        category=category,
        parents=parents
    )

@finance_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def category_delete(category_id):
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first_or_404()

    if category.children:
        flash("Cannot delete category with subcategories", "error")
        return redirect(url_for("finance.category_list"))

    from .models import Expense
    if Expense.query.filter_by(category_id=category.id).first():
        flash("Cannot delete category with expenses", "error")
        return redirect(url_for("finance.category_list"))

    db.session.delete(category)
    db.session.commit()

    flash("Category deleted", "success")
    return redirect(url_for("finance.category_list"))

@finance_bp.route("/recurring")
@login_required
def recurring_list():
    items = (
        RecurringTransaction.query
        .filter_by(user_id=current_user.id)
        .order_by(RecurringTransaction.type, RecurringTransaction.amount)
        .all()
    )

    return render_template(
        "finance/recurring/list.html",
        items=items
    )

@finance_bp.route("/recurring/new", methods=["GET", "POST"])
@login_required
def recurring_create():
    categories = Category.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        is_active = bool(request.form.get("is_active"))

        end_date = request.form.get("end_date")
        if is_active:
            end_date = None
        elif not end_date:
            flash("End date is required when recurring is inactive.", "error")
            return redirect(request.url)

        item = RecurringTransaction(
            user_id=current_user.id,
            is_active=is_active,
            type=request.form["type"],
            amount=request.form["amount"],
            description=request.form.get("description"),
            category_id=request.form.get("category_id") or None,
            start_date=request.form["start_date"],
            end_date=request.form.get("end_date") or None,
            day_of_month=request.form["day_of_month"],
        )

        db.session.add(item)
        db.session.commit()

        flash("Recurring transaction added", "success")
        return redirect(url_for("finance.recurring_list"))

    return render_template(
        "finance/recurring/form.html",
        item=None,
        categories=categories
    )

@finance_bp.route("/recurring/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def recurring_edit(item_id):
    item = RecurringTransaction.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    categories = Category.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        is_active = bool(request.form.get("is_active"))

        end_date = request.form.get("end_date")
        if is_active:
            end_date = None
        elif not end_date:
            flash("End date is required when recurring is inactive.", "error")
            return redirect(request.url)

        item.is_active = is_active
        item.type = request.form["type"]
        item.amount = request.form["amount"]
        item.description = request.form.get("description")
        item.category_id = request.form.get("category_id") or None
        item.start_date = request.form["start_date"]
        item.end_date = request.form.get("end_date") or None
        item.day_of_month = request.form["day_of_month"]

        db.session.commit()
        flash("Recurring transaction updated", "success")
        return redirect(url_for("finance.recurring_list"))

    return render_template(
        "finance/recurring/form.html",
        item=item,
        categories=categories
    )

@finance_bp.route("/recurring/<int:item_id>/delete", methods=["POST"])
@login_required
def recurring_delete(item_id):
    item = RecurringTransaction.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    flash("Recurring transaction deleted", "success")
    return redirect(url_for("finance.recurring_list"))

@finance_bp.route("/forecast/next-month")
@login_required
def next_month_forecast():
    from .services import (
        get_last_n_month_totals,
        get_next_month_recurring_total,
        forecast_next_month,
        calculate_trend_pct,
        generate_forecast_insights
    )

    monthly_totals = get_last_n_month_totals(
        user_id=current_user.id,
        n=6
    )

    recurring_total = get_next_month_recurring_total(
        user_id=current_user.id
    )

    forecast_data = forecast_next_month(
        monthly_totals,
        recurring_total
    )

    insights = generate_forecast_insights(
        forecast=forecast_data["forecast"],
        recurring_ratio=recurring_total / max(forecast_data["forecast"], 1),
        trend_pct=calculate_trend_pct(monthly_totals),
    )

    return render_template(
        "finance/forecast/next_month.html",
        forecast=forecast_data,
        insights=insights,
    )

@finance_bp.route("/forecast/compare")
@login_required
def compare_forecast():
    from .services import (
        get_last_n_month_totals,
        get_next_month_recurring_total,
        forecast_next_month,
    )
    from .ml_services import ml_forecast_next_month

    monthly_totals = get_last_n_month_totals(current_user.id, n=6)
    recurring_total = get_next_month_recurring_total(current_user.id)

    stat = forecast_next_month(monthly_totals, recurring_total)
    ml_value = ml_forecast_next_month(current_user.id)

    return render_template(
        "finance/forecast/compare.html",
        stat=stat,
        ml_value=ml_value,
        delta=(
            round(ml_value - stat["forecast"], 2)
            if ml_value is not None else None
        )
    )

@finance_bp.route("/expenses/scan", methods=["GET", "POST"])
@login_required
def scan_expense():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            return render_template(
                "finance/scan/upload.html",
                error="No file selected"
            )

        path = save_temp_file(file)
        parsed = scan_file(path)
        
        if "error" in parsed:
            return render_template(
                "finance/scan/upload.html",
                error=parsed["error"]
            )
        # Store ONLY small structured data
        print(parsed['date'])
        session["scan_result"] = {
            "amount": parsed["amount"],
            "date": parsed["date"]
                    if parsed["date"] else None,
            "merchant": parsed["merchant"],
            "ocr_confidence": parsed["ocr_confidence"],
            "overall_confidence": parsed["overall_confidence"],
        }

        return redirect(url_for("finance.review_scan"))

    return render_template("finance/scan/upload.html")

@finance_bp.route("/expenses/scan/review", methods=["GET", "POST"])
@login_required
def review_scan():
    data = session.get("scan_result")

    if not data:
        return redirect(url_for("finance.scan_expense"))

    if request.method == "POST":
        expense = Expense(
            user_id=current_user.id,
            amount=request.form["amount"],
            date=request.form["date"],
            merchant=request.form["merchant"],
            description=request.form["description"],
            category_id=request.form["category_id"],
        )

        db.session.add(expense)
        db.session.commit()

        session.pop("scan_result", None)
        return redirect(url_for("finance.expense_list"))

    return render_template(
        "finance/scan/review.html",
        data=data,
        categories=Category.query.all()
    )
