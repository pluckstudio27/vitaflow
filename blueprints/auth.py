from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from auth import authenticate_user, logout_user_with_audit, get_user_context
from models.usuario import Usuario
from extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página e processamento de login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        if request.is_json:
            # Login via API JSON
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            # Login via formulário
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
        
        if not username or not password:
            error_msg = 'Usuário e senha são obrigatórios'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        
        # Autentica o usuário
        usuario = authenticate_user(username, password)
        
        if usuario:
            # Faz login do usuário
            remember_me = request.form.get('remember_me', False) if not request.is_json else data.get('remember_me', False)
            login_user(usuario, remember=remember_me)
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso',
                    'user': usuario.to_dict(),
                    'redirect_url': url_for('main.index')
                })
            
            flash(f'Bem-vindo, {usuario.nome_completo}!', 'success')
            
            # Redireciona para a página solicitada ou página inicial
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            error_msg = 'Usuário ou senha inválidos'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    if request.is_json:
        logout_user_with_audit()
        return jsonify({'success': True, 'message': 'Logout realizado com sucesso'})
    
    logout_user_with_audit()
    flash('Logout realizado com sucesso', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário"""
    if request.is_json:
        return jsonify(current_user.to_dict())
    
    context = get_user_context()
    return render_template('auth/profile.html', **context)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Alteração de senha do usuário"""
    if request.is_json:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
    else:
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
    
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
    
    if len(new_password) < 6:
        error_msg = 'Nova senha deve ter pelo menos 6 caracteres'
        if request.is_json:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        # Atualiza a senha
        current_user.set_password(new_password)
        db.session.commit()
        
        success_msg = 'Senha alterada com sucesso'
        if request.is_json:
            return jsonify({'success': True, 'message': success_msg})
        flash(success_msg, 'success')
        
    except Exception as e:
        error_msg = 'Erro ao alterar senha'
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/check-session')
def check_session():
    """Verifica se o usuário está logado (para AJAX)"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    return jsonify({'authenticated': False}), 401

# Context processor para disponibilizar dados do usuário em todos os templates
@auth_bp.app_context_processor
def inject_user_context():
    """Injeta contexto do usuário em todos os templates"""
    return get_user_context()