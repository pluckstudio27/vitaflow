from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import json
# Removido: from models.usuario import Usuario, LogAuditoria
import extensions
from bson.objectid import ObjectId
from config.ui_blocks import get_ui_blocks_config

# ConfiguraÃ§Ã£o do Flask-Login
login_manager = LoginManager()

# Classe de usuÃ¡rio para MongoDB
class MongoUser:
    def __init__(self, data: dict):
        self.data = data or {}
    
    def get_id(self):
        return str(self.data.get('_id'))
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return bool(self.data.get('ativo', True))
    
    @property
    def is_anonymous(self):
        return False
    
    # Campos bÃ¡sicos
    @property
    def username(self):
        return self.data.get('username')
    
    @property
    def email(self):
        return self.data.get('email')
    
    @property
    def nome_completo(self):
        return self.data.get('nome_completo')
    
    @property
    def nivel_acesso(self):
        return self.data.get('nivel_acesso')
    
    # Hierarquia (IDs, opcional)
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def almoxarifado_id(self):
        return self.data.get('almoxarifado_id')
    
    @property
    def sub_almoxarifado_id(self):
        return self.data.get('sub_almoxarifado_id')
    
    @property
    def setor_id(self):
        return self.data.get('setor_id')
    
    @property
    def data_criacao(self):
        return self.data.get('data_criacao')
    
    @property
    def ultimo_login(self):
        return self.data.get('ultimo_login')
    
    # Senha
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.data.get('password_hash', ''), password)
    
    def set_password(self, new_password: str):
        self.data['password_hash'] = generate_password_hash(new_password)
    
    def save_password_change(self):
        if extensions.mongo_db is None:
            raise RuntimeError('MongoDB não inicializado')
        extensions.mongo_db['usuarios'].update_one({'_id': self.data['_id']}, {'$set': {'password_hash': self.data['password_hash']}})
    
    def to_dict(self):
        return {
            'id': str(self.data.get('_id')),
            'username': self.username,
            'email': self.email,
            'nome_completo': self.nome_completo,
            'nivel_acesso': self.nivel_acesso,
            'ativo': self.is_active
        }
    
    # Stubs de acesso por escopo (ajuste posterior conforme hierarquia Mongo)
    def can_access_central(self, central_id):
        return True
    
    def can_access_almoxarifado(self, almoxarifado_id):
        return True
    
    def can_access_sub_almoxarifado(self, sub_almoxarifado_id):
        return True
    
    def can_access_setor(self, setor_id):
        return True


def init_login_manager(app):
    """Inicializa o gerenciador de login"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faÃ§a login para acessar esta pÃ¡gina.'
    login_manager.login_message_category = 'info'

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        # Retorna JSON 401 para requisições de API, senão redireciona para login
        is_api_request = (request.is_json or 
                          request.path.startswith('/api/') or 
                          'application/json' in request.headers.get('Accept', ''))
        if is_api_request:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        return redirect(url_for(login_manager.login_view))

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID (MongoDB)"""
    try:
        if extensions.mongo_db is None:
            return None
        doc = extensions.mongo_db['usuarios'].find_one({'_id': ObjectId(user_id)})
        return MongoUser(doc) if doc else None
    except Exception:
        return None


def log_auditoria(acao, tabela=None, registro_id=None, dados_anteriores=None, dados_novos=None):
    """Registra uma ação de auditoria (MongoDB)"""
    try:
        if current_user.is_authenticated and (extensions.mongo_db is not None):
            extensions.mongo_db['logs_auditoria'].insert_one({
                'usuario_id': current_user.get_id(),
                'acao': acao,
                'tabela': tabela,
                'registro_id': registro_id,
                'dados_anteriores': dados_anteriores,
                'dados_novos': dados_novos,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'timestamp': datetime.utcnow(),
            })
    except Exception as e:
        print(f"Erro ao registrar log de auditoria: {e}")


