from datetime import datetime
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from models import db, User
from config import Config

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Iniciá sesión para continuar.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {'now': datetime.now()}

    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.products import products_bp
    from blueprints.production import production_bp
    from blueprints.distribution import distribution_bp
    from blueprints.sales import sales_bp
    from blueprints.breakage import breakage_bp
    from blueprints.reports import reports_bp
    from blueprints.dispensers import dispensers_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp, url_prefix='/productos')
    app.register_blueprint(production_bp, url_prefix='/produccion')
    app.register_blueprint(distribution_bp, url_prefix='/distribucion')
    app.register_blueprint(sales_bp, url_prefix='/ventas')
    app.register_blueprint(breakage_bp, url_prefix='/roturas')
    app.register_blueprint(reports_bp, url_prefix='/reportes')
    app.register_blueprint(dispensers_bp, url_prefix='/dispensers')

    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
