from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pymongo import MongoClient, ASCENDING
from werkzeug.security import generate_password_hash
from datetime import datetime

# SQLAlchemy (mantido para compatibilidade em partes do código)
db = SQLAlchemy()
migrate = Migrate()

# MongoDB (persistência oficial)
mongo_client: MongoClient | None = None
mongo_db = None

def ensure_collections_and_indexes(db):
    """Cria coleções essenciais e índices (idempotente)."""
    try:
        required = [
            'usuarios',
            'centrais',
            'almoxarifados',
            'sub_almoxarifados',
            'setores',
            'categorias',
            'produtos',
            'movimentacoes',
            'locais',
        ]
        existing = set(db.list_collection_names())
        for name in required:
            if name not in existing:
                db.create_collection(name)
        # Índices essenciais
        db['usuarios'].create_index([('username', ASCENDING)], unique=True, name='idx_unique_username')
        db['produtos'].create_index([('codigo', ASCENDING)], name='idx_prod_codigo')
        db['produtos'].create_index([('nome', ASCENDING)], name='idx_prod_nome')
        db['movimentacoes'].create_index([('data', ASCENDING)], name='idx_mov_data')
    except Exception as e:
        print(f'[Mongo Init] Falha ao criar coleções/índices: {e}')

def init_mongo(app):
    """Inicializa cliente MongoDB usando configurações do app e semeia usuário admin padrão se necessário."""
    global mongo_client, mongo_db
    if mongo_client is None:
        mongo_uri = app.config.get('MONGO_URI')
        dbname = app.config.get('MONGO_DB')
        mongo_client = MongoClient(mongo_uri)
        mongo_db = mongo_client[dbname]

        # Garantir coleções e índices
        ensure_collections_and_indexes(mongo_db)
        
        # Seed/Upsert de usuário admin padrão
        try:
            usuarios_col = mongo_db['usuarios']
            # Garantir índice (idempotente)
            usuarios_col.create_index([('username', ASCENDING)], unique=True, name='idx_unique_username')
            admin_fields = {
                'email': 'admin@local',
                'nome': 'Administrador',
                'password_hash': generate_password_hash('admin'),
                'ativo': True,
                'nivel_acesso': 'super_admin',
                'data_criacao': datetime.utcnow(),
                'ultimo_login': None,
                'central_id': None,
                'almoxarifado_id': None,
                'sub_almoxarifado_id': None,
                'setor_id': None,
            }
            result = usuarios_col.update_one(
                {'username': 'admin'},
                {'$set': {'username': 'admin', **admin_fields}},
                upsert=True
            )
            if result.matched_count:
                print('[Mongo Seed] Usuário admin existente atualizado com senha padrão "admin".')
            else:
                print('[Mongo Seed] Usuário admin criado com senha padrão "admin".')
        except Exception as e:
            print(f'[Mongo Seed] Falha ao semear/atualizar usuário admin: {e}')
    return mongo_client, mongo_db
