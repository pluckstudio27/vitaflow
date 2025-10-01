from datetime import datetime, date
from sqlalchemy import func, Numeric
from extensions import db

class Produto(db.Model):
    """Modelo para Produto - cadastrado na Central"""
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    central_id = db.Column(db.Integer, db.ForeignKey('centrais.id'), nullable=False, index=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    descricao = db.Column(db.Text)
    unidade_medida = db.Column(db.String(10), nullable=False)  # UN, KG, L, etc.
    categoria = db.Column(db.String(100), index=True)  # Mantido para compatibilidade
    subcategoria = db.Column(db.String(100), index=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_produtos.id'), nullable=True, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    # categoria_obj é definido como backref no modelo CategoriaProduto
    estoques = db.relationship('EstoqueProduto', backref='produto', lazy=True, cascade='all, delete-orphan')
    movimentacoes = db.relationship('MovimentacaoProduto', backref='produto', lazy=True, cascade='all, delete-orphan')
    lotes = db.relationship('LoteProduto', backref='produto', lazy=True, cascade='all, delete-orphan')
    
    # Índices compostos
    __table_args__ = (
        db.Index('idx_produto_central_ativo', 'central_id', 'ativo'),
        db.Index('idx_produto_categoria_ativo', 'categoria', 'ativo'),
        db.Index('idx_produto_categoria_id_ativo', 'categoria_id', 'ativo'),
        db.Index('idx_produto_codigo_central', 'codigo', 'central_id'),
    )
    
    def __repr__(self):
        return f'<Produto {self.codigo} - {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nome': self.nome,
            'descricao': self.descricao,
            'unidade_medida': self.unidade_medida,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'categoria_id': self.categoria_id,
            'categoria_obj': {
                'id': self.categoria_obj.id,
                'nome': self.categoria_obj.nome,
                'codigo': self.categoria_obj.codigo,
                'cor': self.categoria_obj.cor
            } if self.categoria_obj else None,
            'ativo': self.ativo,
            'central_id': self.central_id,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'estoque_total': self.get_estoque_total()
        }
    
    def get_estoque_total(self):
        """Retorna o estoque total do produto em todos os níveis"""
        total = db.session.query(func.sum(EstoqueProduto.quantidade)).filter(
            EstoqueProduto.produto_id == self.id,
            EstoqueProduto.ativo == True
        ).scalar()
        return total or 0

class EstoqueProduto(db.Model):
    """Modelo para controle de estoque por localização na hierarquia"""
    __tablename__ = 'estoque_produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    quantidade = db.Column(Numeric(10, 3), nullable=False, default=0)
    quantidade_reservada = db.Column(Numeric(10, 3), nullable=False, default=0)
    quantidade_disponivel = db.Column(Numeric(10, 3), nullable=False, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Chaves estrangeiras
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False, index=True)
    
    # Localização na hierarquia (apenas uma deve estar preenchida)
    # Central não armazena produtos - é apenas organizacional
    almoxarifado_id = db.Column(db.Integer, db.ForeignKey('almoxarifados.id'), nullable=True, index=True)
    sub_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('sub_almoxarifados.id'), nullable=True, index=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True, index=True)
    
    # Relacionamentos
    lotes = db.relationship('LoteProduto', backref='estoque', lazy=True)
    
    # Relacionamentos para hierarquia
    almoxarifado = db.relationship('Almoxarifado', foreign_keys=[almoxarifado_id], lazy='select')
    sub_almoxarifado = db.relationship('SubAlmoxarifado', foreign_keys=[sub_almoxarifado_id], lazy='select')
    setor = db.relationship('Setor', foreign_keys=[setor_id], lazy='select')
    
    # Índices compostos
    __table_args__ = (
        db.Index('idx_estoque_produto_almoxarifado', 'produto_id', 'almoxarifado_id'),
        db.Index('idx_estoque_produto_sub_almoxarifado', 'produto_id', 'sub_almoxarifado_id'),
        db.Index('idx_estoque_produto_setor', 'produto_id', 'setor_id'),
        db.CheckConstraint(
            '(almoxarifado_id IS NOT NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NULL) OR '
            '(almoxarifado_id IS NULL AND sub_almoxarifado_id IS NOT NULL AND setor_id IS NULL) OR '
            '(almoxarifado_id IS NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NOT NULL)',
            name='check_single_location'
        ),
    )
    
    def __repr__(self):
        location = self.get_location_name()
        return f'<EstoqueProduto {self.produto.codigo} - {location}: {self.quantidade}>'
    
    def get_location_name(self):
        """Retorna o nome da localização do estoque"""
        if self.almoxarifado_id and self.almoxarifado:
            return f"Almoxarifado: {self.almoxarifado.nome}"
        elif self.sub_almoxarifado_id and self.sub_almoxarifado:
            return f"Sub-Almoxarifado: {self.sub_almoxarifado.nome}"
        elif self.setor_id and self.setor:
            return f"Setor: {self.setor.nome}"
        elif self.almoxarifado_id:
            return f"Almoxarifado (ID: {self.almoxarifado_id})"
        elif self.sub_almoxarifado_id:
            return f"Sub-Almoxarifado (ID: {self.sub_almoxarifado_id})"
        elif self.setor_id:
            return f"Setor (ID: {self.setor_id})"
        return "Localização não definida"
    
    def to_dict(self):
        return {
            'id': self.id,
            'produto_id': self.produto_id,
            'quantidade': float(self.quantidade),
            'quantidade_reservada': float(self.quantidade_reservada),
            'quantidade_disponivel': float(self.quantidade_disponivel),
            'ativo': self.ativo,
            'almoxarifado_id': self.almoxarifado_id,
            'sub_almoxarifado_id': self.sub_almoxarifado_id,
            'setor_id': self.setor_id,
            'localizacao': self.get_location_name(),
            'produto': {
                'id': self.produto.id,
                'codigo': self.produto.codigo,
                'nome': self.produto.nome,
                'categoria_id': self.produto.categoria_id,
                'categoria_obj': {
                    'id': self.produto.categoria_obj.id,
                    'nome': self.produto.categoria_obj.nome,
                    'codigo': self.produto.categoria_obj.codigo,
                    'cor': self.produto.categoria_obj.cor
                } if self.produto.categoria_obj else None
            } if self.produto else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }

