from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime
import json
from extensions import db, is_mongo_available

# Configuração do Flask-Login
login_manager = LoginManager()

def init_login_manager(app):
    """Inicializa o gerenciador de login"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID"""
    if current_app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available():
        try:
            from models_mongo import UsuarioMongo
            return UsuarioMongo.find_by_id(user_id)
        except ImportError:
            pass
    
    # Fallback para SQLAlchemy
    from models.usuario import Usuario
    return Usuario.query.get(int(user_id))

def log_auditoria(acao, tabela=None, registro_id=None, dados_anteriores=None, dados_novos=None):
    """Registra uma ação de auditoria"""
    try:
        if current_user.is_authenticated:
            if current_app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available():
                # Usar MongoDB
                try:
                    from models_mongo import LogAuditoriaMongo
                    log = LogAuditoriaMongo(
                        usuario_id=str(current_user.get_id()),
                        acao=acao,
                        tabela=tabela,
                        registro_id=str(registro_id) if registro_id else None,
                        dados_anteriores=dados_anteriores,
                        dados_novos=dados_novos,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    log.save()
                    return
                except ImportError:
                    pass
            
            # Fallback para SQLAlchemy
            from models.usuario import LogAuditoria
            log = LogAuditoria(
                usuario_id=current_user.id,
                acao=acao,
                tabela=tabela,
                registro_id=registro_id,
                dados_anteriores=json.dumps(dados_anteriores) if dados_anteriores else None,
                dados_novos=json.dumps(dados_novos) if dados_novos else None,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(log)
            db.session.commit()
    except Exception as e:
        print(f"Erro ao registrar log de auditoria: {e}")

def authenticate_user(username, password):
    """Autentica um usuário"""
    try:
        if current_app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available():
            # Usar MongoDB
            try:
                from models_mongo import UsuarioMongo
                usuario = UsuarioMongo.find_by_username(username)
                
                if usuario and usuario.ativo and usuario.check_password(password):
                    # Atualiza último login
                    usuario.ultimo_login = datetime.utcnow()
                    usuario.save()
                    
                    # Registra login na auditoria
                    log_auditoria('LOGIN')
                    
                    return usuario
                return None
            except ImportError:
                pass
        
        # Fallback para SQLAlchemy
        from models.usuario import Usuario
        usuario = Usuario.query.filter_by(username=username, ativo=True).first()
        
        if usuario and usuario.check_password(password):
            # Atualiza último login
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
            
            # Registra login na auditoria
            log_auditoria('LOGIN')
            
            return usuario
        return None
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None

def logout_user_with_audit():
    """Faz logout do usuário com registro de auditoria"""
    try:
        if current_user.is_authenticated:
            log_auditoria('LOGOUT')
        logout_user()
    except Exception as e:
        print(f"Erro no logout: {e}")

# Decoradores de autorização por nível hierárquico

def require_level(*allowed_levels):
    """
    Decorador que requer níveis específicos de acesso
    
    Args:
        allowed_levels: Lista de níveis permitidos
                       ('admin_sistema', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Detecta se é uma requisição de API
            is_api_request = (request.is_json or 
                            request.path.startswith('/api/') or 
                            'application/json' in request.headers.get('Accept', ''))
            
            if not current_user.is_authenticated:
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))
            
            user_level = getattr(current_user, 'nivel_acesso', 'operador_setor')
            if user_level not in allowed_levels:
                if is_api_request:
                    return jsonify({'error': 'Acesso negado - nível insuficiente'}), 403
                flash('Você não tem permissão para acessar esta funcionalidade.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin_sistema(f):
    """Requer nível de administrador do sistema"""
    return require_level('super_admin')(f)

def require_admin_or_above(f):
    """Requer nível de administrador ou superior"""
    return require_level('super_admin', 'admin_central')(f)

def require_manager_or_above(f):
    """Requer nível de gerente ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox')(f)

def require_responsible_or_above(f):
    """Requer nível de responsável ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox')(f)

def require_any_level(f):
    """Permite qualquer nível autenticado"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')(f)

def require_central_access(central_id_param='central_id'):
    """
    Decorador que verifica se o usuário tem acesso à central especificada
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            central_id = kwargs.get(central_id_param) or request.args.get(central_id_param)
            
            if not central_id:
                return jsonify({'error': 'ID da central não fornecido'}), 400
            
            # Admin sistema tem acesso a tudo
            if getattr(current_user, 'nivel_acesso', '') == 'admin_sistema':
                return f(*args, **kwargs)
            
            # Verifica se o usuário tem acesso à central
            user_central_id = getattr(current_user, 'central_id', None)
            if user_central_id and str(user_central_id) == str(central_id):
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Acesso negado à central'}), 403
        return decorated_function
    return decorator

def require_almoxarifado_access(almoxarifado_id_param='almoxarifado_id'):
    """
    Decorador que verifica se o usuário tem acesso ao almoxarifado especificado
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            almoxarifado_id = kwargs.get(almoxarifado_id_param) or request.args.get(almoxarifado_id_param)
            
            if not almoxarifado_id:
                return jsonify({'error': 'ID do almoxarifado não fornecido'}), 400
            
            # Admin sistema e central têm acesso a tudo
            user_level = getattr(current_user, 'nivel_acesso', '')
            if user_level in ['admin_sistema', 'admin_central']:
                return f(*args, **kwargs)
            
            # Verifica se o usuário tem acesso ao almoxarifado
            user_almox_id = getattr(current_user, 'almoxarifado_id', None)
            if user_almox_id and str(user_almox_id) == str(almoxarifado_id):
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Acesso negado ao almoxarifado'}), 403
        return decorated_function
    return decorator

def require_sub_almoxarifado_access(sub_almoxarifado_id_param='sub_almoxarifado_id'):
    """
    Decorador que verifica se o usuário tem acesso ao sub-almoxarifado especificado
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            sub_almox_id = kwargs.get(sub_almoxarifado_id_param) or request.args.get(sub_almoxarifado_id_param)
            
            if not sub_almox_id:
                return jsonify({'error': 'ID do sub-almoxarifado não fornecido'}), 400
            
            # Admin sistema, central e gerente têm acesso a tudo
            user_level = getattr(current_user, 'nivel_acesso', '')
            if user_level in ['admin_sistema', 'admin_central', 'gerente_almox']:
                return f(*args, **kwargs)
            
            # Verifica se o usuário tem acesso ao sub-almoxarifado
            user_sub_almox_id = getattr(current_user, 'sub_almoxarifado_id', None)
            if user_sub_almox_id and str(user_sub_almox_id) == str(sub_almox_id):
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Acesso negado ao sub-almoxarifado'}), 403
        return decorated_function
    return decorator

class ScopeFilter:
    """Classe para filtrar dados baseado no escopo do usuário"""
    
    @staticmethod
    def get_user_scope():
        """Retorna o escopo do usuário atual"""
        if not current_user.is_authenticated:
            return None
        
        return {
            'nivel_acesso': getattr(current_user, 'nivel_acesso', 'operador_setor'),
            'central_id': getattr(current_user, 'central_id', None),
            'almoxarifado_id': getattr(current_user, 'almoxarifado_id', None),
            'sub_almoxarifado_id': getattr(current_user, 'sub_almoxarifado_id', None),
            'categoria_id': getattr(current_user, 'categoria_id', None)
        }
    
    @staticmethod
    def filter_by_scope(model_class, **filters):
        """Filtra dados baseado no escopo do usuário"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return []
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            if current_app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available():
                return model_class.find_all(**filters)
            else:
                return model_class.query.filter_by(**filters).all()
        
        # Aplica filtros baseados no escopo
        if scope['central_id']:
            filters['central_id'] = scope['central_id']
        if scope['almoxarifado_id']:
            filters['almoxarifado_id'] = scope['almoxarifado_id']
        if scope['sub_almoxarifado_id']:
            filters['sub_almoxarifado_id'] = scope['sub_almoxarifado_id']
        if scope['categoria_id']:
            filters['categoria_id'] = scope['categoria_id']
        
        if current_app.config.get('USE_MONGODB_PRIMARY') and is_mongo_available():
            return model_class.find_all(**filters)
        else:
            return model_class.query.filter_by(**filters).all()
    
    @staticmethod
    def filter_centrais_mongo(centrais_cursor):
        """Filtra centrais MongoDB baseado no escopo do usuário"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return []
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return list(centrais_cursor)
        
        # Filtra por central do usuário
        if scope['central_id']:
            from bson import ObjectId
            return [c for c in centrais_cursor if str(c._id) == str(scope['central_id'])]
        
        return list(centrais_cursor)
    
    @staticmethod
    def filter_almoxarifados_mongo(almoxarifados_cursor):
        """Filtra almoxarifados MongoDB baseado no escopo do usuário"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return []
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return list(almoxarifados_cursor)
        
        # Filtra por central/almoxarifado do usuário
        almoxarifados = list(almoxarifados_cursor)
        if scope['almoxarifado_id']:
            from bson import ObjectId
            return [a for a in almoxarifados if str(a._id) == str(scope['almoxarifado_id'])]
        elif scope['central_id']:
            from bson import ObjectId
            return [a for a in almoxarifados if str(a.central_id) == str(scope['central_id'])]
        
        return almoxarifados
    
    @staticmethod
    def filter_sub_almoxarifados_mongo(sub_almoxarifados_cursor):
        """Filtra sub-almoxarifados MongoDB baseado no escopo do usuário"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return []
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return list(sub_almoxarifados_cursor)
        
        # Filtra por sub-almoxarifado/almoxarifado do usuário
        sub_almoxarifados = list(sub_almoxarifados_cursor)
        if scope['sub_almoxarifado_id']:
            from bson import ObjectId
            return [s for s in sub_almoxarifados if str(s._id) == str(scope['sub_almoxarifado_id'])]
        elif scope['almoxarifado_id']:
            from bson import ObjectId
            return [s for s in sub_almoxarifados if str(s.almoxarifado_id) == str(scope['almoxarifado_id'])]
        
        return sub_almoxarifados
    
    @staticmethod
    def filter_setores_mongo(setores_cursor):
        """Filtra setores MongoDB baseado no escopo do usuário"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return []
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return list(setores_cursor)
        
        # Filtra por setor/sub-almoxarifado do usuário
        setores = list(setores_cursor)
        if scope.get('setor_id'):
            from bson import ObjectId
            return [s for s in setores if str(s._id) == str(scope['setor_id'])]
        elif scope['sub_almoxarifado_id']:
            from bson import ObjectId
            return [s for s in setores if str(s.sub_almoxarifado_id) == str(scope['sub_almoxarifado_id'])]
        
        return setores
    
    @staticmethod
    def get_mongo_filter_setores():
        """Retorna filtros de escopo para setores MongoDB"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return {}
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return {}
        
        filters = {}
        if scope.get('setor_id'):
            from bson import ObjectId
            try:
                filters['_id'] = ObjectId(scope['setor_id'])
            except:
                pass
        elif scope['sub_almoxarifado_id']:
            from bson import ObjectId
            try:
                filters['sub_almoxarifado_id'] = ObjectId(scope['sub_almoxarifado_id'])
            except:
                pass
        
        return filters
    
    @staticmethod
    def filter_estoque_mongo():
        """Retorna filtros de escopo para estoque MongoDB"""
        scope = ScopeFilter.get_user_scope()
        if not scope:
            return {}
        
        # Admin sistema vê tudo
        if scope['nivel_acesso'] == 'admin_sistema':
            return {}
        
        filters = {}
        if scope['central_id']:
            filters['central_id'] = scope['central_id']
        if scope['almoxarifado_id']:
            filters['almoxarifado_id'] = scope['almoxarifado_id']
        if scope['sub_almoxarifado_id']:
            filters['sub_almoxarifado_id'] = scope['sub_almoxarifado_id']
        if scope.get('setor_id'):
            filters['setor_id'] = scope['setor_id']
        
        return filters

def get_user_context():
    """Retorna contexto do usuário para templates"""
    if not current_user.is_authenticated:
        return {
            'user_authenticated': False,
            'user_level': None,
            'user_scope': None,
            'ui_blocks': {},
            'menu_blocks': [],
            'dashboard_widgets': [],
            'settings_sections': []
        }
    
    scope = ScopeFilter.get_user_scope()
    
    try:
        from config.ui_blocks import get_ui_blocks_config
        ui_config = get_ui_blocks_config()
        ui_blocks = {
            'menu_blocks': ui_config.get_menu_blocks_for_user(scope['nivel_acesso']),
            'dashboard_widgets': ui_config.get_dashboard_widgets_for_user(scope['nivel_acesso']),
            'settings_sections': ui_config.get_settings_sections_for_user(scope['nivel_acesso'])
        }
    except ImportError:
        ui_blocks = {}
    
    return {
        'user_authenticated': True,
        'user_level': scope['nivel_acesso'],
        'user_scope': scope,
        'ui_blocks': ui_blocks,
        'menu_blocks': ui_blocks.get('menu_blocks', []),
        'dashboard_widgets': ui_blocks.get('dashboard_widgets', []),
        'settings_sections': ui_blocks.get('settings_sections', []),
        'current_user': current_user,
        'user': current_user  # Adiciona 'user' para compatibilidade com templates
    }