from flask import Flask, redirect, url_for
from config import Config
from extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register Member 4 Blueprints (Discounts, Payments, Invoice Tracking, Revenue Reports)
    from blueprints.discounts.routes import discounts_bp
    from blueprints.payments.routes import payments_bp
    from blueprints.invoices.routes import invoices_bp
    from blueprints.reports.routes import reports_bp

    app.register_blueprint(discounts_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(reports_bp)

    @app.route('/')
    def index():
        return redirect(url_for('discounts.list_discounts'))

    # Create tables automatically if needed (for initial dev/test)
    with app.app_context():
        import models  # Ensure all models are registered with SQLAlchemy
        # db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
