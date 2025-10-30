from flask import Flask
import os
from config import Config
from extensions import db, migrate, init_mongo
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from auth import init_login_manager


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='assets', static_url_path='/static')
    app.config.from_object(config_class)

    # Inicializar extensões
    # SQLAlchemy é mantido apenas para compatibilidade, não criar tabelas
    db.init_app(app)
    migrate.init_app(app, db)

    # MongoDB (persistência oficial)
    init_mongo(app)

    # Login manager
    init_login_manager(app)

    # Registrar blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app

# Expor o app para gunicorn
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))