from flask import Flask
from config import Config
from extensions import db, migrate, init_mongo
from blueprints.main import main_bp
from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.categorias_api import categorias_api_bp
from auth import init_login_manager

# Importar modelos para garantir que as tabelas sejam criadas
from models.usuario import Usuario, LogAuditoria
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from models.categoria import CategoriaProduto
from models.produto import Produto
from models.usuario_categoria import UsuarioCategoria

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    init_login_manager(app)
    init_mongo(app)
    
    # Registrar blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(categorias_api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    
    return app

# Create app instance for Gunicorn
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)