class LoteProduto(db.Model):
    """Modelo para controle de lotes de produtos"""
    __tablename__ = 'lotes_produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_lote = db.Column(db.String(100), nullable=False, index=True)
    data_fabricacao = db.Column(db.Date, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True, index=True)
    quantidade_inicial = db.Column(Numeric(10, 3), nullable=False)
    quantidade_atual = db.Column(Numeric(10, 3), nullable=False)
    preco_unitario = db.Column(Numeric(10, 2), nullable=True)
    fornecedor = db.Column(db.String(200), nullable=True)
    nota_fiscal = db.Column(db.String(50), nullable=True)
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Chaves estrangeiras
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False, index=True)
    estoque_id = db.Column(db.Integer, db.ForeignKey('estoque_produtos.id'), nullable=False, index=True)
    
    # Índices compostos
    __table_args__ = (
        db.Index('idx_lote_produto_numero', 'produto_id', 'numero_lote'),
        db.Index('idx_lote_vencimento_ativo', 'data_vencimento', 'ativo'),
        db.Index('idx_lote_estoque_ativo', 'estoque_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<LoteProduto {self.numero_lote} - {self.produto.codigo}>'
    
    @property
    def dias_para_vencimento(self):
        """Calcula quantos dias faltam para o vencimento"""
        if not self.data_vencimento:
            return None
        delta = self.data_vencimento - date.today()
        return delta.days
    
    @property
    def status_vencimento(self):
        """Retorna o status do vencimento"""
        dias = self.dias_para_vencimento
        if dias is None:
            return 'sem_data'
        elif dias < 0:
            return 'vencido'
        elif dias <= 30:
            return 'vence_em_breve'
        elif dias <= 90:
            return 'atencao'
        else:
            return 'ok'
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_lote': self.numero_lote,
            'data_fabricacao': self.data_fabricacao.isoformat() if self.data_fabricacao else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'quantidade_inicial': float(self.quantidade_inicial),
            'quantidade_atual': float(self.quantidade_atual),
            'preco_unitario': float(self.preco_unitario) if self.preco_unitario else None,
            'fornecedor': self.fornecedor,
            'nota_fiscal': self.nota_fiscal,
            'observacoes': self.observacoes,
            'ativo': self.ativo,
            'produto_id': self.produto_id,
            'estoque_id': self.estoque_id,
            'dias_para_vencimento': self.dias_para_vencimento,
            'status_vencimento': self.status_vencimento,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }

class MovimentacaoProduto(db.Model):
    """Modelo para registro de movimentações de produtos"""
    __tablename__ = 'movimentacoes_produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo_movimentacao = db.Column(db.String(20), nullable=False, index=True)  # ENTRADA, SAIDA, TRANSFERENCIA
    quantidade = db.Column(Numeric(10, 3), nullable=False)
    motivo = db.Column(db.String(200), nullable=True)
    observacoes = db.Column(db.Text)
    usuario_responsavel = db.Column(db.String(100), nullable=False)
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Chaves estrangeiras
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False, index=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes_produtos.id'), nullable=True, index=True)
    
    # Localização de origem (para transferências e saídas)
    origem_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('almoxarifados.id'), nullable=True, index=True)
    origem_sub_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('sub_almoxarifados.id'), nullable=True, index=True)
    origem_setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True, index=True)
    
    # Localização de destino (para transferências e entradas)
    destino_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('almoxarifados.id'), nullable=True, index=True)
    destino_sub_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('sub_almoxarifados.id'), nullable=True, index=True)
    destino_setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'), nullable=True, index=True)
    
    # Relacionamentos para origem
    origem_almoxarifado = db.relationship('Almoxarifado', foreign_keys=[origem_almoxarifado_id], lazy='select')
    origem_sub_almoxarifado = db.relationship('SubAlmoxarifado', foreign_keys=[origem_sub_almoxarifado_id], lazy='select')
    origem_setor = db.relationship('Setor', foreign_keys=[origem_setor_id], lazy='select')
    
    # Relacionamentos para destino
    destino_almoxarifado = db.relationship('Almoxarifado', foreign_keys=[destino_almoxarifado_id], lazy='select')
    destino_sub_almoxarifado = db.relationship('SubAlmoxarifado', foreign_keys=[destino_sub_almoxarifado_id], lazy='select')
    destino_setor = db.relationship('Setor', foreign_keys=[destino_setor_id], lazy='select')
    
    # Índices compostos
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'produto_id', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
    )
    
    def __repr__(self):
        return f'<MovimentacaoProduto {self.tipo_movimentacao} - {self.produto.codigo}: {self.quantidade}>'
    
    def get_origem_nome(self):
        """Retorna o nome da localização de origem"""
        if self.origem_almoxarifado_id:
            return f"Almoxarifado: {self.origem_almoxarifado.nome}"
        elif self.origem_sub_almoxarifado_id:
            return f"Sub-Almoxarifado: {self.origem_sub_almoxarifado.nome}"
        elif self.origem_setor_id:
            return f"Setor: {self.origem_setor.nome}"
        return "Origem externa"
    
    def get_destino_nome(self):
        """Retorna o nome da localização de destino"""
        if self.destino_almoxarifado_id:
            return f"Almoxarifado: {self.destino_almoxarifado.nome}"
        elif self.destino_sub_almoxarifado_id:
            return f"Sub-Almoxarifado: {self.destino_sub_almoxarifado.nome}"
        elif self.destino_setor_id:
            return f"Setor: {self.destino_setor.nome}"
        return "Destino externo"
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_movimentacao': self.tipo_movimentacao,
            'quantidade': float(self.quantidade),
            'motivo': self.motivo,
            'observacoes': self.observacoes,
            'usuario_responsavel': self.usuario_responsavel,
            'produto_id': self.produto_id,
            'lote_id': self.lote_id,
            'origem': self.get_origem_nome(),
            'destino': self.get_destino_nome(),
            'data_movimentacao': self.data_movimentacao.isoformat() if self.data_movimentacao else None
        }