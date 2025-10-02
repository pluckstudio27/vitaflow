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
    """Valida e sanitiza uma URI do MongoDB.
    
    Args:
        uri (str): URI do MongoDB para validar
        
    Returns:
        str: URI sanitizada e válida
        
    Raises:
        ValueError: Se a URI for inválida e não puder ser corrigida
    """
    if not uri:
        raise ValueError('URI do MongoDB não pode estar vazia')
    
    # Converte para string se não for e remove espaços das extremidades
    uri = str(uri).strip()
    
    # Remove caracteres de controle e invisíveis
    import re
    # Remove caracteres de controle ASCII (0-31) exceto tab, newline, carriage return
    uri = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', uri)
    
    # Remove quebras de linha e tabs
    uri = uri.replace('\n', '').replace('\r', '').replace('\t', '')
    
    # Remove espaços extras (múltiplos espaços se tornam um)
    uri = re.sub(r'\s+', ' ', uri)
    
    # Decodifica URL encoding se presente
    try:
        import urllib.parse
        # Tenta decodificar, mas só se parecer estar codificado
        if '%' in uri:
            decoded = urllib.parse.unquote(uri)
            # Só usa a versão decodificada se ainda for uma URI válida
            if decoded.startswith(('mongodb://', 'mongodb+srv://')):
                uri = decoded
    except Exception:
        pass  # Se falhar na decodificação, continua com a URI original
    
    # Verifica se tem prefixo válido
    if not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
        raise ValueError('URI deve começar com mongodb:// ou mongodb+srv://')
    
    # Se não tem opções, remove espaços finais e retorna
    if '?' not in uri:
        return uri.replace(' ', '')
    
    # Separa base da URI das opções
    try:
        base_uri, options_str = uri.split('?', 1)
        
        # Remove todos os espaços das opções
        options_str = re.sub(r'\s', '', options_str)
        
        if not options_str:
            return base_uri
        
        # Processa as opções
        option_pairs = []
        for option in options_str.split('&'):
            if not option:
                continue
                
            pair = option.strip()
            if not pair:
                continue
            
            # Se não tem '=', tenta corrigir baseado em opções conhecidas
            if '=' not in pair:
                # Lista expandida de opções conhecidas
                known_boolean_options = [
                    'retryWrites', 'ssl', 'tls', 'directConnection', 
                    'journal', 'fsync', 'safe', 'slaveOk', 'uuidRepresentation'
                ]
                known_string_options = [
                    'authSource', 'authMechanism', 'readPreference',
                    'readConcernLevel', 'compressors', 'zlibCompressionLevel',
                    'w', 'wtimeoutMS', 'maxPoolSize', 'minPoolSize'
                ]
                
                if pair in known_boolean_options:
                    pair = f'{pair}=true'
                elif pair in known_string_options:
                    if pair == 'authSource':
                        pair = f'{pair}=admin'
                    elif pair == 'readPreference':
                        pair = f'{pair}=primary'
                    elif pair == 'w':
                        pair = f'{pair}=majority'
                    elif pair == 'authMechanism':
                        pair = f'{pair}=SCRAM-SHA-1'
                    else:
                        # Para outras opções string, pula (será removido)
                        continue
                else:
                    # Para opções completamente desconhecidas, tenta adicionar =true
                    pair = f'{pair}=true'
            
            # Verifica se o par tem formato válido key=value
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove opções com chaves ou valores vazios
                if not key or value == '':
                    continue
                
                # Valida caracteres especiais na chave
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', key):
                    continue  # Pula chaves com caracteres inválidos
                
                # Reconstrói o par limpo
                pair = f'{key}={value}'
            
            option_pairs.append(pair)
        
        # Remove duplicatas mantendo a última ocorrência
        seen_keys = {}
        final_pairs = []
        for pair in option_pairs:
            if '=' in pair:
                key = pair.split('=', 1)[0]
                seen_keys[key] = pair
        final_pairs = list(seen_keys.values())
        
        # Reconstrói a URI com opções corrigidas
        if final_pairs:
            uri = f'{base_uri}?{"&".join(final_pairs)}'
        else:
            uri = base_uri
            
    except Exception as e:
        # Se houver erro no processamento das opções, usa apenas a base
        if '?' in uri:
            uri = uri.split('?', 1)[0]
    
    # Limpeza final: remove todos os espaços
    uri = uri.replace(' ', '')
    
    # Validação final básica
    if not uri or len(uri) < 10:
        raise ValueError('URI do MongoDB muito curta ou inválida')
    
    # Validação adicional: verifica se a estrutura básica está correta
    if not re.match(r'^mongodb(\+srv)?://[^/]+(/[^?]*)?(\?.*)?$', uri):
        raise ValueError('Estrutura da URI do MongoDB inválida')
    
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
        # Logs extremamente detalhados para debug no Render
        app.logger.info(f'=== DEBUG RENDER: Iniciando validação da URI ===')
        app.logger.info(f'URI original completa: {repr(uri)}')
        app.logger.info(f'URI original (primeiros 100 chars): {uri[:100]}')
        app.logger.info(f'Tipo da URI: {type(uri)}')
        app.logger.info(f'Tamanho da URI: {len(uri)} caracteres')
        
        # Verifica caracteres especiais
        special_chars = [c for c in uri if ord(c) < 32 or ord(c) > 126]
        if special_chars:
            app.logger.warning(f'Caracteres especiais encontrados: {[hex(ord(c)) for c in special_chars]}')
        
        uri_original = uri
        uri = validate_and_sanitize_mongo_uri(uri)
        
        if uri != uri_original:
            app.logger.info(f'URI foi corrigida!')
            app.logger.info(f'URI corrigida completa: {repr(uri)}')
            app.logger.info(f'URI corrigida (primeiros 100 chars): {uri[:100]}')
        else:
            app.logger.info('URI não precisou de correção')
        
        app.logger.info(f'=== DEBUG RENDER: Validação concluída ===')
        
    except ValueError as e:
        error_msg = f'URI do MongoDB inválida: {e}'
        app.logger.error(f'=== DEBUG RENDER: Erro de validação ===')
        app.logger.error(f'Erro: {error_msg}')
        app.logger.error(f'URI que causou erro: {repr(uri)}')
        if use_primary:
            raise ValueError(error_msg)
        return
    except Exception as e:
        error_msg = f'Erro inesperado na validação da URI: {e}'
        app.logger.error(f'=== DEBUG RENDER: Erro inesperado ===')
        app.logger.error(f'Erro: {error_msg}')
        app.logger.error(f'URI que causou erro: {repr(uri)}')
        app.logger.error(f'Tipo do erro: {type(e)}')
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
        app.logger.info(f'=== DEBUG RENDER: Tentando conectar ao MongoDB ===')
        app.logger.info(f'URI final para conexão: {repr(uri)}')
        app.logger.info(f'URI final (primeiros 100 chars): {uri[:100]}')
        app.logger.info(f'Tentando conectar ao MongoDB com URI processada...')
        
        # Configurações SSL específicas para Render
        ssl_config = {}
        if os.getenv('RENDER'):
            app.logger.info('=== RENDER DETECTADO: Aplicando configurações TLS específicas ===')
            ssl_config = {
                'tls': True,
                'tlsAllowInvalidCertificates': True,
                'tlsAllowInvalidHostnames': True
            }
            app.logger.info(f'Configurações TLS aplicadas: {ssl_config}')
        
        mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000, **ssl_config)
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
        # Tratamento específico para erros SSL - tenta fallbacks progressivos
        if 'SSL' in str(e) or 'TLS' in str(e) or 'ssl' in str(e).lower() or 'handshake' in str(e).lower():
            app.logger.error(f'=== ERRO SSL DETECTADO: {e} ===')
            app.logger.info('Tentando fallbacks SSL progressivos...')
            
            # Fallback 1: Tentar sem SSL
            try:
                app.logger.info('Fallback 1: Tentando conexão sem SSL...')
                fallback_config = {'ssl': False, 'tls': False}
                mongo_client = MongoClient(uri, serverSelectionTimeoutMS=10000, **fallback_config)
                mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()
                mongo_client.admin.command('ping')
                app.logger.warning("MongoDB conectado com fallback SSL desabilitado")
                
                if use_primary:
                    from models_mongo import init_mongodb
                    init_mongodb()
                    app.logger.info("Índices MongoDB inicializados")
                return
            except Exception as e1:
                app.logger.warning(f'Fallback 1 falhou: {e1}')
            
            # Fallback 2: Tentar com configurações TLS mais permissivas
            try:
                app.logger.info('Fallback 2: Tentando com TLS mais permissivo...')
                fallback_config = {
                    'tls': True,
                    'tlsAllowInvalidCertificates': True,
                    'tlsAllowInvalidHostnames': True,
                    'tlsDisableOCSPEndpointCheck': True
                }
                mongo_client = MongoClient(uri, serverSelectionTimeoutMS=15000, **fallback_config)
                mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()
                mongo_client.admin.command('ping')
                app.logger.warning("MongoDB conectado com fallback TLS permissivo")
                
                if use_primary:
                    from models_mongo import init_mongodb
                    init_mongodb()
                    app.logger.info("Índices MongoDB inicializados")
                return
            except Exception as e2:
                app.logger.warning(f'Fallback 2 falhou: {e2}')
            
            # Fallback 3: Tentar com configurações mínimas
            try:
                app.logger.info('Fallback 3: Tentando com configurações mínimas...')
                fallback_config = {
                    'tls': True
                }
                mongo_client = MongoClient(uri, serverSelectionTimeoutMS=20000, **fallback_config)
                mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()
                mongo_client.admin.command('ping')
                app.logger.warning("MongoDB conectado com fallback TLS mínimo")
                
                if use_primary:
                    from models_mongo import init_mongodb
                    init_mongodb()
                    app.logger.info("Índices MongoDB inicializados")
                return
            except Exception as e3:
                app.logger.warning(f'Fallback 3 falhou: {e3}')
            
            # Fallback 4: Tentar apenas com a URI (sem configurações extras)
            try:
                app.logger.info('Fallback 4: Tentando apenas com URI padrão...')
                mongo_client = MongoClient(uri, serverSelectionTimeoutMS=30000)
                mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()
                mongo_client.admin.command('ping')
                app.logger.warning("MongoDB conectado com URI padrão")
                
                if use_primary:
                    from models_mongo import init_mongodb
                    init_mongodb()
                    app.logger.info("Índices MongoDB inicializados")
                return
            except Exception as e4:
                app.logger.warning(f'Fallback 4 falhou: {e4}')
            
            # Se todos os fallbacks SSL falharam, continua para outros tratamentos
            app.logger.error('Todos os fallbacks TLS falharam, tentando outras correções...')
        
        # Tratamento específico para InvalidURI - tenta uma última correção
        if 'InvalidURI' in str(type(e)) or 'MongoDB URI options are key=value pairs' in str(e):
            app.logger.error(f'=== DEBUG RENDER: Erro InvalidURI detectado ===')
            app.logger.error(f'Erro InvalidURI: {e}')
            app.logger.error(f'Tipo do erro: {type(e)}')
            app.logger.error(f'URI que causou o erro: {repr(uri)}')
            app.logger.warning(f'Tentando correção de emergência...')
            
            # Tenta uma correção de emergência removendo todas as opções
            try:
                if '?' in uri:
                    base_uri = uri.split('?', 1)[0]
                    app.logger.info(f'URI base para emergência: {repr(base_uri)}')
                    app.logger.info(f'Tentando conectar apenas com URI base: {base_uri[:50]}...')
                    mongo_client = MongoClient(base_uri, serverSelectionTimeoutMS=5000)
                    mongo_db = mongo_client.get_database(db_name) if db_name else mongo_client.get_default_database()
                    mongo_client.admin.command('ping')
                    app.logger.warning("MongoDB conectado com URI base (sem opções)")
                    
                    # Se MongoDB é o principal, inicializa os índices
                    if use_primary:
                        from models_mongo import init_mongodb
                        init_mongodb()
                        app.logger.info("Índices MongoDB inicializados")
                    return
                else:
                    raise e  # Re-lança se não há opções para remover
            except Exception as e2:
                error_msg = f'URI do MongoDB malformada mesmo após correção: {e}. Original: {e2}'
                app.logger.error(error_msg)
        elif 'ServerSelectionTimeoutError' in str(type(e)):
            if 'SSL' in str(e) or 'TLS' in str(e) or 'ssl' in str(e).lower():
                error_msg = f'Timeout ao conectar ao MongoDB: {e}. Problema SSL/TLS detectado. Verifique se o servidor está acessível e as configurações SSL estão corretas'
            else:
                error_msg = f'Timeout ao conectar ao MongoDB: {e}. Verifique se o servidor está acessível'
        elif 'Authentication' in str(e):
            error_msg = f'Erro de autenticação MongoDB: {e}. Verifique usuário e senha'
        elif 'SSL' in str(e) or 'TLS' in str(e) or 'ssl' in str(e).lower():
            error_msg = f'Erro SSL/TLS ao conectar ao MongoDB: {e}. Problema de certificado ou handshake SSL'
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