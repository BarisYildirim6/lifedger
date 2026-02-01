from flask import Flask
from .config import Config
from .extensions import db, migrate, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .auth.routes import auth_bp
    from .finance.routes import finance_bp
    #from .reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(finance_bp)
    #app.register_blueprint(reports_bp)

    return app
