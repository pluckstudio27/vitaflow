"""
Modelo para relacionamento many-to-many entre Usuario e Categoria
"""
from extensions import db

class UsuarioCategoria(db.Model):
    """
    Tabela de relacionamento many-to-many entre Usuario e CategoriaProduto
    Permite que um usuário gerencie múltiplas categorias específicas
    """
    __tablename__ = 'usuario_categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_produtos.id'), nullable=False, index=True)
    
    # Índices compostos para performance
    __table_args__ = (
        db.Index('idx_usuario_categoria_unique', 'usuario_id', 'categoria_id', unique=True),
        db.Index('idx_usuario_categoria_usuario', 'usuario_id'),
        db.Index('idx_usuario_categoria_categoria', 'categoria_id'),
    )
    
    def __repr__(self):
        return f'<UsuarioCategoria usuario_id={self.usuario_id} categoria_id={self.categoria_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'categoria_id': self.categoria_id
        }