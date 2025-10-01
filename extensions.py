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
    """Inicializa conexão com MongoDB se MONGO_URI estiver configurado.

    Lê MONGO_URI e MONGO_DB de app.config ou variáveis de ambiente.
    Configuração ausente é tratada de forma graciosa (sem erro).
    """
    global mongo_client, mongo_db

    uri = app.config.get('MONGO_URI') or os.environ.get('MONGO_URI')
    db_name = app.config.get('MONGO_DB') or os.environ.get('MONGO_DB')

    if not uri:
        app.logger.info('MongoDB não configurado: defina MONGO_URI para habilitar.')
        return

    if MongoClient is None:
        app.logger.error('pymongo não está instalado. Adicione "pymongo" ao requirements.txt')
        return

    try:
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()

        # Verifica conectividade
        mongo_client.admin.command('ping')
        app.logger.info(f"MongoDB conectado com sucesso (db='{mongo_db.name}')")
    except Exception as e:
        app.logger.error(f'Falha ao conectar ao MongoDB: {e}')
        # Mantém a aplicação rodando mesmo sem Mongo
        mongo_client = None
        mongo_db = None