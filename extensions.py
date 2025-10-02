from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

# ------------------ MongoDB Integration ------------------
try:
    from pymongo import MongoClient
except Exception:
    # Permite rodar sem pymongo instalado (ex.: antes de instalar dependências)
    MongoClient = None

mongo_client = None
mongo_db = None

def init_mongo(app):
    """Inicializa conexão com MongoDB.

    Lê MONGO_URI e MONGO_DB de app.config.
    Se USE_MONGODB_PRIMARY for True, a conexão é obrigatória.
    """
    global mongo_client, mongo_db

    uri = app.config.get('MONGO_URI')
    db_name = app.config.get('MONGO_DB')
    use_primary = app.config.get('USE_MONGODB_PRIMARY', False)

    if not uri:
        if use_primary:
            app.logger.error('MongoDB configurado como principal mas MONGO_URI não definido!')
            raise ValueError('MONGO_URI é obrigatório quando USE_MONGODB_PRIMARY=True')
        else:
            app.logger.info('MongoDB não configurado: defina MONGO_URI para habilitar.')
            return

    if MongoClient is None:
        error_msg = 'pymongo não está instalado. Execute: pip install pymongo'
        app.logger.error(error_msg)
        if use_primary:
            raise ImportError(error_msg)
        return

    try:
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()

        # Verifica conectividade
        mongo_client.admin.command('ping')
        app.logger.info(f"MongoDB conectado com sucesso (db='{mongo_db.name}', primary={use_primary})")
        
        # Se MongoDB é o principal, inicializa os índices
        if use_primary:
            from models_mongo import init_mongodb
            init_mongodb()
            app.logger.info("Índices MongoDB inicializados")
            
    except Exception as e:
        error_msg = f'Falha ao conectar ao MongoDB: {e}'
        app.logger.error(error_msg)
        if use_primary:
            raise ConnectionError(error_msg)
        # Mantém a aplicação rodando se MongoDB não é principal
        mongo_client = None
        mongo_db = None


def get_mongo_db():
    """Retorna a instância do banco MongoDB"""
    return mongo_db


def is_mongo_available():
    """Verifica se MongoDB está disponível"""
    return mongo_client is not None and mongo_db is not None