from datetime import datetime
from extensions import db

class CategoriaProduto(db.Model):
    """Modelo para Categoria de Produto - permite gerenciamento por usuário"""
    __tablename__ = 'categorias_produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text)
    codigo = db.Column(db.String(10), nullable=False, unique=True, index=True)  # Ex: MH, OD, IN
    cor = db.Column(db.String(7), default='#007bff')  # Cor hexadecimal para identificação visual
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    produtos = db.relationship('Produto', foreign_keys='Produto.categoria_id', backref='categoria_obj', lazy=True, overlaps="categoria_produto")
    usuarios = db.relationship('Usuario', foreign_keys='Usuario.categoria_id', backref='categoria_gerenciada', lazy=True, overlaps="categoria")
    
    # Índices
    __table_args__ = (
        db.Index('idx_categoria_nome_ativo', 'nome', 'ativo'),
        db.Index('idx_categoria_codigo_ativo', 'codigo', 'ativo'),
    )
    
    def __repr__(self):
        return f'<CategoriaProduto {self.codigo} - {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'codigo': self.codigo,
            'cor': self.cor,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'total_produtos': self.get_total_produtos(),
            'total_usuarios': self.get_total_usuarios()
        }
    
    def get_total_produtos(self):
        """Retorna o total de produtos ativos nesta categoria"""
        from models.produto import Produto
        return Produto.query.filter_by(categoria_id=self.id, ativo=True).count()
    
    def get_total_usuarios(self):
        """Retorna o total de usuários que gerenciam esta categoria"""
        from models.usuario import Usuario
        return Usuario.query.filter_by(categoria_id=self.id, ativo=True).count()
    
    @staticmethod
    def get_categorias_ativas():
        """Retorna todas as categorias ativas ordenadas por nome"""
        return CategoriaProduto.query.filter_by(ativo=True).order_by(CategoriaProduto.nome).all()
    
    @staticmethod
    def get_active_categories():
        """Alias para get_categorias_ativas - compatibilidade com templates"""
        return CategoriaProduto.get_categorias_ativas()
    
    @staticmethod
    def criar_categorias_padrao():
        """Cria categorias padrão do sistema"""
        categorias_padrao = [
            {
                'nome': 'Material Hospitalar',
                'codigo': 'MH',
                'descricao': 'Materiais e equipamentos para uso hospitalar',
                'cor': '#28a745'
            },
            {
                'nome': 'Material Odontológico', 
                'codigo': 'OD',
                'descricao': 'Materiais e equipamentos odontológicos',
                'cor': '#17a2b8'
            },
            {
                'nome': 'Medicamentos Injetáveis',
                'codigo': 'IN',
                'descricao': 'Medicamentos para aplicação injetável',
                'cor': '#dc3545'
            },
            {
                'nome': 'Medicamentos Orais',
                'codigo': 'MD',
                'descricao': 'Medicamentos para uso oral',
                'cor': '#fd7e14'
            },
            {
                'nome': 'Material de Limpeza',
                'codigo': 'LP',
                'descricao': 'Produtos de limpeza e higienização',
                'cor': '#6f42c1'
            },
            {
                'nome': 'Gênero Expediente',
                'codigo': 'GE',
                'descricao': 'Material de escritório e expediente',
                'cor': '#20c997'
            },
            {
                'nome': 'Material Gráfico',
                'codigo': 'GR',
                'descricao': 'Materiais gráficos e impressos',
                'cor': '#ffc107'
            },
            {
                'nome': 'Equipamentos',
                'codigo': 'EQ',
                'descricao': 'Equipamentos e instrumentos',
                'cor': '#6c757d'
            },
            {
                'nome': 'Material de Laboratório',
                'codigo': 'LB',
                'descricao': 'Materiais para laboratório',
                'cor': '#e83e8c'
            }
        ]
        
        for cat_data in categorias_padrao:
            categoria_existente = CategoriaProduto.query.filter_by(codigo=cat_data['codigo']).first()
            if not categoria_existente:
                categoria = CategoriaProduto(
                    nome=cat_data['nome'],
                    codigo=cat_data['codigo'],
                    descricao=cat_data['descricao'],
                    cor=cat_data['cor']
                )
                db.session.add(categoria)
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar categorias padrão: {e}")
            return False