from app.extensions import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    name = db.Column(db.String(100), nullable=False)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=True
    )

    parent = db.relationship(
        "Category",
        remote_side=[id],
        backref="children"
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", "parent_id",
                            name="uq_user_category"),
    )

    def __repr__(self):
        return f"<Category {self.name}>"

class Income(db.Model):
    __tablename__ = "income"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)

    is_recurring = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Income {self.amount} from {self.source}>"

class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False
    )

    recurring_id = db.Column(
        db.Integer,
        db.ForeignKey("recurring_transactions.id"),
        nullable=True
    )

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    merchant = db.Column(db.String(255))
    description = db.Column(db.String(255))
    payment_method = db.Column(db.String(50))
    date = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    category = db.relationship("Category")
    recurring = db.relationship("RecurringTransaction", back_populates="expenses")

    def __repr__(self):
        return f"<Expense {self.amount} on {self.date}>"
    
class CategoryBudget(db.Model):
    __tablename__ = "category_budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)

    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "category_id", "year", "month",
            name="uq_category_budget_month"
        ),
    )

class RecurringTransaction(db.Model):
    __tablename__ = "recurring_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    type = db.Column(db.String(10), nullable=False)  # "income" | "expense"

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    day_of_month = db.Column(db.Integer, nullable=False)  # e.g. 1, 5, 15

    is_active = db.Column(db.Boolean, nullable=True, default=True)

    category = db.relationship("Category")
    expenses = db.relationship(
        "Expense",
        back_populates="recurring",
        cascade="all, delete-orphan"
    )