from datetime import datetime
from extensions import db

class Central(db.Model):
    """Modelo para Central - nível mais alto da hierarquia"""
    __tablename__ = 'centrais'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    almoxarifados = db.relationship('Almoxarifado', backref='central', lazy=True, cascade='all, delete-orphan')
    
    # Índices compostos para otimizar consultas comuns
    __table_args__ = (
        db.Index('idx_central_ativo_nome', 'ativo', 'nome'),
        db.Index('idx_central_data_criacao_ativo', 'data_criacao', 'ativo'),
    )
    
    def __repr__(self):
        return f'<Central {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'total_almoxarifados': len([a for a in self.almoxarifados if a.ativo])
        }

class Almoxarifado(db.Model):
    """Modelo para Almoxarifado - segundo nível da hierarquia"""
    __tablename__ = 'almoxarifados'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Chave estrangeira
    central_id = db.Column(db.Integer, db.ForeignKey('centrais.id'), nullable=False, index=True)
    
    # Relacionamentos
    sub_almoxarifados = db.relationship('SubAlmoxarifado', backref='almoxarifado', lazy=True, cascade='all, delete-orphan')
    
    # Constraints e índices para otimizar consultas
    __table_args__ = (
        db.UniqueConstraint('nome', 'central_id', name='uq_almoxarifado_nome_central'),
        db.Index('idx_almoxarifado_central_ativo', 'central_id', 'ativo'),
        db.Index('idx_almoxarifado_ativo_nome', 'ativo', 'nome'),
        db.Index('idx_almoxarifado_data_criacao_central', 'data_criacao', 'central_id'),
    )
    
    def __repr__(self):
        return f'<Almoxarifado {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'central_id': self.central_id,
            'central_nome': self.central.nome if self.central else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'total_sub_almoxarifados': len([s for s in self.sub_almoxarifados if s.ativo])
        }

class SubAlmoxarifado(db.Model):
    """Modelo para Sub-Almoxarifado - terceiro nível da hierarquia"""
    __tablename__ = 'sub_almoxarifados'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Chave estrangeira
    almoxarifado_id = db.Column(db.Integer, db.ForeignKey('almoxarifados.id'), nullable=False, index=True)
    
    # Relacionamentos
    setores = db.relationship('Setor', backref='sub_almoxarifado', lazy=True, cascade='all, delete-orphan')
    
    # Constraints e índices para otimizar consultas
    __table_args__ = (
        db.UniqueConstraint('nome', 'almoxarifado_id', name='uq_sub_almoxarifado_nome_almoxarifado'),
        db.Index('idx_sub_almoxarifado_almoxarifado_ativo', 'almoxarifado_id', 'ativo'),
        db.Index('idx_sub_almoxarifado_ativo_nome', 'ativo', 'nome'),
        db.Index('idx_sub_almoxarifado_data_criacao_almoxarifado', 'data_criacao', 'almoxarifado_id'),
    )
    
    def __repr__(self):
        return f'<SubAlmoxarifado {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'almoxarifado_id': self.almoxarifado_id,
            'almoxarifado_nome': self.almoxarifado.nome if self.almoxarifado else None,
            'central_nome': self.almoxarifado.central.nome if self.almoxarifado and self.almoxarifado.central else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'total_setores': len([s for s in self.setores if s.ativo])
        }

class Setor(db.Model):
    """Modelo para Setor - quarto nível da hierarquia"""
    __tablename__ = 'setores'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Chave estrangeira
    sub_almoxarifado_id = db.Column(db.Integer, db.ForeignKey('sub_almoxarifados.id'), nullable=False, index=True)
    
    # Constraints e índices para otimizar consultas
    __table_args__ = (
        db.UniqueConstraint('nome', 'sub_almoxarifado_id', name='uq_setor_nome_sub_almoxarifado'),
        db.Index('idx_setor_sub_almoxarifado_ativo', 'sub_almoxarifado_id', 'ativo'),
        db.Index('idx_setor_ativo_nome', 'ativo', 'nome'),
        db.Index('idx_setor_data_criacao_sub_almoxarifado', 'data_criacao', 'sub_almoxarifado_id'),
    )
    
    def __repr__(self):
        return f'<Setor {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'sub_almoxarifado_id': self.sub_almoxarifado_id,
            'sub_almoxarifado_nome': self.sub_almoxarifado.nome if self.sub_almoxarifado else None,
            'almoxarifado_nome': self.sub_almoxarifado.almoxarifado.nome if self.sub_almoxarifado and self.sub_almoxarifado.almoxarifado else None,
            'central_nome': self.sub_almoxarifado.almoxarifado.central.nome if self.sub_almoxarifado and self.sub_almoxarifado.almoxarifado and self.sub_almoxarifado.almoxarifado.central else None,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }