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

def validate_and_sanitize_mongo_uri(uri):
    """Valida e sanitiza a URI do MongoDB"""
    if not uri:
        return None
    
    # Remove espaços em branco e caracteres de controle
    uri = uri.strip()
    invalid_chars = ['\n', '\r', '\t']
    for char in invalid_chars:
        if char in uri:
            uri = uri.replace(char, '')
    
    # Verifica se a URI começa com mongodb:// ou mongodb+srv://
    if not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
        raise ValueError('URI do MongoDB deve começar com mongodb:// ou mongodb+srv://')
    
    # Corrige problemas comuns nas opções da URI
    if '?' in uri:
        base_uri, options = uri.split('?', 1)
        if options:
            # Remove espaços das opções e corrige problemas
            options = options.replace(' ', '')  # Remove todos os espaços das opções
            
            # Corrige opções malformadas
            option_pairs = []
            for pair in options.split('&'):
                if not pair:  # Remove opções vazias
                    continue
                if '=' not in pair:
                    # Opções conhecidas que podem não ter valor
                    known_boolean_options = ['retryWrites', 'ssl', 'tls', 'authMechanism']
                    known_string_options = ['authSource', 'replicaSet', 'readPreference']
                    
                    if pair in known_boolean_options:
                        pair = f'{pair}=true'
                    elif pair in known_string_options:
                        # Para authSource, usa um valor padrão comum
                        if pair == 'authSource':
                            pair = f'{pair}=admin'
                        else:
                            # Para outras opções string, adiciona valor vazio (será removido depois)
                            continue
                    else:
                        # Para opções desconhecidas, tenta adicionar =true
                        pair = f'{pair}=true'
                
                # Remove opções com valores vazios
                if '=' in pair and pair.split('=', 1)[1] == '':
                    continue
                    
                option_pairs.append(pair)
            
            # Reconstrói a URI com opções corrigidas
            if option_pairs:
                uri = f'{base_uri}?{"&".join(option_pairs)}'
            else:
                uri = base_uri
    
    # Verificação final: não deve haver espaços na URI final
    if ' ' in uri:
        uri = uri.replace(' ', '')
    
    return uri

def init_mongo(app):
    """Inicializa conexão com MongoDB.

    Lê MONGO_URI e MONGO_DB de app.config.
    Se USE_MONGODB_PRIMARY for True, a conexão é obrigatória.
    """
    global mongo_client, mongo_db

    uri = app.config.get('MONGO_URI')
    db_name = app.config.get('MONGO_DB')
    use_primary = app.config.get('USE_MONGODB_PRIMARY', False)

    app.logger.info(f"Inicializando MongoDB (primary={use_primary})...")

    if not uri:
        if use_primary:
            app.logger.error('MongoDB configurado como principal mas MONGO_URI não definido!')
            raise ValueError('MONGO_URI é obrigatório quando USE_MONGODB_PRIMARY=True')
        else:
            app.logger.info('MongoDB não configurado: defina MONGO_URI para habilitar.')
            return
    
    # Valida e sanitiza a URI
    try:
        uri = validate_and_sanitize_mongo_uri(uri)
        app.logger.info('URI do MongoDB validada com sucesso')
    except ValueError as e:
        error_msg = f'URI do MongoDB inválida: {e}'
        app.logger.error(error_msg)
        if use_primary:
            raise ValueError(error_msg)
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
        # Tratamento específico para diferentes tipos de erro
        if 'InvalidURI' in str(type(e)) or 'MongoDB URI options are key=value pairs' in str(e):
            error_msg = f'URI do MongoDB malformada: {e}. Verifique se as opções estão no formato key=value separadas por &'
        elif 'ServerSelectionTimeoutError' in str(type(e)):
            error_msg = f'Timeout ao conectar ao MongoDB: {e}. Verifique se o servidor está acessível'
        elif 'Authentication' in str(e):
            error_msg = f'Erro de autenticação MongoDB: {e}. Verifique usuário e senha'
        else:
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