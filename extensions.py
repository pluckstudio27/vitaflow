from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect
from werkzeug.security import generate_password_hash
from datetime import datetime
import certifi
import os

# SQLAlchemy (mantido para compatibilidade em partes do código)
db = SQLAlchemy()
migrate = Migrate()

# MongoDB (persistência oficial)
mongo_client: MongoClient | None = None
mongo_db = None

def ensure_collections_and_indexes(db, logger=None):
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
            'logs_auditoria',  # adicionada para evitar erros no primeiro uso
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
        db['logs_auditoria'].create_index([('timestamp', ASCENDING)], name='idx_audit_time')
        db['logs_auditoria'].create_index([('usuario_id', ASCENDING)], name='idx_audit_user')
    except Exception as e:
        if logger is not None:
            logger.error(f'[Mongo Init] Falha ao criar coleções/índices: {e}')
        else:
            print(f'[Mongo Init] Falha ao criar coleções/índices: {e}')

def _sanitize_mongo_uri(uri: str) -> str:
    """Mascara credenciais em uma URI Mongo para evitar exposição em logs."""
    try:
        if '://' in uri and '@' in uri:
            scheme, rest = uri.split('://', 1)
            creds, host_and_path = rest.split('@', 1)
            masked_creds = '***:***' if ':' in creds else '***'
            return f"{scheme}://{masked_creds}@{host_and_path}"
        return uri
    except Exception:
        return '<hidden>'

def init_mongo(app):
    """Inicializa cliente MongoDB usando configurações do app e semeia usuário admin padrão se necessário."""
    global mongo_client, mongo_db
    if mongo_client is None:
        mongo_uri = app.config.get('MONGO_URI')
        dbname = app.config.get('MONGO_DB')
        # Ler ajustes de tempo e TLS via ambiente
        timeout_select = int(os.environ.get('MONGO_TIMEOUT_SELECT_MS', '15000'))
        timeout_connect = int(os.environ.get('MONGO_TIMEOUT_CONNECT_MS', '12000'))
        timeout_socket = int(os.environ.get('MONGO_TIMEOUT_SOCKET_MS', '12000'))
        allow_invalid = os.environ.get('MONGO_TLS_ALLOW_INVALID', 'false').lower() == 'true'
        app.logger.info(f"[Mongo Init] Conectando em URI={_sanitize_mongo_uri(mongo_uri)} DB={dbname}")
        app.logger.info(f"[Mongo Init] Options: select={timeout_select}ms connect={timeout_connect}ms socket={timeout_socket}ms tlsAllowInvalid={allow_invalid}")
        try:
            client_kwargs = {
                'serverSelectionTimeoutMS': timeout_select,
                'connectTimeoutMS': timeout_connect,
                'socketTimeoutMS': timeout_socket,
            }
            if allow_invalid:
                client_kwargs['tlsAllowInvalidCertificates'] = True
            else:
                client_kwargs['tlsCAFile'] = certifi.where()

            mongo_client = MongoClient(
                mongo_uri,
                **client_kwargs,
            )
            # Testar conectividade rapidamente para evitar travar o startup
            mongo_client.admin.command('ping')
            mongo_db = mongo_client[dbname]

            # Garantir coleções e índices
            ensure_collections_and_indexes(mongo_db, logger=app.logger)
            
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
                    app.logger.info('[Mongo Seed] Usuário admin existente atualizado com senha padrão "admin".')
                else:
                    app.logger.info('[Mongo Seed] Usuário admin criado com senha padrão "admin".')
            except Exception as e:
                app.logger.error(f'[Mongo Seed] Falha ao semear/atualizar usuário admin: {e}')
        except (ServerSelectionTimeoutError, AutoReconnect, Exception) as e:
            app.logger.error(f"[Mongo Init] Conexão MongoDB indisponível: {type(e).__name__}: {e}")
            # Fallback: tentar iniciar banco em memória com mongomock para desenvolvimento/teste
            try:
                import mongomock
                app.logger.warning("[Mongo Init] Usando mongomock (banco em memória) como fallback de desenvolvimento.")
                mongo_client = mongomock.MongoClient()
                mongo_db = mongo_client[dbname]
                # Garantir coleções, índices e usuário admin padrão
                ensure_collections_and_indexes(mongo_db, logger=app.logger)
                try:
                    usuarios_col = mongo_db['usuarios']
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
                    usuarios_col.update_one(
                        {'username': 'admin'},
                        {'$set': {'username': 'admin', **admin_fields}},
                        upsert=True
                    )
                    app.logger.info('[Mongo Seed] (mongomock) Usuário admin disponível com senha padrão "admin".')
                except Exception as se:
                    app.logger.error(f'[Mongo Seed] (mongomock) Falha ao preparar usuário admin: {se}')
            except Exception as e2:
                app.logger.error(f"[Mongo Init] Fallback mongomock indisponível: {type(e2).__name__}: {e2}")
                mongo_client = None
                mongo_db = None
    return mongo_client, mongo_db
