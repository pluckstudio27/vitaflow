from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vitaflow-hospital-angicos-2024')
# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Render.com usa postgres:// mas SQLAlchemy precisa de postgresql://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///hospital_almoxarifado.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações para upload de arquivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# Função de contexto global para templates
@app.context_processor
def inject_date():
    return {'hoje': date.today()}

# Funções auxiliares para upload de arquivos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        # Gerar nome único para o arquivo
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return unique_filename
    return None

# Modelo de usuários para autenticação
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)  # admin, tecnico, secretaria, operador
    setor = db.Column(db.String(50))  # enfermagem, farmacia, laboratorio, centro_cirurgico, administracao
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nome_completo': self.nome_completo,
            'cargo': self.cargo,
            'setor': self.setor,
            'ativo': self.ativo,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

# Decorador para verificar login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para verificar permissões por cargo
def requires_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user or user.cargo not in roles:
                flash('Você não tem permissão para acessar esta página.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decorador específico para usuários com acesso limitado a solicitações
def requires_solicitation_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('login'))
        
        # Permitir acesso para admin, tecnico, secretaria, operador e usuario
        allowed_roles = ['admin', 'tecnico', 'secretaria', 'operador', 'usuario']
        if user.cargo not in allowed_roles:
            flash('Você não tem permissão para acessar esta página.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Modelo de dados para itens do almoxarifado
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    setor = db.Column(db.String(50), nullable=False)  # enfermagem, farmacia, laboratorio, centro_cirurgico
    localizacao = db.Column(db.String(20), nullable=False)  # almoxarifado, farmacia
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    data_compra = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date)
    preco_unitario = db.Column(db.Float)
    fornecedor = db.Column(db.String(100))
    lote = db.Column(db.String(50))
    foto = db.Column(db.String(200))  # Caminho para a foto do item
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Item {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'setor': self.setor,
            'localizacao': self.localizacao,
            'quantidade': self.quantidade,
            'data_compra': self.data_compra.strftime('%Y-%m-%d') if self.data_compra else None,
            'data_vencimento': self.data_vencimento.strftime('%Y-%m-%d') if self.data_vencimento else None,
            'preco_unitario': self.preco_unitario,
            'fornecedor': self.fornecedor,
            'lote': self.lote
        }

# Modelo de dados para solicitações de compras
class SolicitacaoCompra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(20), unique=True, nullable=False)  # Protocolo único gerado automaticamente
    setor = db.Column(db.String(50), nullable=False)  # enfermagem, farmacia, laboratorio, centro_cirurgico
    item_nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    quantidade_solicitada = db.Column(db.Integer, nullable=False)
    prioridade = db.Column(db.String(20), nullable=False, default='normal')  # urgente, alta, normal, baixa
    justificativa = db.Column(db.Text)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_necessidade = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='aguardando_autorizacao')  # aguardando_autorizacao, autorizada, rejeitada_tecnico, aguardando_validacao, validada, rejeitada_secretaria, aprovada, comprada
    solicitante = db.Column(db.String(100), nullable=False)
    cargo_solicitante = db.Column(db.String(50))  # Cargo do solicitante
    responsavel_tecnico = db.Column(db.String(100))  # Enfermeiro, farmacêutico, nutricionista responsável
    cargo_responsavel = db.Column(db.String(50))  # enfermeiro, farmaceutico, nutricionista
    data_autorizacao = db.Column(db.DateTime)  # Data da autorização técnica
    observacoes_tecnico = db.Column(db.Text)  # Observações do responsável técnico
    secretaria_validador = db.Column(db.String(100))  # Nome da secretária que validou
    data_validacao = db.Column(db.DateTime)  # Data da validação pela secretária
    observacoes_secretaria = db.Column(db.Text)  # Observações da secretária
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SolicitacaoCompra {self.item_nome} - {self.setor}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'protocolo': self.protocolo,
            'setor': self.setor,
            'item_nome': self.item_nome,
            'descricao': self.descricao,
            'quantidade_solicitada': self.quantidade_solicitada,
            'prioridade': self.prioridade,
            'justificativa': self.justificativa,
            'data_solicitacao': self.data_solicitacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_solicitacao else None,
            'data_necessidade': self.data_necessidade.strftime('%Y-%m-%d') if self.data_necessidade else None,
            'status': self.status,
            'solicitante': self.solicitante,
            'cargo_solicitante': self.cargo_solicitante,
            'responsavel_tecnico': self.responsavel_tecnico,
            'cargo_responsavel': self.cargo_responsavel,
            'data_autorizacao': self.data_autorizacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_autorizacao else None,
            'observacoes_tecnico': self.observacoes_tecnico,
            'secretaria_validador': self.secretaria_validador,
            'data_validacao': self.data_validacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_validacao else None,
            'observacoes_secretaria': self.observacoes_secretaria,
            'observacoes': self.observacoes
        }

# Modelo de dados para análise de consumo
class AnaliseConsumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    mes_referencia = db.Column(db.Date, nullable=False)
    consumo_mensal = db.Column(db.Integer, nullable=False, default=0)
    estoque_minimo = db.Column(db.Integer, nullable=False, default=0)
    estoque_maximo = db.Column(db.Integer, nullable=False, default=0)
    media_consumo_3meses = db.Column(db.Float, default=0)
    media_consumo_6meses = db.Column(db.Float, default=0)
    sugestao_compra = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com Item
    item = db.relationship('Item', backref=db.backref('analises_consumo', lazy=True))
    
    def __repr__(self):
        return f'<AnaliseConsumo {self.item.nome if self.item else "Item"} - {self.mes_referencia}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'mes_referencia': self.mes_referencia.strftime('%Y-%m-%d') if self.mes_referencia else None,
            'consumo_mensal': self.consumo_mensal,
            'estoque_minimo': self.estoque_minimo,
            'estoque_maximo': self.estoque_maximo,
            'media_consumo_3meses': self.media_consumo_3meses,
            'media_consumo_6meses': self.media_consumo_6meses,
            'sugestao_compra': self.sugestao_compra
        }

