import os
from flask import Flask
from config import config
from extensions import db, migrate, init_mongo, is_mongo_available
from blueprints.main import main_bp
from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.categorias_api import categorias_api_bp
from auth_mongo import init_login_manager

# Importar modelos SQLAlchemy (fallback)
from models.usuario import Usuario, LogAuditoria
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from models.categoria import CategoriaProduto
from models.produto import Produto
from models.usuario_categoria import UsuarioCategoria

# Importar modelos MongoDB (principal)
try:
    from models_mongo import (
        UsuarioMongo, LogAuditoriaMongo, CategoriaProdutoMongo, ConfiguracaoCategoriaMongo,
        ProdutoMongo, EstoqueProdutoMongo, LoteProdutoMongo, MovimentacaoProdutoMongo,
        CentralMongo, AlmoxarifadoMongo, SubAlmoxarifadoMongo, SetorMongo,
        init_mongodb, create_all_indexes
    )
    MONGODB_MODELS_AVAILABLE = True
except ImportError as e:
    print(f"Aviso: Modelos MongoDB não disponíveis: {e}")
    MONGODB_MODELS_AVAILABLE = False

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
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
    
    # Inicializar dados padrão após configuração
    with app.app_context():
        if app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available() and MONGODB_MODELS_AVAILABLE:
            # Usar MongoDB como principal
            app.logger.info("Inicializando dados padrão no MongoDB...")
            create_default_admin_mongo()
        else:
            # Usar SQLAlchemy como fallback
            app.logger.info("Inicializando dados padrão no SQLAlchemy...")
            db.create_all()
            create_default_admin_sql()
    
    return app


def create_default_admin_mongo():
    """Cria usuário admin padrão no MongoDB"""
    try:
        # Verifica se já existe um admin
        admin = UsuarioMongo.find_by_username('admin')
        if not admin:
            admin = UsuarioMongo(
                username='admin',
                email='admin@almox-sms.com',
                nome_completo='Administrador do Sistema',
                nivel_acesso='super_admin',
                ativo=True
            )
            admin.set_password('admin123')
            admin.save()
            print("Usuário admin criado no MongoDB (username: admin, password: admin123)")
        else:
            print("Usuário admin já existe no MongoDB")
    except Exception as e:
        print(f"Erro ao criar admin no MongoDB: {e}")


def create_default_admin_sql():
    """Cria usuário admin padrão no SQLAlchemy"""
    try:
        # Verifica se já existe um admin
        admin = Usuario.query.filter_by(username='admin').first()
        if not admin:
            admin = Usuario(
                username='admin',
                email='admin@almox-sms.com',
                ativo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado no SQLAlchemy (username: admin, password: admin123)")
        else:
            print("Usuário admin já existe no SQLAlchemy")
    except Exception as e:
        print(f"Erro ao criar admin no SQLAlchemy: {e}")
        db.session.rollback()

# Create app instance for Gunicorn
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        if app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available() and MONGODB_MODELS_AVAILABLE:
            print("Aplicação configurada para usar MongoDB como banco principal")
            # MongoDB já foi inicializado em init_mongo()
        else:
            print("Aplicação usando SQLAlchemy como banco principal")
            db.create_all()
    app.run(debug=True)