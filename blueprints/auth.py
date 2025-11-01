from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
import time
import secrets
from auth import authenticate_user, logout_user_with_audit, get_user_context
# Removido: from models.usuario import Usuario
# Removido: from extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Rate limiting simples por IP para rota de login
LOGIN_ATTEMPTS = {}

def _get_client_ip():
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    xri = request.headers.get('X-Real-IP')
    if xri:
        return xri.strip()
    return request.remote_addr or 'local'

def _too_many_attempts(ip, now=None):
    now = now or time.time()
    window_short = 60.0
    window_long = 600.0
    max_short = 5
    max_long = 20
    attempts = LOGIN_ATTEMPTS.get(ip, [])
    # Filtrar apenas dentro das janelas
    attempts = [t for t in attempts if (now - t) <= window_long]
    LOGIN_ATTEMPTS[ip] = attempts
    count_short = sum(1 for t in attempts if (now - t) <= window_short)
    count_long = len(attempts)
    if count_short >= max_short or count_long >= max_long:
        return True
    return False

def _record_attempt(ip, now=None):
    now = now or time.time()
    attempts = LOGIN_ATTEMPTS.get(ip, [])
    attempts.append(now)
    LOGIN_ATTEMPTS[ip] = attempts

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página e processamento de login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Rate limiting (antes de processar)
        ip = _get_client_ip()
        if _too_many_attempts(ip):
            current_app.logger.warning(f"Rate limit de login atingido para IP {ip}")
            if request.is_json:
                return jsonify({'error': 'Muitas tentativas. Tente novamente em alguns minutos.'}), 429
            flash('Muitas tentativas de login. Tente novamente em alguns minutos.', 'error')
            return render_template('auth/login.html')

        if request.is_json:
            # Login via API JSON
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            # Login via formulário
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            # CSRF básico
            token_form = request.form.get('csrf_token')
            token_sess = session.get('csrf_token')
            if not token_form or token_form != token_sess:
                current_app.logger.warning('CSRF inválido no login via formulário')
                flash('Sessão expirada. Recarregue a página e tente novamente.', 'error')
                return render_template('auth/login.html')
        
        if not username or not password:
            error_msg = 'Usuário e senha são obrigatórios'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        
        # Autentica o usuário (Mongo)
        usuario = authenticate_user(username, password)
        
        if usuario:
            # Faz login do usuário
            remember_me = request.form.get('remember_me', False) if not request.is_json else data.get('remember_me', False)
            login_user(usuario, remember=remember_me)
            # Reset tentativas em caso de sucesso
            ip = _get_client_ip()
            LOGIN_ATTEMPTS.pop(ip, None)
            
            if request.is_json:
                return jsonify({'message': 'Login realizado com sucesso'}), 200
            return redirect(url_for('main.index'))
        else:
            # Registrar tentativa falha
            _record_attempt(ip)
            error_msg = 'Credenciais inválidas'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')
    
    # GET: gerar CSRF para formulário
    session['csrf_token'] = secrets.token_urlsafe(32)
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    logout_user_with_audit()
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário"""
    # Renovar CSRF para operações via formulário nesta página
    session['csrf_token'] = secrets.token_urlsafe(32)
    if request.is_json:
        return jsonify(current_user.to_dict())
    
    context = get_user_context()
    return render_template('auth/profile.html', **context)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Alteração de senha do usuário (Mongo)"""
    if request.is_json:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
    else:
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        # CSRF básico para formulário
        token_form = request.form.get('csrf_token')
        token_sess = session.get('csrf_token')
        if not token_form or token_form != token_sess:
            flash('Sessão expirada. Recarregue a página e tente novamente.', 'error')
            return redirect(url_for('auth.profile'))
    
    # Validações
    if not current_password or not new_password or not confirm_password:
        error_msg = 'Todos os campos são obrigatórios'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    if not current_user.check_password(current_password):
        error_msg = 'Senha atual incorreta'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        error_msg = 'Nova senha e confirmação não coincidem'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    # Atualizar senha no Mongo via método do usuário
    try:
        current_user.set_password(new_password)
        current_user.save_password_change()
        if request.is_json:
            return jsonify({'message': 'Senha alterada com sucesso'}), 200
        flash('Senha alterada com sucesso', 'success')
    except Exception as e:
        if request.is_json:
            return jsonify({'error': f'Erro ao alterar senha: {e}'}), 500
        flash('Erro ao alterar senha', 'error')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/check-session')
def check_session():
    """Verifica se sessão é válida"""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': current_user.to_dict()})
    return jsonify({'authenticated': False}), 200

@auth_bp.app_context_processor
def inject_user_context():
    """Injeta contexto do usuário em templates"""
    return get_user_context()