# Modelo de dados para movimentações de estoque
# Modelo para gerenciar recebimento e conferência de pedidos
class RecebimentoPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(20), nullable=False)  # Protocolo da solicitação relacionada
    numero_nota_fiscal = db.Column(db.String(50), nullable=False)
    fornecedor = db.Column(db.String(100), nullable=False)
    data_emissao_nf = db.Column(db.Date, nullable=False)
    valor_total_nf = db.Column(db.Float, nullable=False)
    data_recebimento = db.Column(db.DateTime, default=datetime.utcnow)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)  # Secretária responsável
    status_conferencia = db.Column(db.String(30), nullable=False, default='pendente')  # pendente, conferido, divergencia
    observacoes_conferencia = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RecebimentoPedido {self.protocolo} - NF: {self.numero_nota_fiscal}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'protocolo': self.protocolo,
            'numero_nota_fiscal': self.numero_nota_fiscal,
            'fornecedor': self.fornecedor,
            'data_emissao_nf': self.data_emissao_nf.strftime('%Y-%m-%d') if self.data_emissao_nf else None,
            'valor_total_nf': self.valor_total_nf,
            'data_recebimento': self.data_recebimento.strftime('%Y-%m-%d %H:%M:%S') if self.data_recebimento else None,
            'responsavel_recebimento': self.responsavel_recebimento,
            'status_conferencia': self.status_conferencia,
            'observacoes_conferencia': self.observacoes_conferencia
        }

# Modelo para itens específicos do recebimento
class ItemRecebimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(db.Integer, db.ForeignKey('recebimento_pedido.id'), nullable=False)
    item_nome = db.Column(db.String(100), nullable=False)
    quantidade_pedida = db.Column(db.Integer, nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    lote = db.Column(db.String(50))
    data_validade = db.Column(db.Date)
    preco_unitario = db.Column(db.Float)
    status_item = db.Column(db.String(20), nullable=False, default='conforme')  # conforme, divergente, vencido, danificado
    observacoes_item = db.Column(db.Text)
    destino_final = db.Column(db.String(50))  # almoxarifado, farmacia
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    recebimento = db.relationship('RecebimentoPedido', backref=db.backref('itens', lazy=True))
    
    def __repr__(self):
        return f'<ItemRecebimento {self.item_nome} - {self.quantidade_recebida}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'recebimento_id': self.recebimento_id,
            'item_nome': self.item_nome,
            'quantidade_pedida': self.quantidade_pedida,
            'quantidade_recebida': self.quantidade_recebida,
            'lote': self.lote,
            'data_validade': self.data_validade.strftime('%Y-%m-%d') if self.data_validade else None,
            'preco_unitario': self.preco_unitario,
            'status_item': self.status_item,
            'observacoes_item': self.observacoes_item,
            'destino_final': self.destino_final
        }

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'transferencia' ou 'saida'
    origem = db.Column(db.String(50), nullable=False)  # almoxarifado, farmacia
    destino = db.Column(db.String(50), nullable=False)  # farmacia, enfermagem, laboratorio, centro_cirurgico
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200))  # Motivo da movimentação
    responsavel = db.Column(db.String(100))  # Quem fez a movimentação
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    
    # Relacionamento com Item
    item = db.relationship('Item', backref=db.backref('movimentacoes', lazy=True))
    
    def __repr__(self):
        return f'<Movimentacao {self.tipo}: {self.quantidade} de {self.item.nome if self.item else "Item"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_nome': self.item.nome if self.item else None,
            'tipo': self.tipo,
            'origem': self.origem,
            'destino': self.destino,
            'quantidade': self.quantidade,
            'motivo': self.motivo,
            'responsavel': self.responsavel,
            'data_movimentacao': self.data_movimentacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_movimentacao else None,
            'observacoes': self.observacoes
        }

# Rota principal - Dashboard
# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.ativo:
            session['user_id'] = user.id
            session['username'] = user.username
            session['nome_completo'] = user.nome_completo
            session['cargo'] = user.cargo
            session['setor'] = user.setor
            
            # Atualizar último login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Bem-vindo(a), {user.nome_completo}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/usuarios', endpoint='usuarios')
@requires_role(['admin'])
def gerenciar_usuarios():
    usuarios = User.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/adicionar', methods=['GET', 'POST'])
