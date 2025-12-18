from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import time

# SQLAlchemy (mantido para compatibilidade em partes do código)
db = SQLAlchemy()
migrate = Migrate()

# MongoDB (persistência oficial)
mongo_client: MongoClient | None = None
mongo_db = None

class SimpleTTLCache:
    def __init__(self, max_size: int = 1000):
        self.store = {}
        self.order = []
        self.max_size = max_size

    def get(self, key):
        val = self.store.get(key)
        if not val:
            return None
        data, exp = val
        if exp is not None and exp < time.time():
            try:
                del self.store[key]
            except Exception:
                pass
            return None
        return data

    def set(self, key, data, ttl: int = 30):
        exp = (time.time() + ttl) if ttl and ttl > 0 else None
        self.store[key] = (data, exp)
        self.order.append(key)
        if len(self.order) > self.max_size:
            old = self.order.pop(0)
            try:
                del self.store[old]
            except Exception:
                pass

    def clear_prefix(self, prefix: str):
        try:
            keys = [k for k in list(self.store.keys()) if str(k).startswith(prefix)]
            for k in keys:
                try:
                    del self.store[k]
                except Exception:
                    pass
        except Exception:
            pass

response_cache = SimpleTTLCache(2000)

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
            'listas_compras',  # lista de compras por usuário
        ]
        existing = set(db.list_collection_names())
        for name in required:
            if name not in existing:
                db.create_collection(name)
        # Índices essenciais
        db['usuarios'].create_index([('username', ASCENDING)], unique=True, name='idx_unique_username')
        db['produtos'].create_index([('codigo', ASCENDING)], name='idx_prod_codigo')
        db['produtos'].create_index([('nome', ASCENDING)], name='idx_prod_nome')
        try:
            db['movimentacoes'].create_index([('data_movimentacao', ASCENDING)], name='idx_mov_data_movimentacao')
        except Exception:
            pass
        try:
            db['movimentacoes'].create_index([('tipo', ASCENDING)], name='idx_mov_tipo')
            db['movimentacoes'].create_index([('produto_id', ASCENDING)], name='idx_mov_produto')
            db['movimentacoes'].create_index([('created_at', DESCENDING)], name='idx_mov_created_at')
            db['movimentacoes'].create_index([('produto_id', ASCENDING), ('data_movimentacao', DESCENDING)], name='idx_mov_prod_data')
        except Exception:
            pass
        try:
            db['estoques'].create_index([('produto_id', ASCENDING)], name='idx_est_produto')
            db['estoques'].create_index([('local_tipo', ASCENDING), ('local_id', ASCENDING)], name='idx_est_local')
            db['estoques'].create_index([('updated_at', DESCENDING)], name='idx_est_updated')
        except Exception:
            pass
        try:
            db['logs_auditoria'].create_index([('timestamp', ASCENDING)], name='idx_audit_time')
            db['logs_auditoria'].create_index([('usuario_id', ASCENDING)], name='idx_audit_user')
        except Exception:
            pass
        try:
            db['listas_compras'].create_index([('usuario_id', ASCENDING)], name='idx_lista_usuario')
            db['listas_compras'].create_index([('created_at', ASCENDING)], name='idx_lista_created')
        except Exception:
            pass
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
                # Preferir bundle CA do certifi, mas não travar se ausente
                try:
                    import certifi
                    client_kwargs['tlsCAFile'] = certifi.where()
                except Exception:
                    # Fallback: confiar no bundle do sistema sem definir tlsCAFile
                    pass

            mongo_client = MongoClient(
                mongo_uri,
                **client_kwargs,
            )
            # Testar conectividade rapidamente para evitar travar o startup
            mongo_client.admin.command('ping')
            mongo_db = mongo_client[dbname]

            # Em ambiente de testes, limpar coleções para isolamento dos testes
            try:
                if app.config.get('TESTING'):
                    for name in ['usuarios','centrais','almoxarifados','sub_almoxarifados','setores','categorias','produtos','movimentacoes','locais','logs_auditoria','listas_compras','estoques','lotes','compras']:
                        try:
                            mongo_db.drop_collection(name)
                        except Exception:
                            pass
            except Exception:
                pass

            # Garantir coleções e índices
            ensure_collections_and_indexes(mongo_db, logger=app.logger)
            
            # Seed seguro do usuário admin e usuários de teste
            try:
                usuarios_col = mongo_db['usuarios']
                usuarios_col.create_index([('username', ASCENDING)], unique=True, name='idx_unique_username')
                is_dev_or_test = bool(app.config.get('DEBUG')) or bool(app.config.get('TESTING'))
                initial_pwd = os.environ.get('INITIAL_ADMIN_PASSWORD') or ('admin' if is_dev_or_test else None)
                existing = usuarios_col.find_one({'username': 'admin'})
                if existing is None:
                    if initial_pwd is not None:
                        usuarios_col.insert_one({
                            'username': 'admin',
                            'email': 'admin@local',
                            'nome': 'Administrador',
                            'password_hash': generate_password_hash(initial_pwd),
                            'ativo': True,
                            'nivel_acesso': 'super_admin',
                            'data_criacao': datetime.utcnow(),
                            'ultimo_login': None,
                            'central_id': None,
                            'almoxarifado_id': None,
                            'sub_almoxarifado_id': None,
                            'setor_id': None,
                        })
                        app.logger.info('[Mongo Seed] Usuário admin criado.')
                    else:
                        app.logger.info('[Mongo Seed] Usuário admin NÃO criado (sem INITIAL_ADMIN_PASSWORD e ambiente de produção).')
                else:
                    update_fields = {
                        'email': existing.get('email') or 'admin@local',
                        'nome': existing.get('nome') or existing.get('nome_completo') or 'Administrador',
                        'ativo': True,
                        'nivel_acesso': 'super_admin',
                    }
                    if initial_pwd is not None:
                        update_fields['password_hash'] = generate_password_hash(initial_pwd)
                        app.logger.info('[Mongo Seed] Usuário admin existente atualizado.')
                    usuarios_col.update_one({'_id': existing['_id']}, {'$set': update_fields})

                if is_dev_or_test or (os.environ.get('SEED_TEST_USERS', 'true').lower() == 'true'):
                    test_user = usuarios_col.find_one({'username': 'test_operator'})
                    test_pwd = os.environ.get('TEST_OPERATOR_PASSWORD') or 'password123'
                    if test_user is None:
                        usuarios_col.insert_one({
                            'username': 'test_operator',
                            'email': 'test@local',
                            'nome': 'Test Operator',
                            'password_hash': generate_password_hash(test_pwd),
                            'ativo': True,
                            'nivel_acesso': 'admin_central',
                            'data_criacao': datetime.utcnow(),
                            'ultimo_login': None,
                            'central_id': None,
                            'almoxarifado_id': None,
                            'sub_almoxarifado_id': None,
                            'setor_id': None,
                        })
                        app.logger.info('[Mongo Seed] Usuário de testes \"test_operator\" criado.')
                    else:
                        usuarios_col.update_one({'_id': test_user['_id']}, {'$set': {
                            'ativo': True,
                            'nivel_acesso': 'admin_central',
                        }})
                    test_user2 = usuarios_col.find_one({'username': 'testuser'})
                    test_pwd2 = os.environ.get('TEST_USER_PASSWORD') or 'testpassword'
                    if test_user2 is None:
                        usuarios_col.insert_one({
                            'username': 'testuser',
                            'email': 'testuser@local',
                            'nome': 'Test User',
                            'password_hash': generate_password_hash(test_pwd2),
                            'ativo': True,
                            'nivel_acesso': 'admin_central',
                            'data_criacao': datetime.utcnow(),
                            'ultimo_login': None,
                            'central_id': None,
                            'almoxarifado_id': None,
                            'sub_almoxarifado_id': None,
                            'setor_id': None,
                        })
                        app.logger.info('[Mongo Seed] Usuário de testes \"testuser\" criado.')
                    else:
                        usuarios_col.update_one({'_id': test_user2['_id']}, {'$set': {
                            'ativo': True,
                            'nivel_acesso': 'admin_central',
                        }})
            except Exception as e:
                app.logger.error(f'[Mongo Seed] Falha ao semear usuários: {e}')
            try:
                now = datetime.utcnow()
                db = mongo_db
                cent = db['centrais']
                alm = db['almoxarifados']
                sub = db['sub_almoxarifados']
                setr = db['setores']
                cat = db['categorias']
                prod = db['produtos']
                est = db['estoques']
                if cent.count_documents({}) == 0:
                    cent.insert_one({'id': 1, 'nome': 'Central Demo', 'created_at': now})
                if alm.count_documents({}) == 0:
                    alm.insert_one({'id': 1, 'nome': 'Almox Demo', 'central_id': 1, 'created_at': now})
                if sub.count_documents({}) == 0:
                    sub.insert_one({'id': 1, 'nome': 'Sub Demo', 'almoxarifado_id': 1, 'created_at': now})
                if setr.count_documents({}) == 0:
                    setr.insert_many([
                        {'id': 1, 'nome': 'Setor Demo A', 'sub_almoxarifado_id': 1, 'almoxarifado_id': 1, 'created_at': now, 'ativo': True},
                        {'id': 2, 'nome': 'Setor Demo B', 'sub_almoxarifado_id': 1, 'almoxarifado_id': 1, 'created_at': now, 'ativo': True}
                    ])
                if cat.count_documents({}) == 0:
                    cat.insert_one({'id': 1, 'nome': 'Geral', 'codigo': 'GER', 'created_at': now})
                if prod.count_documents({}) == 0:
                    prod.insert_one({'id': 1, 'nome': 'Produto Demo', 'codigo': 'GER-0001', 'unidade_medida': 'un', 'central_id': 1, 'ativo': True, 'created_at': now})
                else:
                    if prod.find_one({'id': 1}) is None:
                        prod.insert_one({'id': 1, 'nome': 'Produto Demo', 'codigo': 'GER-0001', 'unidade_medida': 'un', 'central_id': 1, 'ativo': True, 'created_at': now})
                # Garantir estoque inicial para pelo menos um produto existente
                pfirst = prod.find_one({}, sort=[('_id', 1)]) or {}
                pid_out = pfirst.get('id') if pfirst.get('id') is not None else (str(pfirst.get('_id')) if pfirst.get('_id') is not None else 1)
                if est.count_documents({'local_tipo': 'setor', 'local_id': 1, 'produto_id': pid_out}) == 0:
                    est.insert_one({'produto_id': pid_out, 'local_tipo': 'setor', 'local_id': 1, 'setor_id': 1, 'nome_local': 'Setor Demo A', 'quantidade': 500.0, 'quantidade_disponivel': 500.0, 'created_at': now, 'updated_at': now})
                usuarios_col = db['usuarios']
                usuarios_col.update_one({'username': 'test_operator'}, {'$set': {'central_id': 1, 'almoxarifado_id': 1, 'sub_almoxarifado_id': 1}}, upsert=False)
                usuarios_col.update_one({'username': 'testuser'}, {'$set': {'central_id': 1, 'almoxarifado_id': 1, 'sub_almoxarifado_id': 1, 'setor_id': 1}}, upsert=False)
            except Exception:
                pass
        except (ServerSelectionTimeoutError, AutoReconnect, Exception) as e:
            # Fallback controlado para ambiente de desenvolvimento/teste usando mongomock
            try:
                allow_mock = bool(app.config.get('ALLOW_MOCK_DB')) or (os.environ.get('USE_MONGOMOCK', 'false').lower() == 'true')
            except Exception:
                allow_mock = False
            if allow_mock:
                app.logger.warning(f"[Mongo Init] Usando mongomock (fallback) por indisponibilidade: {type(e).__name__}: {e}")
                try:
                    import mongomock
                    mongo_client = mongomock.MongoClient()
                    mongo_db = mongo_client[dbname]
                    ensure_collections_and_indexes(mongo_db, logger=app.logger)
                    try:
                        usuarios_col = mongo_db['usuarios']
                        usuarios_col.create_index([('username', ASCENDING)], unique=True, name='idx_unique_username')
                        initial_pwd = os.environ.get('INITIAL_ADMIN_PASSWORD') or 'admin'
                        if usuarios_col.find_one({'username': 'admin'}) is None:
                            usuarios_col.insert_one({
                                'username': 'admin',
                                'email': 'admin@local',
                                'nome': 'Administrador',
                                'password_hash': generate_password_hash(initial_pwd),
                                'ativo': True,
                                'nivel_acesso': 'super_admin',
                                'data_criacao': datetime.utcnow(),
                                'ultimo_login': None,
                                'central_id': None,
                                'almoxarifado_id': None,
                                'sub_almoxarifado_id': None,
                                'setor_id': None,
                            })
                        if usuarios_col.find_one({'username': 'test_operator'}) is None:
                            usuarios_col.insert_one({
                                'username': 'test_operator',
                                'email': 'test@local',
                                'nome': 'Test Operator',
                                'password_hash': generate_password_hash(os.environ.get('TEST_OPERATOR_PASSWORD') or 'password123'),
                                'ativo': True,
                                'nivel_acesso': 'admin_central',
                                'data_criacao': datetime.utcnow(),
                                'ultimo_login': None,
                                'central_id': None,
                                'almoxarifado_id': None,
                                'sub_almoxarifado_id': None,
                                'setor_id': None,
                            })
                        if usuarios_col.find_one({'username': 'testuser'}) is None:
                            usuarios_col.insert_one({
                                'username': 'testuser',
                                'email': 'testuser@local',
                                'nome': 'Test User',
                                'password_hash': generate_password_hash(os.environ.get('TEST_USER_PASSWORD') or 'testpassword'),
                                'ativo': True,
                                'nivel_acesso': 'admin_central',
                                'data_criacao': datetime.utcnow(),
                                'ultimo_login': None,
                                'central_id': None,
                                'almoxarifado_id': None,
                                'sub_almoxarifado_id': None,
                                'setor_id': None,
                            })
                        now = datetime.utcnow()
                        db = mongo_db
                        cent = db['centrais']
                        alm = db['almoxarifados']
                        sub = db['sub_almoxarifados']
                        setr = db['setores']
                        cat = db['categorias']
                        prod = db['produtos']
                        est = db['estoques']
                        if cent.count_documents({}) == 0:
                            cent.insert_one({'id': 1, 'nome': 'Central Demo', 'created_at': now})
                        if alm.count_documents({}) == 0:
                            alm.insert_one({'id': 1, 'nome': 'Almox Demo', 'central_id': 1, 'created_at': now})
                        if sub.count_documents({}) == 0:
                            sub.insert_one({'id': 1, 'nome': 'Sub Demo', 'almoxarifado_id': 1, 'created_at': now})
                        if setr.count_documents({}) == 0:
                            setr.insert_many([
                                {'id': 1, 'nome': 'Setor Demo A', 'sub_almoxarifado_id': 1, 'almoxarifado_id': 1, 'created_at': now, 'ativo': True},
                                {'id': 2, 'nome': 'Setor Demo B', 'sub_almoxarifado_id': 1, 'almoxarifado_id': 1, 'created_at': now, 'ativo': True}
                            ])
                        if cat.count_documents({}) == 0:
                            cat.insert_one({'id': 1, 'nome': 'Geral', 'codigo': 'GER', 'created_at': now})
                        if prod.count_documents({}) == 0:
                            prod.insert_one({'id': 1, 'nome': 'Produto Demo', 'codigo': 'GER-0001', 'unidade_medida': 'un', 'central_id': 1, 'ativo': True, 'created_at': now})
                        pfirst = prod.find_one({}, sort=[('_id', 1)]) or {}
                        pid_out = pfirst.get('id') if pfirst.get('id') is not None else (str(pfirst.get('_id')) if pfirst.get('_id') is not None else 1)
                        if est.count_documents({'local_tipo': 'setor', 'local_id': 1, 'produto_id': pid_out}) == 0:
                            est.insert_one({'produto_id': pid_out, 'local_tipo': 'setor', 'local_id': 1, 'setor_id': 1, 'nome_local': 'Setor Demo A', 'quantidade': 500.0, 'quantidade_disponivel': 500.0, 'created_at': now, 'updated_at': now})
                        usuarios_col.update_one({'username': 'test_operator'}, {'$set': {'central_id': 1, 'almoxarifado_id': 1, 'sub_almoxarifado_id': 1}}, upsert=False)
                        usuarios_col.update_one({'username': 'testuser'}, {'$set': {'central_id': 1, 'almoxarifado_id': 1, 'sub_almoxarifado_id': 1, 'setor_id': 1}}, upsert=False)
                    except Exception:
                        pass
                except Exception as e2:
                    app.logger.error(f"[Mongo Init] Fallback mongomock falhou: {type(e2).__name__}: {e2}")
                    mongo_client = None
                    mongo_db = None
                    raise RuntimeError(f"MongoDB indisponível e fallback falhou: {type(e).__name__}: {e} / {type(e2).__name__}: {e2}")
            else:
                # Não usar mongomock em produção: sempre exigir MongoDB real
                app.logger.error(f"[Mongo Init] Conexão MongoDB indisponível: {type(e).__name__}: {e}")
                mongo_client = None
                mongo_db = None
                raise RuntimeError(f"MongoDB indisponível: {type(e).__name__}: {e}")
    return mongo_client, mongo_db
