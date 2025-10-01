from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class Usuario(UserMixin, db.Model):
    """Modelo para usuários do sistema com controle hierárquico de acesso"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nome_completo = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Nível de acesso hierárquico
    nivel_acesso = db.Column(db.Enum(
        'super_admin',      # Acesso total ao sistema
        'admin_central',    # Administrador de uma central específica
        'gerente_almox',    # Gerente de um almoxarifado específico
        'resp_sub_almox',   # Responsável por um sub-almoxarifado específico
        'operador_setor',   # Operador de um setor específico
        name='nivel_acesso_enum'
    ), nullable=False, index=True)
    
    # Relacionamentos hierárquicos (apenas um será preenchido baseado no nível)
    central_id = db.Column(db.Integer, db.ForeignKey('centrais.id'), nullable=True, index=True)
    almoxarifado_id = db.Column(db.Integer, db.ForeignKey('almoxarifados.id'), nullable=True, index=True)
    sub_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('sub_almoxarifados.id'), nullable=True, index=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True, index=True)
    
    # Categoria de produtos que o usuário pode gerenciar
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_produtos.id'), nullable=True, index=True)
    
    # Status e auditoria
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    central = db.relationship('Central', foreign_keys=[central_id], lazy='select')
    almoxarifado = db.relationship('Almoxarifado', foreign_keys=[almoxarifado_id], lazy='select')
    sub_almoxarifado = db.relationship('SubAlmoxarifado', foreign_keys=[sub_almoxarifado_id], lazy='select')
    setor = db.relationship('Setor', foreign_keys=[setor_id], lazy='select')
    # categoria_gerenciada é definido como backref no modelo CategoriaProduto
    
    # Relacionamento many-to-many com categorias específicas
    categorias_especificas = db.relationship(
        'CategoriaProduto',
        secondary='usuario_categorias',
        backref=db.backref('usuarios_especificos', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Índices compostos para otimizar consultas
    __table_args__ = (
        db.Index('idx_usuario_nivel_ativo', 'nivel_acesso', 'ativo'),
        db.Index('idx_usuario_central_ativo', 'central_id', 'ativo'),
        db.Index('idx_usuario_almoxarifado_ativo', 'almoxarifado_id', 'ativo'),
        db.Index('idx_usuario_sub_almoxarifado_ativo', 'sub_almoxarifado_id', 'ativo'),
        db.Index('idx_usuario_setor_ativo', 'setor_id', 'ativo'),
        # Constraint para garantir que o relacionamento hierárquico seja consistente com o nível de acesso
        db.CheckConstraint(
            '(nivel_acesso = \'super_admin\' AND central_id IS NULL AND almoxarifado_id IS NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NULL) OR '
            '(nivel_acesso = \'admin_central\' AND central_id IS NOT NULL AND almoxarifado_id IS NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NULL) OR '
            '(nivel_acesso = \'gerente_almox\' AND almoxarifado_id IS NOT NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NULL) OR '
            '(nivel_acesso = \'resp_sub_almox\' AND sub_almoxarifado_id IS NOT NULL AND setor_id IS NULL) OR '
            '(nivel_acesso = \'operador_setor\' AND setor_id IS NOT NULL)',
            name='check_nivel_acesso_hierarquia'
        ),
    )
    
    def __repr__(self):
        return f'<Usuario {self.username} - {self.nivel_acesso}>'
    
    def set_password(self, password):
        """Define a senha do usuário com hash seguro"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica se a senha fornecida está correta"""
        return check_password_hash(self.password_hash, password)
    
    def get_scope_name(self):
        """Retorna o nome do escopo de acesso do usuário"""
        if self.nivel_acesso == 'super_admin':
            return 'Sistema Completo'
        elif self.nivel_acesso == 'admin_central':
            return f'Central: {self.central.nome}' if self.central else 'Central não definida'
        elif self.nivel_acesso == 'gerente_almox':
            return f'Almoxarifado: {self.almoxarifado.nome}' if self.almoxarifado else 'Almoxarifado não definido'
        elif self.nivel_acesso == 'resp_sub_almox':
            return f'Sub-Almoxarifado: {self.sub_almoxarifado.nome}' if self.sub_almoxarifado else 'Sub-Almoxarifado não definido'
        elif self.nivel_acesso == 'operador_setor':
            return f'Setor: {self.setor.nome}' if self.setor else 'Setor não definido'
        return 'Escopo não definido'
    
    def get_hierarchy_path(self):
        """Retorna o caminho hierárquico completo do usuário"""
        if self.nivel_acesso == 'super_admin':
            return 'Sistema'
        elif self.nivel_acesso == 'admin_central' and self.central:
            return f'{self.central.nome}'
        elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado:
            return f'{self.almoxarifado.central.nome} > {self.almoxarifado.nome}'
        elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado:
            return f'{self.sub_almoxarifado.almoxarifado.central.nome} > {self.sub_almoxarifado.almoxarifado.nome} > {self.sub_almoxarifado.nome}'
        elif self.nivel_acesso == 'operador_setor' and self.setor:
            return f'{self.setor.sub_almoxarifado.almoxarifado.central.nome} > {self.setor.sub_almoxarifado.almoxarifado.nome} > {self.setor.sub_almoxarifado.nome} > {self.setor.nome}'
        return 'Hierarquia não definida'
    
    def can_access_central(self, central_id):
        """Verifica se o usuário pode acessar uma central específica"""
        if self.nivel_acesso == 'super_admin':
            return True
        elif self.nivel_acesso == 'admin_central':
            return self.central_id == central_id
        elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado:
            return self.almoxarifado.central_id == central_id
        elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado:
            return self.sub_almoxarifado.almoxarifado.central_id == central_id
        elif self.nivel_acesso == 'operador_setor' and self.setor:
            return self.setor.sub_almoxarifado.almoxarifado.central_id == central_id
        return False
    
    def can_access_almoxarifado(self, almoxarifado_id):
        """Verifica se o usuário pode acessar um almoxarifado específico"""
        if self.nivel_acesso == 'super_admin':
            return True
        elif self.nivel_acesso == 'admin_central' and self.central:
            # Admin de central pode acessar todos os almoxarifados da central
            from models.hierarchy import Almoxarifado
            almox = Almoxarifado.query.get(almoxarifado_id)
            return almox and almox.central_id == self.central_id
        elif self.nivel_acesso == 'gerente_almox':
            return self.almoxarifado_id == almoxarifado_id
        elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado:
            return self.sub_almoxarifado.almoxarifado_id == almoxarifado_id
        elif self.nivel_acesso == 'operador_setor' and self.setor:
            return self.setor.sub_almoxarifado.almoxarifado_id == almoxarifado_id
        return False
    
    def can_access_sub_almoxarifado(self, sub_almoxarifado_id):
        """Verifica se o usuário pode acessar um sub-almoxarifado específico"""
        if self.nivel_acesso == 'super_admin':
            return True
        elif self.nivel_acesso == 'admin_central' and self.central:
            # Admin de central pode acessar todos os sub-almoxarifados da central
            from models.hierarchy import SubAlmoxarifado
            sub_almox = SubAlmoxarifado.query.get(sub_almoxarifado_id)
            return sub_almox and sub_almox.almoxarifado.central_id == self.central_id
        elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado:
            # Gerente de almoxarifado pode acessar todos os sub-almoxarifados do almoxarifado
            from models.hierarchy import SubAlmoxarifado
            sub_almox = SubAlmoxarifado.query.get(sub_almoxarifado_id)
            return sub_almox and sub_almox.almoxarifado_id == self.almoxarifado_id
        elif self.nivel_acesso == 'resp_sub_almox':
            return self.sub_almoxarifado_id == sub_almoxarifado_id
        elif self.nivel_acesso == 'operador_setor' and self.setor:
            return self.setor.sub_almoxarifado_id == sub_almoxarifado_id
        return False
    
    def can_access_setor(self, setor_id):
        """Verifica se o usuário pode acessar um setor específico"""
        if self.nivel_acesso == 'super_admin':
            return True
        elif self.nivel_acesso == 'admin_central' and self.central:
            # Admin de central pode acessar todos os setores da central
            from models.hierarchy import Setor
            setor = Setor.query.get(setor_id)
            return setor and setor.sub_almoxarifado.almoxarifado.central_id == self.central_id
        elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado:
            # Gerente de almoxarifado pode acessar todos os setores do almoxarifado
            from models.hierarchy import Setor
            setor = Setor.query.get(setor_id)
            return setor and setor.sub_almoxarifado.almoxarifado_id == self.almoxarifado_id
        elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado:
            # Responsável de sub-almoxarifado pode acessar todos os setores do sub-almoxarifado
            from models.hierarchy import Setor
            setor = Setor.query.get(setor_id)
            return setor and setor.sub_almoxarifado_id == self.sub_almoxarifado_id
        elif self.nivel_acesso == 'operador_setor':
            return self.setor_id == setor_id
        return False
    
    def pode_gerenciar_categoria(self, categoria_id):
        """Verifica se o usuário pode gerenciar uma categoria específica"""
        # Super admin e admin geral podem gerenciar todas as categorias
        if self.nivel_acesso in ['super_admin', 'admin_geral']:
            return True
        
        # Se tem categoria_id definida (todas as categorias), pode gerenciar qualquer uma
        if self.categoria_id is None:
            return True
        
        # Se tem categoria_id específica, só pode gerenciar essa
        if self.categoria_id == categoria_id:
            return True
        
        # Verifica se está nas categorias específicas do usuário
        return self.categorias_especificas.filter_by(id=categoria_id).first() is not None
    
    def get_categorias_permitidas(self):
        """Retorna lista de IDs das categorias que o usuário pode gerenciar"""
        # Super admin e admin geral podem gerenciar todas as categorias
        if self.nivel_acesso in ['super_admin', 'admin_geral']:
            return None  # None significa todas as categorias
        
        # Se tem categoria_id None (todas as categorias)
        if self.categoria_id is None:
            return None
        
        categorias_ids = []
        
        # Adiciona a categoria principal se existir
        if self.categoria_id:
            categorias_ids.append(self.categoria_id)
        
        # Adiciona as categorias específicas
        for categoria in self.categorias_especificas:
            if categoria.id not in categorias_ids:
                categorias_ids.append(categoria.id)
        
        return categorias_ids if categorias_ids else None
    
    def adicionar_categoria_especifica(self, categoria_id):
        """Adiciona uma categoria específica ao usuário"""
        from models.categoria import CategoriaProduto
        categoria = CategoriaProduto.query.get(categoria_id)
        if categoria and not self.categorias_especificas.filter_by(id=categoria_id).first():
            self.categorias_especificas.append(categoria)
            return True
        return False
    
    def remover_categoria_especifica(self, categoria_id):
        """Remove uma categoria específica do usuário"""
        categoria = self.categorias_especificas.filter_by(id=categoria_id).first()
        if categoria:
            self.categorias_especificas.remove(categoria)
            return True
        return False
    
    def get_categorias_display(self):
        """Retorna uma representação das categorias para exibição na interface"""
        # Se é super admin ou admin central, tem acesso a todas
        if self.nivel_acesso in ['super_admin', 'admin_central']:
            return {'tipo': 'todas', 'texto': 'Todas', 'categorias': []}
        
        # Busca categorias específicas
        categorias_especificas = list(self.categorias_especificas)
        
        if not categorias_especificas:
            # Se não tem categorias específicas, verifica se tem categoria principal
            if self.categoria_gerenciada:
                return {
                    'tipo': 'principal', 
                    'texto': f'{self.categoria_gerenciada.codigo}', 
                    'categorias': [self.categoria_gerenciada]
                }
            else:
                # Se não tem nem específicas nem principal, é "Todas" (apenas para admins)
                return {'tipo': 'todas', 'texto': 'Todas', 'categorias': []}
        
        # Tem categorias específicas
        if len(categorias_especificas) == 1:
            cat = categorias_especificas[0]
            return {
                'tipo': 'especifica', 
                'texto': f'{cat.codigo}', 
                'categorias': categorias_especificas
            }
        else:
            # Múltiplas categorias específicas
            return {
                'tipo': 'multiplas', 
                'texto': f'{len(categorias_especificas)} categorias', 
                'categorias': categorias_especificas
            }
    
    def to_dict(self):
        """Converte o usuário para dicionário"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nome': self.nome_completo,  # Mapeia nome_completo para nome para compatibilidade com API
            'nome_completo': self.nome_completo,
            'nivel_acesso': self.nivel_acesso,
            'escopo': self.get_scope_name(),
            'hierarquia': self.get_hierarchy_path(),
            'ativo': self.ativo,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'central_id': self.central_id,
            'almoxarifado_id': self.almoxarifado_id,
            'sub_almoxarifado_id': self.sub_almoxarifado_id,
            'setor_id': self.setor_id,
            'categoria_id': self.categoria_id,
            'categoria': {
                'id': self.categoria_gerenciada.id,
                'nome': self.categoria_gerenciada.nome,
                'codigo': self.categoria_gerenciada.codigo,
                'cor': self.categoria_gerenciada.cor
            } if self.categoria_gerenciada else None,
            'categorias_especificas': [
                {
                    'id': cat.id,
                    'nome': cat.nome,
                    'codigo': cat.codigo,
                    'cor': cat.cor
                } for cat in self.categorias_especificas
            ],
            'categorias_permitidas': self.get_categorias_permitidas()
        }

class LogAuditoria(db.Model):
    """Modelo para logs de auditoria do sistema"""
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    acao = db.Column(db.String(100), nullable=False, index=True)  # LOGIN, LOGOUT, CREATE, UPDATE, DELETE
    tabela = db.Column(db.String(50), nullable=True, index=True)  # Nome da tabela afetada
    registro_id = db.Column(db.Integer, nullable=True, index=True)  # ID do registro afetado
    dados_anteriores = db.Column(db.Text, nullable=True)  # JSON dos dados antes da alteração
    dados_novos = db.Column(db.Text, nullable=True)  # JSON dos dados após a alteração
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 ou IPv6
    user_agent = db.Column(db.Text, nullable=True)
    data_acao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relacionamento
    usuario = db.relationship('Usuario', backref='logs_auditoria', lazy='select')
    
    # Índices compostos
    __table_args__ = (
        db.Index('idx_auditoria_usuario_data', 'usuario_id', 'data_acao'),
        db.Index('idx_auditoria_acao_data', 'acao', 'data_acao'),
        db.Index('idx_auditoria_tabela_data', 'tabela', 'data_acao'),
    )
    
    def __repr__(self):
        return f'<LogAuditoria {self.usuario.username} - {self.acao} - {self.data_acao}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario.nome_completo if self.usuario else None,
            'acao': self.acao,
            'tabela': self.tabela,
            'registro_id': self.registro_id,
            'ip_address': self.ip_address,
            'data_acao': self.data_acao.isoformat() if self.data_acao else None
        }