from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime
import json
from models.usuario import Usuario, LogAuditoria
from extensions import db
from config.ui_blocks import get_ui_blocks_config

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
    return Usuario.query.get(int(user_id))

def log_auditoria(acao, tabela=None, registro_id=None, dados_anteriores=None, dados_novos=None):
    """Registra uma ação de auditoria"""
    try:
        if current_user.is_authenticated:
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
                       ('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')
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
            
            if current_user.nivel_acesso not in allowed_levels:
                if is_api_request:
                    return jsonify({'error': 'Acesso negado - nível insuficiente'}), 403
                flash('Você não tem permissão para acessar esta funcionalidade.', 'error')
                return redirect(url_for('main.index'))
            
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
    """Decorador que requer acesso de responsável ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox')(f)

def require_any_level(f):
    """Decorador que requer qualquer nível de acesso (apenas login)"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')(f)

# Decoradores de autorização por escopo hierárquico

def require_central_access(central_id_param='central_id'):
    """
    Decorador que verifica acesso a uma central específica
    
    Args:
        central_id_param: Nome do parâmetro que contém o ID da central
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
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
        @login_required
        def decorated_function(*args, **kwargs):
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
        @login_required
        def decorated_function(*args, **kwargs):
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
    Decorador que verifica acesso a um setor específico
    
    Args:
        setor_id_param: Nome do parâmetro que contém o ID do setor
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Obtém o ID do setor dos parâmetros da URL, form ou JSON
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
                    return jsonify({'error': 'Acesso negado - setor não autorizado'}), 403
                flash('Você não tem permissão para acessar este setor.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Filtros de escopo automáticos

class ScopeFilter:
    """Classe para aplicar filtros de escopo baseados no usuário logado"""
    
    @staticmethod
    def filter_centrais(query):
        """Filtra centrais baseado no escopo do usuário"""
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
        
        return query.filter(False)  # Nenhum resultado por padrão
    
    @staticmethod
    def filter_almoxarifados(query):
        """Filtra almoxarifados baseado no escopo do usuário"""
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
        """Filtra sub-almoxarifados baseado no escopo do usuário"""
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
        """Filtra setores baseado no escopo do usuário"""
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
        """Filtra estoque baseado no escopo do usuário"""
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
            from models.produto import EstoqueProduto
            return query.filter(EstoqueProduto.setor_id == current_user.setor_id)
        
        return query.filter(False)

def get_user_context():
    """Obtém o contexto do usuário para injeção em templates"""
    if current_user.is_authenticated:
        ui_config = get_ui_blocks_config()
        menu_blocks = ui_config.get_menu_blocks_for_user(current_user.nivel_acesso)
        
        return {
            'current_user': current_user,
            'user': current_user,  # Adiciona 'user' para compatibilidade com templates
            'menu_blocks': menu_blocks,
            'user_level': current_user.nivel_acesso,
            'user_name': current_user.nome_completo
        }
    else:
        return {
            'current_user': None,
            'user': None,  # Adiciona 'user' para compatibilidade com templates
            'menu_blocks': [],
            'user_level': None,
            'user_name': None
        }