def authenticate_user(username, password):
    """Autentica um usuário (MongoDB)"""
    try:
        if extensions.mongo_db is None:
            print('MongoDB não inicializado')
            return None
        print(f"AUTH DEBUG: tentando autenticar username='{username}'")
        doc = extensions.mongo_db['usuarios'].find_one({'username': username})
        print(f"AUTH DEBUG: usuario encontrado? {bool(doc)}")
        if doc:
            print(f"AUTH DEBUG: ativo={doc.get('ativo')} has_hash={'password_hash' in doc}")
            print(f"AUTH DEBUG: hash='{doc.get('password_hash', '')}'")
            pwd_ok = check_password_hash(doc.get('password_hash', ''), password)
            # Permitir login dev para admin se necessário
            if (not pwd_ok) and username == 'admin' and password == 'admin' and current_app.config.get('DEBUG', True):
                print('AUTH DEBUG: override dev para admin/admin')
                pwd_ok = True
            print(f"AUTH DEBUG: senha confere? {pwd_ok}")
            if doc.get('ativo', True) and pwd_ok:
                usuario = MongoUser(doc)
                extensions.mongo_db['usuarios'].update_one({'_id': doc['_id']}, {'$set': {'ultimo_login': datetime.utcnow()}})
                log_auditoria('LOGIN')
                return usuario
        return None
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None


def logout_user_with_audit():
    """Faz logout do usuÃ¡rio com registro de auditoria (MongoDB)"""
    try:
        if current_user.is_authenticated:
            log_auditoria('LOGOUT')
        logout_user()
    except Exception as e:
        print(f"Erro no logout: {e}")

# Decoradores de autorizaÃ§Ã£o por nÃ­vel hierÃ¡rquico

def require_level(*allowed_levels):
    """
    Decorador que requer níveis específicos de acesso
    
    Args:
        allowed_levels: Lista de níveis permitidos
                       ('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Detecta se é uma requisição de API
            is_api_request = (request.is_json or 
                            request.path.startswith('/api/') or 
                            'application/json' in request.headers.get('Accept', ''))
            
            if not current_user.is_authenticated:
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))
            
            if current_user.nivel_acesso not in allowed_levels:
                if is_api_request:
                    return jsonify({'error': 'Acesso negado - nível insuficiente'}), 403
                flash('Você não tem permissão para acessar esta funcionalidade.', 'error')
                # Redireciona para uma página segura que não causa loop de redirecionamento
                return redirect(url_for('auth.profile'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_super_admin(f):
    """Decorador que requer acesso de super administrador"""
    return require_level('super_admin')(f)

def require_admin_or_above(f):
    """Decorador que requer acesso de administrador ou superior"""
    return require_level('super_admin', 'admin_central')(f)

def require_manager_or_above(f):
    """Decorador que requer acesso de gerente ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox')(f)

def require_responsible_or_above(f):
    """Decorador que requer acesso de responsÃ¡vel ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox')(f)

def require_any_level(f):
    """Decorador que requer qualquer nÃ­vel de acesso (apenas login)"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')(f)

# Decoradores de autorizaÃ§Ã£o por escopo hierÃ¡rquico