@requires_role(['admin'])
def adicionar_usuario():
    if request.method == 'POST':
        # Validações
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Verificar se as senhas coincidem
        if password != confirm_password:
            flash('As senhas não coincidem!', 'error')
            return render_template('adicionar_usuario.html')
        
        # Verificar se username já existe
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe!', 'error')
            return render_template('adicionar_usuario.html')
        
        # Verificar se email já existe
        if User.query.filter_by(email=email).first():
            flash('E-mail já está em uso!', 'error')
            return render_template('adicionar_usuario.html')
        
        novo_usuario = User(
            username=username,
            email=email,
            nome_completo=request.form['nome_completo'],
            cargo=request.form['cargo'],
            setor=request.form.get('setor', ''),
            ativo='ativo' in request.form
        )
        novo_usuario.set_password(password)
        
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            flash(f'Usuário {novo_usuario.nome_completo} criado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {str(e)}', 'error')
    
    return render_template('adicionar_usuario.html')

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@requires_role(['admin'])
def editar_usuario(id):
    usuario = User.query.get_or_404(id)
    
    if request.method == 'POST':
        # Validações
        username = request.form['username']
        email = request.form['email']
        
        # Verificar se username já existe (exceto o próprio usuário)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != id:
            flash('Nome de usuário já existe!', 'error')
            return render_template('editar_usuario.html', usuario=usuario)
        
        # Verificar se email já existe (exceto o próprio usuário)
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != id:
            flash('E-mail já está em uso!', 'error')
            return render_template('editar_usuario.html', usuario=usuario)
        
        # Atualizar dados
        usuario.username = username
        usuario.email = email
        usuario.nome_completo = request.form['nome_completo']
        usuario.cargo = request.form['cargo']
        usuario.setor = request.form.get('setor', '')
        usuario.ativo = 'ativo' in request.form
        
        # Atualizar senha se fornecida
        if request.form.get('password'):
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            if password != confirm_password:
                flash('As senhas não coincidem!', 'error')
                return render_template('editar_usuario.html', usuario=usuario)
            
            usuario.set_password(password)
        
        try:
            db.session.commit()
            flash(f'Usuário {usuario.nome_completo} atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
@requires_role(['admin'])
def excluir_usuario(id):
    usuario = User.query.get_or_404(id)
    
    # Não permitir excluir o próprio usuário
    if session.get('user_id') == id:
        flash('Você não pode excluir sua própria conta!', 'error')
        return redirect(url_for('usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuário {usuario.nome_completo} excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    
    return redirect(url_for('usuarios'))

@app.route('/usuarios/toggle/<int:id>', methods=['POST'])
@requires_role(['admin'])
def toggle_usuario(id):
    usuario = User.query.get_or_404(id)
    
    # Não permitir desativar o próprio usuário
    if session.get('user_id') == id:
        flash('Você não pode desativar sua própria conta!', 'error')
        return redirect(url_for('usuarios'))
    
    try:
        usuario.ativo = not usuario.ativo
        db.session.commit()
        status = 'ativado' if usuario.ativo else 'desativado'
        flash(f'Usuário {usuario.nome_completo} {status} com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar status do usuário: {str(e)}', 'error')
    
    return redirect(url_for('usuarios'))

@app.route('/test')
def test_route():
    return "VitaFlow está funcionando! Acesse /login para fazer login."

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas gerais
    total_almoxarifado = Item.query.filter_by(localizacao='almoxarifado').count()
    total_farmacia = Item.query.filter_by(localizacao='farmacia').count()
    total_geral = Item.query.count()
    
    # Quantidades totais
    quantidade_almoxarifado = db.session.query(db.func.sum(Item.quantidade)).filter_by(localizacao='almoxarifado').scalar() or 0
    quantidade_farmacia = db.session.query(db.func.sum(Item.quantidade)).filter_by(localizacao='farmacia').scalar() or 0
    quantidade_total = quantidade_almoxarifado + quantidade_farmacia
    
    # Valor total estimado
    valor_total = db.session.query(db.func.sum(Item.quantidade * Item.preco_unitario)).filter(
        Item.preco_unitario.isnot(None)
    ).scalar() or 0
    
    # Itens próximos ao vencimento (30 dias)
    from datetime import timedelta
    data_limite = date.today() + timedelta(days=30)
    itens_vencendo = Item.query.filter(
        Item.data_vencimento.isnot(None),
        Item.data_vencimento <= data_limite,
        Item.data_vencimento >= date.today()
    ).count()
    
    # Itens vencidos
    itens_vencidos = Item.query.filter(
        Item.data_vencimento.isnot(None),
        Item.data_vencimento < date.today()
    ).count()
    
    # Itens com estoque baixo (≤5 unidades)
    estoque_baixo = Item.query.filter(Item.quantidade <= 5).count()
    
    # Estatísticas por setor
    setores = ['enfermagem', 'farmacia', 'laboratorio', 'centro_cirurgico']
    estatisticas_setor = {}
    
    for setor in setores:
        almox = Item.query.filter_by(setor=setor, localizacao='almoxarifado').count()
        farm = Item.query.filter_by(setor=setor, localizacao='farmacia').count()
        estatisticas_setor[setor] = {
            'almoxarifado': almox,
            'farmacia': farm,
            'total': almox + farm
        }
    
    stats = {
        'total_almoxarifado': total_almoxarifado,
        'total_farmacia': total_farmacia,
        'total_geral': total_geral,
        'quantidade_almoxarifado': quantidade_almoxarifado,
        'quantidade_farmacia': quantidade_farmacia,
        'quantidade_total': quantidade_total,
        'valor_total': valor_total if valor_total > 0 else None,
        'itens_vencendo': itens_vencendo,
        'itens_vencidos': itens_vencidos,
        'estoque_baixo': estoque_baixo,
        'por_setor': {setor: dados['total'] for setor, dados in estatisticas_setor.items()}
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         estatisticas_setor=estatisticas_setor,
                         date=date)

# Rota para listar todos os itens
@app.route('/itens')
def listar_itens():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Filtros
    setor = request.args.get('setor')
    localizacao = request.args.get('localizacao')
    vencimento = request.args.get('vencimento')
    estoque = request.args.get('estoque')
    busca = request.args.get('busca')
    
    query = Item.query
    
    # Filtro por setor
    if setor:
        query = query.filter_by(setor=setor)
    
    # Filtro por localização
    if localizacao:
        query = query.filter_by(localizacao=localizacao)
    
    # Filtro por vencimento
    if vencimento:
        if vencimento == 'proximo':
            # Próximos 30 dias
            from datetime import timedelta
            data_limite = date.today() + timedelta(days=30)
            query = query.filter(
                Item.data_vencimento.isnot(None),
                Item.data_vencimento <= data_limite,
                Item.data_vencimento >= date.today()
            )
        elif vencimento == 'vencido':
            # Itens vencidos
            query = query.filter(
                Item.data_vencimento.isnot(None),
                Item.data_vencimento < date.today()
            )
        elif vencimento == 'sem_data':
            # Sem data de vencimento
            query = query.filter(Item.data_vencimento.is_(None))
    
    # Filtro por estoque
    if estoque:
        if estoque == 'baixo':
            # Estoque baixo (≤5 unidades)
            query = query.filter(Item.quantidade <= 5)
        elif estoque == 'zero':
            # Sem estoque
            query = query.filter(Item.quantidade == 0)
        elif estoque == 'alto':
            # Estoque alto (>20 unidades)
            query = query.filter(Item.quantidade > 20)
    
    # Filtro por busca
    if busca:
        query = query.filter(
            db.or_(
                Item.nome.contains(busca),
                Item.descricao.contains(busca),
                Item.fornecedor.contains(busca),
                Item.lote.contains(busca)
            )
        )
    
    # Ordenação
    ordenacao = request.args.get('ordenacao', 'recente')
    if ordenacao == 'nome':
        query = query.order_by(Item.nome.asc())
    elif ordenacao == 'quantidade':
        query = query.order_by(Item.quantidade.desc())
    elif ordenacao == 'vencimento':
        query = query.order_by(Item.data_vencimento.asc().nullslast())
    elif ordenacao == 'setor':
        query = query.order_by(Item.setor.asc(), Item.nome.asc())
    else:  # recente
        query = query.order_by(Item.created_at.desc())
    
    itens = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Estatísticas dos resultados filtrados
    total_filtrado = query.count()
    
    # Calcular estatísticas dos itens filtrados
    itens_filtrados = query.all()
    stats_filtrados = {
        'total_itens': len(itens_filtrados),
        'almoxarifado': len([i for i in itens_filtrados if i.localizacao == 'almoxarifado']),
        'farmacia': len([i for i in itens_filtrados if i.localizacao == 'farmacia']),
        'vencidos': len([i for i in itens_filtrados if i.data_vencimento and i.data_vencimento < date.today()]),
        'estoque_baixo': len([i for i in itens_filtrados if i.quantidade <= 5]),
        'valor_total': sum([i.preco_unitario * i.quantidade for i in itens_filtrados if i.preco_unitario])
    }
    
    filtros_ativos = {
        'setor': setor,
        'localizacao': localizacao,
        'vencimento': vencimento,
        'estoque': estoque,
        'busca': busca,
        'ordenacao': ordenacao
    }
    
    return render_template('listar_itens.html', 
                         itens=itens, 
                         filtros=filtros_ativos,
                         stats=stats_filtrados,
                         total_filtrado=total_filtrado,
                         date=date)

# Rota para adicionar novo item
@app.route('/itens/adicionar', methods=['GET', 'POST'])
def adicionar_item():
    if request.method == 'POST':
        try:
            # Converter strings de data para objetos date
            data_compra = datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
            data_vencimento = None
            if request.form.get('data_vencimento'):
                data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date()
            
            # Processar upload de foto
            foto_filename = None
            if 'foto' in request.files:
                file = request.files['foto']
                if file.filename != '':
                    foto_filename = save_uploaded_file(file)
                    if not foto_filename:
                        flash('Formato de arquivo não suportado. Use PNG, JPG, JPEG ou GIF.', 'error')
                        return render_template('adicionar_item.html')
            
            novo_item = Item(
                nome=request.form['nome'],
                descricao=request.form.get('descricao', ''),
                setor=request.form['setor'],
                localizacao=request.form['localizacao'],
                quantidade=int(request.form['quantidade']),
                data_compra=data_compra,
                data_vencimento=data_vencimento,
                preco_unitario=float(request.form['preco_unitario']) if request.form.get('preco_unitario') else None,
                fornecedor=request.form.get('fornecedor', ''),
                lote=request.form.get('lote', ''),
                foto=foto_filename
            )
            
            db.session.add(novo_item)
            db.session.commit()
            
            flash(f'Item "{novo_item.nome}" adicionado com sucesso!', 'success')
            return redirect(url_for('listar_itens'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar item: {str(e)}', 'error')
    
    return render_template('adicionar_item.html')

# Rota para editar item
@app.route('/itens/editar/<int:id>', methods=['GET', 'POST'])
def editar_item(id):
    item = Item.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Converter strings de data para objetos date
            data_compra = datetime.strptime(request.form['data_compra'], '%Y-%m-%d').date()
            data_vencimento = None
            if request.form.get('data_vencimento'):
                data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date()
            
            # Processar upload de nova foto
            if 'foto' in request.files:
                file = request.files['foto']
                if file.filename != '':
                    # Remover foto antiga se existir
                    if item.foto:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], item.foto)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # Salvar nova foto
                    foto_filename = save_uploaded_file(file)
                    if foto_filename:
                        item.foto = foto_filename
                    else:
                        flash('Formato de arquivo não suportado. Use PNG, JPG, JPEG ou GIF.', 'error')
                        return render_template('editar_item.html', item=item)
            
            item.nome = request.form['nome']
            item.descricao = request.form.get('descricao', '')
            item.setor = request.form['setor']
            item.localizacao = request.form['localizacao']
            item.quantidade = int(request.form['quantidade'])
            item.data_compra = data_compra
            item.data_vencimento = data_vencimento
            item.preco_unitario = float(request.form['preco_unitario']) if request.form.get('preco_unitario') else None
            item.fornecedor = request.form.get('fornecedor', '')
            item.lote = request.form.get('lote', '')
            item.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Item "{item.nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('listar_itens'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar item: {str(e)}', 'error')
    
    return render_template('editar_item.html', item=item)

# Rota para excluir item
@app.route('/itens/excluir/<int:id>')
def excluir_item(id):
    item = Item.query.get_or_404(id)
    
    try:
        nome_item = item.nome
        db.session.delete(item)
        db.session.commit()
        
        flash(f'Item "{nome_item}" excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir item: {str(e)}', 'error')
    
    return redirect(url_for('listar_itens'))

# Rota para ver detalhes do item
@app.route('/itens/detalhes/<int:id>')
def detalhes_item(id):
    item = Item.query.get_or_404(id)
    return render_template('detalhes_item.html', item=item)

# Rota para servir imagens uploadadas
# Rota para transferir itens do almoxarifado para farmácia
@app.route('/transferir', methods=['GET', 'POST'])
def transferir_item():
    if request.method == 'POST':
        item_id = request.form['item_id']
        quantidade = int(request.form['quantidade'])
        responsavel = request.form['responsavel']
        motivo = request.form.get('motivo', '')
        observacoes = request.form.get('observacoes', '')
        
        item = Item.query.get_or_404(item_id)
        
        # Verificar se há quantidade suficiente no almoxarifado
        if item.localizacao != 'almoxarifado' or item.quantidade < quantidade:
            flash('Quantidade insuficiente no almoxarifado ou item não está no almoxarifado!', 'error')
            return redirect(url_for('transferir_item'))
        
        # Criar registro de movimentação
        movimentacao = Movimentacao(
            item_id=item_id,
            tipo='transferencia',
            origem='almoxarifado',
            destino='farmacia',
            quantidade=quantidade,
            motivo=motivo,
            responsavel=responsavel,
            observacoes=observacoes
        )
        
        # Atualizar quantidades
        item.quantidade -= quantidade
        
        # Verificar se já existe o item na farmácia
        item_farmacia = Item.query.filter_by(
            nome=item.nome,
            setor=item.setor,
            localizacao='farmacia',
            lote=item.lote
        ).first()
        
        if item_farmacia:
            item_farmacia.quantidade += quantidade
        else:
            # Criar novo item na farmácia
            novo_item = Item(
                nome=item.nome,
                descricao=item.descricao,
                setor=item.setor,
                localizacao='farmacia',
                quantidade=quantidade,
                data_compra=item.data_compra,
                data_vencimento=item.data_vencimento,
                preco_unitario=item.preco_unitario,
                fornecedor=item.fornecedor,
                lote=item.lote,
                foto=item.foto
            )
            db.session.add(novo_item)
        
        db.session.add(movimentacao)
        db.session.commit()
        
        flash(f'Transferência realizada com sucesso! {quantidade} unidades de {item.nome} transferidas para a farmácia.', 'success')
        return redirect(url_for('transferir_item'))
    
    # GET - Mostrar formulário
    itens_almoxarifado = Item.query.filter_by(localizacao='almoxarifado').filter(Item.quantidade > 0).all()
    return render_template('transferir.html', itens=itens_almoxarifado)

# Rota para saída de itens da farmácia para setores
@app.route('/saida', methods=['GET', 'POST'])
def saida_item():
    if request.method == 'POST':
        item_id = request.form['item_id']
        quantidade = int(request.form['quantidade'])
        destino = request.form['destino']
        responsavel = request.form['responsavel']
        motivo = request.form.get('motivo', '')
        observacoes = request.form.get('observacoes', '')
        
        item = Item.query.get_or_404(item_id)
        
        # Verificar se há quantidade suficiente na farmácia
        if item.localizacao != 'farmacia' or item.quantidade < quantidade:
            flash('Quantidade insuficiente na farmácia ou item não está na farmácia!', 'error')
            return redirect(url_for('saida_item'))
        
        # Criar registro de movimentação
        movimentacao = Movimentacao(
            item_id=item_id,
            tipo='saida',
            origem='farmacia',
            destino=destino,
            quantidade=quantidade,
            motivo=motivo,
            responsavel=responsavel,
            observacoes=observacoes
        )
        
        # Atualizar quantidade na farmácia
        item.quantidade -= quantidade
        
        db.session.add(movimentacao)
        db.session.commit()
        
        flash(f'Saída registrada com sucesso! {quantidade} unidades de {item.nome} enviadas para {destino}.', 'success')
        return redirect(url_for('saida_item'))
    
    # GET - Mostrar formulário
    itens_farmacia = Item.query.filter_by(localizacao='farmacia').filter(Item.quantidade > 0).all()
    setores = ['enfermagem', 'laboratorio', 'centro_cirurgico']
    return render_template('saida.html', itens=itens_farmacia, setores=setores)

# Rota para relatório de movimentações
@app.route('/movimentacoes')
def relatorio_movimentacoes():
    movimentacoes = Movimentacao.query.order_by(Movimentacao.data_movimentacao.desc()).all()
    return render_template('movimentacoes.html', movimentacoes=movimentacoes)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API para obter estatísticas em JSON
@app.route('/api/estatisticas')
def api_estatisticas():
    total_almoxarifado = db.session.query(db.func.sum(Item.quantidade)).filter_by(localizacao='almoxarifado').scalar() or 0
    total_farmacia = db.session.query(db.func.sum(Item.quantidade)).filter_by(localizacao='farmacia').scalar() or 0
    
    setores = ['enfermagem', 'farmacia', 'laboratorio', 'centro_cirurgico']
    estatisticas_setor = {}
    
    for setor in setores:
        almox = db.session.query(db.func.sum(Item.quantidade)).filter_by(setor=setor, localizacao='almoxarifado').scalar() or 0
        farm = db.session.query(db.func.sum(Item.quantidade)).filter_by(setor=setor, localizacao='farmacia').scalar() or 0
        estatisticas_setor[setor] = {'almoxarifado': almox, 'farmacia': farm, 'total': almox + farm}
    
    return jsonify({
        'total_almoxarifado': total_almoxarifado,
        'total_farmacia': total_farmacia,
        'total_geral': total_almoxarifado + total_farmacia,
        'por_setor': estatisticas_setor
    })

# Rotas para Planejamento de Compras
@app.route('/planejamento')
@requires_solicitation_access
def planejamento_compras():
    """Página principal do planejamento de compras"""
    # Buscar solicitações pendentes por setor
    solicitacoes = SolicitacaoCompra.query.filter_by(status='aguardando_autorizacao').order_by(SolicitacaoCompra.data_necessidade.asc()).all()
    
    # Estatísticas por setor
    setores = ['enfermagem', 'farmacia', 'laboratorio', 'centro_cirurgico']
    estatisticas_setor = {}
    
    for setor in setores:
        total_solicitacoes = SolicitacaoCompra.query.filter_by(setor=setor, status='pendente').count()
        urgentes = SolicitacaoCompra.query.filter_by(setor=setor, status='pendente', prioridade='urgente').count()
        estatisticas_setor[setor] = {
            'total': total_solicitacoes,
            'urgentes': urgentes
        }
    
    return render_template('planejamento.html', 
                         solicitacoes=solicitacoes,
                         estatisticas_setor=estatisticas_setor)

def gerar_protocolo():
    """Gera um protocolo único para a solicitação"""
    import random
    import string
    
    while True:
        # Formato: SOL + ano + 6 dígitos aleatórios
        ano = datetime.now().year
        codigo = ''.join(random.choices(string.digits, k=6))
        protocolo = f"SOL{ano}{codigo}"
        
        # Verificar se já existe
        existe = SolicitacaoCompra.query.filter_by(protocolo=protocolo).first()
        if not existe:
            return protocolo

@app.route('/planejamento/solicitar', methods=['GET', 'POST'])
@requires_solicitation_access
def solicitar_compra():
    """Formulário para solicitar compras por setor"""
    if request.method == 'POST':
        protocolo = gerar_protocolo()
        
        nova_solicitacao = SolicitacaoCompra(
            protocolo=protocolo,
            setor=request.form['setor'],
            item_nome=request.form['item_nome'],
            descricao=request.form.get('descricao', ''),
            quantidade_solicitada=int(request.form['quantidade_solicitada']),
            prioridade=request.form['prioridade'],
            justificativa=request.form.get('justificativa', ''),
            data_necessidade=datetime.strptime(request.form['data_necessidade'], '%Y-%m-%d').date(),
            solicitante=request.form['solicitante'],
            cargo_solicitante=request.form.get('cargo_solicitante', ''),
            observacoes=request.form.get('observacoes', '')
        )
        
        try:
            db.session.add(nova_solicitacao)
            db.session.commit()
            flash(f'Solicitação criada com sucesso! Protocolo: {protocolo}', 'success')
            return redirect(url_for('planejamento_compras'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar solicitação: {str(e)}', 'error')
    
    return render_template('solicitar_compra.html')

@app.route('/planejamento/analise')
def analise_consumo():
    """Página de análise de consumo e sugestões de compra"""
    # Buscar itens com baixo estoque
    itens_baixo_estoque = Item.query.filter(Item.quantidade <= 10).all()
    
    # Calcular consumo médio dos últimos 3 meses
    from datetime import timedelta
    tres_meses_atras = date.today() - timedelta(days=90)
    
    analises = []
    for item in Item.query.all():
        # Calcular consumo baseado nas movimentações de saída
        movimentacoes_saida = Movimentacao.query.filter(
            Movimentacao.item_id == item.id,
            Movimentacao.tipo == 'saida',
            Movimentacao.data_movimentacao >= tres_meses_atras
        ).all()
        
        consumo_total = sum(mov.quantidade for mov in movimentacoes_saida)
        consumo_medio_mensal = consumo_total / 3 if consumo_total > 0 else 0
        
        # Sugerir estoque mínimo (2 meses de consumo)
        estoque_minimo_sugerido = int(consumo_medio_mensal * 2)
        
        # Sugerir compra se estoque atual < estoque mínimo
        sugestao_compra = max(0, estoque_minimo_sugerido - item.quantidade)
        
        if consumo_medio_mensal > 0 or item.quantidade <= 10:
            analises.append({
                'item': item.to_dict(),
                'consumo_medio_mensal': round(consumo_medio_mensal, 2),
                'estoque_minimo_sugerido': estoque_minimo_sugerido,
                'sugestao_compra': sugestao_compra,
                'status': 'crítico' if item.quantidade <= 5 else 'baixo' if item.quantidade <= 10 else 'normal'
            })
    
    return render_template('analise_consumo.html', 
                         analises=analises,
                         itens_baixo_estoque=itens_baixo_estoque)

@app.route('/planejamento/aprovar/<int:id>', methods=['POST'])
def aprovar_solicitacao(id):
    """Aprovar uma solicitação de compra"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    solicitacao.status = 'aprovada'
    solicitacao.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Solicitação de {solicitacao.item_nome} aprovada!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('planejamento_compras'))

@app.route('/planejamento/rejeitar/<int:id>', methods=['POST'])
def rejeitar_solicitacao(id):
    """Rejeitar uma solicitação de compra"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    solicitacao.status = 'rejeitada'
    solicitacao.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Solicitação de {solicitacao.item_nome} rejeitada!', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('planejamento_compras'))

# Novas rotas para o fluxo de autorização e validação
@app.route('/autorizacao')
@requires_role(['admin', 'tecnico'])
def painel_autorizacao():
    """Painel para responsáveis técnicos autorizarem solicitações"""
    solicitacoes_pendentes = SolicitacaoCompra.query.filter_by(status='aguardando_autorizacao').order_by(SolicitacaoCompra.data_solicitacao.desc()).all()
    return render_template('painel_autorizacao.html', solicitacoes=solicitacoes_pendentes)

@app.route('/autorizacao/autorizar/<int:id>', methods=['POST'])
def autorizar_solicitacao(id):
    """Autorizar uma solicitação pelo responsável técnico"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    
    if solicitacao.status != 'aguardando_autorizacao':
        flash('Esta solicitação não pode ser autorizada no momento.', 'error')
        return redirect(url_for('painel_autorizacao'))
    
    solicitacao.responsavel_tecnico = request.form['responsavel_tecnico']
    solicitacao.cargo_responsavel = request.form['cargo_responsavel']
    solicitacao.observacoes_tecnico = request.form.get('observacoes_tecnico', '')
    solicitacao.data_autorizacao = datetime.utcnow()
    solicitacao.status = 'aguardando_validacao'
    
    try:
        db.session.commit()
        flash(f'Solicitação {solicitacao.protocolo} autorizada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao autorizar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('painel_autorizacao'))

@app.route('/autorizacao/rejeitar/<int:id>', methods=['POST'])
def rejeitar_autorizacao(id):
    """Rejeitar uma solicitação pelo responsável técnico"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    
    if solicitacao.status != 'aguardando_autorizacao':
        flash('Esta solicitação não pode ser rejeitada no momento.', 'error')
        return redirect(url_for('painel_autorizacao'))
    
    solicitacao.responsavel_tecnico = request.form['responsavel_tecnico']
    solicitacao.cargo_responsavel = request.form['cargo_responsavel']
    solicitacao.observacoes_tecnico = request.form.get('observacoes_tecnico', '')
    solicitacao.data_autorizacao = datetime.utcnow()
    solicitacao.status = 'rejeitada_tecnico'
    
    try:
        db.session.commit()
        flash(f'Solicitação {solicitacao.protocolo} rejeitada pelo responsável técnico.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('painel_autorizacao'))

@app.route('/validacao')
@requires_role(['admin', 'secretaria'])
def painel_validacao():
    """Painel para secretárias validarem solicitações autorizadas"""
    solicitacoes_autorizadas = SolicitacaoCompra.query.filter_by(status='aguardando_validacao').order_by(SolicitacaoCompra.data_autorizacao.desc()).all()
    return render_template('painel_validacao.html', solicitacoes=solicitacoes_autorizadas)

@app.route('/validacao/validar/<int:id>', methods=['POST'])
def validar_solicitacao(id):
    """Validar uma solicitação pela secretária"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    
    if solicitacao.status != 'aguardando_validacao':
        flash('Esta solicitação não pode ser validada no momento.', 'error')
        return redirect(url_for('painel_validacao'))
    
    solicitacao.secretaria_validador = request.form['secretaria_validador']
    solicitacao.observacoes_secretaria = request.form.get('observacoes_secretaria', '')
    solicitacao.data_validacao = datetime.utcnow()
    solicitacao.status = 'aprovada'
    
    try:
        db.session.commit()
        flash(f'Solicitação {solicitacao.protocolo} validada e aprovada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao validar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('painel_validacao'))

@app.route('/validacao/rejeitar/<int:id>', methods=['POST'])
def rejeitar_validacao(id):
    """Rejeitar uma solicitação pela secretária"""
    solicitacao = SolicitacaoCompra.query.get_or_404(id)
    
    if solicitacao.status != 'aguardando_validacao':
        flash('Esta solicitação não pode ser rejeitada no momento.', 'error')
        return redirect(url_for('painel_validacao'))
    
    solicitacao.secretaria_validador = request.form['secretaria_validador']
    solicitacao.observacoes_secretaria = request.form.get('observacoes_secretaria', '')
    solicitacao.data_validacao = datetime.utcnow()
    solicitacao.status = 'rejeitada_secretaria'
    
    try:
        db.session.commit()
        flash(f'Solicitação {solicitacao.protocolo} rejeitada pela secretária.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar solicitação: {str(e)}', 'error')
    
    return redirect(url_for('painel_validacao'))

# Rotas para Recebimento e Conferência
@app.route('/recebimento')
@requires_role(['admin', 'secretaria', 'operador'])
def painel_recebimento():
    """Painel para recebimento e conferência de pedidos"""
    solicitacoes_aprovadas = SolicitacaoCompra.query.filter_by(status='aprovada').order_by(SolicitacaoCompra.data_validacao.desc()).all()
    recebimentos_pendentes = RecebimentoPedido.query.filter_by(status_conferencia='pendente').order_by(RecebimentoPedido.data_recebimento.desc()).all()
    return render_template('painel_recebimento.html', solicitacoes=solicitacoes_aprovadas, recebimentos=recebimentos_pendentes)

@app.route('/recebimento/novo/<int:solicitacao_id>', methods=['GET', 'POST'])
def novo_recebimento(solicitacao_id):
    """Criar novo recebimento para uma solicitação aprovada"""
    solicitacao = SolicitacaoCompra.query.get_or_404(solicitacao_id)
    
    if solicitacao.status != 'aprovada':
        flash('Esta solicitação não pode ser recebida no momento.', 'error')
        return redirect(url_for('painel_recebimento'))
    
    if request.method == 'POST':
        # Criar recebimento
        recebimento = RecebimentoPedido(
            solicitacao_id=solicitacao.id,
            numero_nota_fiscal=request.form['numero_nota_fiscal'],
            fornecedor=request.form['fornecedor'],
            data_nota_fiscal=datetime.strptime(request.form['data_nota_fiscal'], '%Y-%m-%d'),
            valor_total=float(request.form['valor_total']),
            responsavel_recebimento=request.form['responsavel_recebimento'],
            observacoes=request.form.get('observacoes', ''),
            status_conferencia='pendente'
        )
        
        try:
            db.session.add(recebimento)
            db.session.flush()  # Para obter o ID do recebimento
            
            # Criar item de recebimento
            item_recebimento = ItemRecebimento(
                recebimento_id=recebimento.id,
                item_nome=solicitacao.item_nome,
                quantidade_solicitada=solicitacao.quantidade_solicitada,
                quantidade_recebida=int(request.form['quantidade_recebida']),
                valor_unitario=float(request.form['valor_unitario']),
                lote=request.form.get('lote', ''),
                data_validade=datetime.strptime(request.form['data_validade'], '%Y-%m-%d') if request.form.get('data_validade') else None,
                observacoes_item=request.form.get('observacoes_item', '')
            )
            
            db.session.add(item_recebimento)
            db.session.commit()
            
            flash(f'Recebimento criado com sucesso! Protocolo: {recebimento.protocolo_recebimento}', 'success')
            return redirect(url_for('conferir_recebimento', id=recebimento.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar recebimento: {str(e)}', 'error')
    
    return render_template('novo_recebimento.html', solicitacao=solicitacao)

@app.route('/recebimento/conferir/<int:id>', methods=['GET', 'POST'])
def conferir_recebimento(id):
    """Conferir um recebimento pendente"""
    recebimento = RecebimentoPedido.query.get_or_404(id)
    
    if request.method == 'POST':
        acao = request.form['acao']
        
        if acao == 'aprovar':
            recebimento.status_conferencia = 'conferido'
            recebimento.data_conferencia = datetime.utcnow()
            recebimento.responsavel_conferencia = request.form['responsavel_conferencia']
            recebimento.observacoes_conferencia = request.form.get('observacoes_conferencia', '')
            
            # Atualizar estoque para cada item recebido
            for item_recebimento in recebimento.itens:
                item_estoque = Item.query.filter_by(nome=item_recebimento.item_nome).first()
                if item_estoque:
                    item_estoque.quantidade_almoxarifado += item_recebimento.quantidade_recebida
                    
                    # Criar movimentação de entrada
                    movimentacao = Movimentacao(
                        item_id=item_estoque.id,
                        tipo='entrada',
                        quantidade=item_recebimento.quantidade_recebida,
                        origem='recebimento',
                        destino='almoxarifado',
                        responsavel=recebimento.responsavel_conferencia,
                        observacoes=f'Recebimento NF: {recebimento.numero_nota_fiscal}'
                    )
                    db.session.add(movimentacao)
            
            # Atualizar status da solicitação
            recebimento.solicitacao.status = 'recebida'
            
            flash(f'Recebimento {recebimento.protocolo_recebimento} aprovado e estoque atualizado!', 'success')
            
        elif acao == 'rejeitar':
            recebimento.status_conferencia = 'divergencia'
            recebimento.data_conferencia = datetime.utcnow()
            recebimento.responsavel_conferencia = request.form['responsavel_conferencia']
            recebimento.observacoes_conferencia = request.form.get('observacoes_conferencia', '')
            
            flash(f'Recebimento {recebimento.protocolo_recebimento} rejeitado.', 'warning')
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar conferência: {str(e)}', 'error')
        
        return redirect(url_for('painel_recebimento'))
    
    return render_template('conferir_recebimento.html', recebimento=recebimento)

@app.route('/recebimento/relatorio')
def relatorio_recebimentos():
    """Relatório de recebimentos"""
    recebimentos = RecebimentoPedido.query.order_by(RecebimentoPedido.data_recebimento.desc()).all()
    return render_template('relatorio_recebimentos.html', recebimentos=recebimentos)

def inicializar_sistema():
    """Inicializa o banco de dados e cria usuários padrão se necessário"""
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se já existem usuários
        if User.query.count() == 0:
            print("Criando usuários padrão...")
            
            usuarios_padrao = [
                {
                    'username': 'admin',
                    'email': 'admin@hospital-angicos.gov.br',
                    'nome_completo': 'Administrador do Sistema',
                    'cargo': 'admin',
                    'setor': 'administracao',
                    'password': 'admin123'
                },
                {
                    'username': 'enfermeiro1',
                    'email': 'enfermeiro@hospital-angicos.gov.br',
                    'nome_completo': 'Maria Silva Santos',
                    'cargo': 'tecnico',
                    'setor': 'enfermagem',
                    'password': 'enf123'
                },
                {
                    'username': 'farmaceutico1',
                    'email': 'farmaceutico@hospital-angicos.gov.br',
                    'nome_completo': 'João Carlos Oliveira',
                    'cargo': 'tecnico',
                    'setor': 'farmacia',
                    'password': 'farm123'
                },
                {
                    'username': 'secretaria1',
                    'email': 'secretaria@hospital-angicos.gov.br',
                    'nome_completo': 'Ana Paula Costa',
                    'cargo': 'secretaria',
                    'setor': 'administracao',
                    'password': 'sec123'
                },
                {
                    'username': 'operador1',
                    'email': 'operador@hospital-angicos.gov.br',
                    'nome_completo': 'Carlos Eduardo Lima',
                    'cargo': 'operador',
                    'setor': 'almoxarifado',
                    'password': 'op123'
                }
            ]
            
            for user_data in usuarios_padrao:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    nome_completo=user_data['nome_completo'],
                    cargo=user_data['cargo'],
                    setor=user_data['setor']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                print(f"✓ Usuário criado: {user_data['nome_completo']} ({user_data['username']})")
            
            db.session.commit()
            
            print("\n=== CREDENCIAIS DE ACESSO ===")
            print("Administrador:")
            print("  Usuário: admin")
            print("  Senha: admin123")
            print("\nEnfermeiro (Técnico):")
            print("  Usuário: enfermeiro1")
            print("  Senha: enf123")
            print("\nFarmacêutico (Técnico):")
            print("  Usuário: farmaceutico1")
            print("  Senha: farm123")
            print("\nSecretária:")
            print("  Usuário: secretaria1")
            print("  Senha: sec123")
            print("\nOperador:")
            print("  Usuário: operador1")
            print("  Senha: op123")
            print("\n⚠️  IMPORTANTE: Altere as senhas padrão após o primeiro login!")
        else:
            print(f"Sistema já inicializado com {User.query.count()} usuários.")

if __name__ == '__main__':
    inicializar_sistema()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)