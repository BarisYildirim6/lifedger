from app import create_app
from datetime import date
from app.finance.services import materialize_recurring_expenses

def run():
    app = create_app()

    with app.app_context():
        materialize_recurring_expenses(date.today())

if __name__ == "__main__":
    run()