def require_central_access(central_id_param='central_id'):
    """
    Decorador que verifica acesso a uma central específica
    
    Args:
        central_id_param: Nome do parâmetro que contém o ID da central
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID da central dos parâmetros da URL, form ou JSON
            central_id = None
            if central_id_param in kwargs:
                central_id = kwargs[central_id_param]
            elif request.method == 'GET':
                central_id = request.args.get(central_id_param)
            elif request.is_json:
                central_id = request.json.get(central_id_param)
            else:
                central_id = request.form.get(central_id_param)
            
            if central_id and not current_user.can_access_central(int(central_id)):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - central não autorizada'}), 403
                flash('Você não tem permissão para acessar esta central.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_almoxarifado_access(almoxarifado_id_param='almoxarifado_id'):
    """
    Decorador que verifica acesso a um almoxarifado específico
    
    Args:
        almoxarifado_id_param: Nome do parâmetro que contém o ID do almoxarifado
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID do almoxarifado dos parâmetros da URL, form ou JSON
            almoxarifado_id = None
            if almoxarifado_id_param in kwargs:
                almoxarifado_id = kwargs[almoxarifado_id_param]
            elif request.method == 'GET':
                almoxarifado_id = request.args.get(almoxarifado_id_param)
            elif request.is_json:
                almoxarifado_id = request.json.get(almoxarifado_id_param)
            else:
                almoxarifado_id = request.form.get(almoxarifado_id_param)
            
            if almoxarifado_id and not current_user.can_access_almoxarifado(int(almoxarifado_id)):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - almoxarifado não autorizado'}), 403
                flash('Você não tem permissão para acessar este almoxarifado.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_sub_almoxarifado_access(sub_almoxarifado_id_param='sub_almoxarifado_id'):
    """
    Decorador que verifica acesso a um sub-almoxarifado específico
    
    Args:
        sub_almoxarifado_id_param: Nome do parâmetro que contém o ID do sub-almoxarifado
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID do sub-almoxarifado dos parâmetros da URL, form ou JSON
            sub_almoxarifado_id = None
            if sub_almoxarifado_id_param in kwargs:
                sub_almoxarifado_id = kwargs[sub_almoxarifado_id_param]
            elif request.method == 'GET':
                sub_almoxarifado_id = request.args.get(sub_almoxarifado_id_param)
            elif request.is_json:
                sub_almoxarifado_id = request.json.get(sub_almoxarifado_id_param)
            else:
                sub_almoxarifado_id = request.form.get(sub_almoxarifado_id_param)
            
            if sub_almoxarifado_id and not current_user.can_access_sub_almoxarifado(int(sub_almoxarifado_id)):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - sub-almoxarifado não autorizado'}), 403
                flash('Você não tem permissão para acessar este sub-almoxarifado.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_setor_access(setor_id_param='setor_id'):
    """
    Decorador que verifica acesso a um setor especÃ­fico
    
    Args:
        setor_id_param: Nome do parÃ¢metro que contÃ©m o ID do setor
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # ObtÃ©m o ID do setor dos parÃ¢metros da URL, form ou JSON
            setor_id = None
            if setor_id_param in kwargs:
                setor_id = kwargs[setor_id_param]
            elif request.method == 'GET':
                setor_id = request.args.get(setor_id_param)
            elif request.is_json:
                setor_id = request.json.get(setor_id_param)
            else:
                setor_id = request.form.get(setor_id_param)
            
            if setor_id and not current_user.can_access_setor(int(setor_id)):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - setor nÃ£o autorizado'}), 403
                flash('VocÃª nÃ£o tem permissÃ£o para acessar este setor.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Filtros de escopo automÃ¡ticos

class ScopeFilter:
    """Classe para aplicar filtros de escopo baseados no usuÃ¡rio logado"""
    
    @staticmethod
    def filter_centrais(query):
        """Filtra centrais baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)  # Nenhum resultado
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todas as centrais
        elif current_user.nivel_acesso == 'admin_central':
            return query.filter_by(id=current_user.central_id)
        elif current_user.nivel_acesso == 'gerente_almox' and current_user.almoxarifado:
            return query.filter_by(id=current_user.almoxarifado.central_id)
        elif current_user.nivel_acesso == 'resp_sub_almox' and current_user.sub_almoxarifado:
            return query.filter_by(id=current_user.sub_almoxarifado.almoxarifado.central_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado.almoxarifado.central_id)
        
        return query.filter(False)  # Nenhum resultado por padrÃ£o
    
    @staticmethod
    def filter_almoxarifados(query):
        """Filtra almoxarifados baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os almoxarifados
        elif current_user.nivel_acesso == 'admin_central':
            return query.filter_by(central_id=current_user.central_id)
        elif current_user.nivel_acesso == 'gerente_almox':
            return query.filter_by(id=current_user.almoxarifado_id)
        elif current_user.nivel_acesso == 'resp_sub_almox' and current_user.sub_almoxarifado:
            return query.filter_by(id=current_user.sub_almoxarifado.almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado.almoxarifado_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_sub_almoxarifados(query):
        """Filtra sub-almoxarifados baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os sub-almoxarifados
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import Almoxarifado, SubAlmoxarifado
            almoxarifados_ids = [a.id for a in Almoxarifado.query.filter_by(central_id=current_user.central_id).all()]
            return query.filter(SubAlmoxarifado.almoxarifado_id.in_(almoxarifados_ids))
        elif current_user.nivel_acesso == 'gerente_almox':
            return query.filter_by(almoxarifado_id=current_user.almoxarifado_id)
        elif current_user.nivel_acesso == 'resp_sub_almox':
            return query.filter_by(id=current_user.sub_almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_setores(query):
        """Filtra setores baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os setores
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import SubAlmoxarifado, Almoxarifado, Setor
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            return query.filter(Setor.sub_almoxarifado_id.in_(sub_almoxarifados_ids))
        elif current_user.nivel_acesso == 'gerente_almox':
            from models.hierarchy import SubAlmoxarifado, Setor
            sub_almoxarifados_ids = [sa.id for sa in SubAlmoxarifado.query.filter_by(almoxarifado_id=current_user.almoxarifado_id).all()]
            return query.filter(Setor.sub_almoxarifado_id.in_(sub_almoxarifados_ids))
        elif current_user.nivel_acesso == 'resp_sub_almox':
            return query.filter_by(sub_almoxarifado_id=current_user.sub_almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor':
            return query.filter_by(id=current_user.setor_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_estoque(query):
        """Filtra estoque baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todo o estoque
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import Setor, SubAlmoxarifado, Almoxarifado
            from models.produto import EstoqueProduto
            # Filtrar por almoxarifados, sub-almoxarifados e setores da central
            almoxarifados_ids = db.session.query(Almoxarifado.id).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            setores_ids = db.session.query(Setor.id).join(SubAlmoxarifado).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            return query.filter(
                db.or_(
                    EstoqueProduto.almoxarifado_id.in_(almoxarifados_ids),
                    EstoqueProduto.sub_almoxarifado_id.in_(sub_almoxarifados_ids),
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'gerente_almox':
            from models.hierarchy import Setor, SubAlmoxarifado
            from models.produto import EstoqueProduto
            # Filtrar por almoxarifado, sub-almoxarifados e setores do almoxarifado
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).filter(SubAlmoxarifado.almoxarifado_id == current_user.almoxarifado_id).subquery()
            setores_ids = db.session.query(Setor.id).join(SubAlmoxarifado).filter(SubAlmoxarifado.almoxarifado_id == current_user.almoxarifado_id).subquery()
            return query.filter(
                db.or_(
                    EstoqueProduto.almoxarifado_id == current_user.almoxarifado_id,
                    EstoqueProduto.sub_almoxarifado_id.in_(sub_almoxarifados_ids),
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'resp_sub_almox':
            from models.hierarchy import Setor
            from models.produto import EstoqueProduto
            # Filtrar por sub-almoxarifado e setores do sub-almoxarifado
            setores_ids = [s.id for s in Setor.query.filter_by(sub_almoxarifado_id=current_user.sub_almoxarifado_id).all()]
            return query.filter(
                db.or_(
                    EstoqueProduto.sub_almoxarifado_id == current_user.sub_almoxarifado_id,
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'operador_setor':
            return query.filter_by(setor_id=current_user.setor_id)
        
        return query.filter(False)

def get_user_context():
    """ObtÃ©m o contexto do usuÃ¡rio para injeÃ§Ã£o em templates (MongoDB)"""
    if current_user.is_authenticated:
        ui_config = get_ui_blocks_config()
        menu_blocks = ui_config.get_menu_blocks_for_user(current_user.nivel_acesso)
        dashboard_widgets = ui_config.get_dashboard_widgets_for_user(current_user.nivel_acesso)
        level = current_user.nivel_acesso or ''
        flags = {
            'is_super_admin': level == 'super_admin',
            'is_admin_central': level == 'admin_central',
            'is_gerente_almox': level == 'gerente_almox',
            'is_resp_sub_almox': level == 'resp_sub_almox',
            'is_operador_setor': level == 'operador_setor',
        }
        scope_labels = {
            'super_admin': 'Super Admin (Todos os escopos)',
            'admin_central': 'Admin Central',
            'gerente_almox': 'Gerente de Almoxarifado',
            'resp_sub_almox': 'ResponsÃ¡vel de Sub-Almoxarifado',
            'operador_setor': 'Operador de Setor',
        }
        return {
            'current_user': current_user,
            'user': current_user,
            'menu_blocks': menu_blocks,
            'dashboard_widgets': dashboard_widgets,
            'scope_name': scope_labels.get(level, 'UsuÃ¡rio'),
            'user_level': level,
            'user_name': getattr(current_user, 'nome_completo', None),
            **flags
        }
    else:
        return {
            'current_user': None,
            'user': None,
            'menu_blocks': [],
            'dashboard_widgets': [],
            'scope_name': '',
            'user_level': None,
            'user_name': None,
            'is_super_admin': False,
            'is_admin_central': False,
            'is_gerente_almox': False,
            'is_resp_sub_almox': False,
            'is_operador_setor': False,
        }
