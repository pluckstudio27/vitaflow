"""
Modelo MongoDB para categorias de produtos
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId
from .base import BaseMongoModel


class CategoriaProdutoMongo(BaseMongoModel):
    """Modelo MongoDB para categorias de produtos"""
    
    collection_name = 'categorias_produtos'
    
    def __init__(self, **kwargs):
        # Validações específicas da categoria
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome da categoria é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('cor_identificacao', '#007bff')  # Azul padrão
        kwargs.setdefault('icone', 'fas fa-box')  # Ícone padrão
        kwargs.setdefault('ordem_exibicao', 0)
        kwargs.setdefault('permite_estoque_negativo', False)
        kwargs.setdefault('requer_lote', False)
        kwargs.setdefault('requer_validade', False)
        kwargs.setdefault('dias_alerta_vencimento', 30)
        kwargs.setdefault('estoque_minimo_padrao', 0)
        kwargs.setdefault('estoque_maximo_padrao', 0)
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def cor_identificacao(self):
        return self.data.get('cor_identificacao', '#007bff')
    
    @property
    def icone(self):
        return self.data.get('icone', 'fas fa-box')
    
    @property
    def ordem_exibicao(self):
        return self.data.get('ordem_exibicao', 0)
    
    @property
    def permite_estoque_negativo(self):
        return self.data.get('permite_estoque_negativo', False)
    
    @property
    def requer_lote(self):
        return self.data.get('requer_lote', False)
    
    @property
    def requer_validade(self):
        return self.data.get('requer_validade', False)
    
    @property
    def dias_alerta_vencimento(self):
        return self.data.get('dias_alerta_vencimento', 30)
    
    @property
    def estoque_minimo_padrao(self):
        return self.data.get('estoque_minimo_padrao', 0)
    
    @property
    def estoque_maximo_padrao(self):
        return self.data.get('estoque_maximo_padrao', 0)
    
    @property
    def categoria_pai_id(self):
        return self.data.get('categoria_pai_id')
    
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def configuracoes_especiais(self):
        return self.data.get('configuracoes_especiais', {})
    
    def get_subcategorias(self) -> List['CategoriaProdutoMongo']:
        """Retorna as subcategorias desta categoria"""
        return self.find_many({'categoria_pai_id': str(self._id), 'ativo': True})
    
    def get_categoria_pai(self) -> Optional['CategoriaProdutoMongo']:
        """Retorna a categoria pai, se existir"""
        if not self.categoria_pai_id:
            return None
        return self.find_by_id(self.categoria_pai_id)
    
    def get_hierarquia_completa(self) -> List[str]:
        """Retorna a hierarquia completa da categoria (nomes)"""
        hierarquia = [self.nome]
        categoria_atual = self
        
        while categoria_atual.categoria_pai_id:
            categoria_pai = categoria_atual.get_categoria_pai()
            if categoria_pai:
                hierarquia.insert(0, categoria_pai.nome)
                categoria_atual = categoria_pai
            else:
                break
        
        return hierarquia
    
    def get_path_hierarquia(self) -> str:
        """Retorna o path da hierarquia separado por '/'"""
        return ' / '.join(self.get_hierarquia_completa())
    
    def get_nivel_hierarquia(self) -> int:
        """Retorna o nível na hierarquia (0 = raiz)"""
        nivel = 0
        categoria_atual = self
        
        while categoria_atual.categoria_pai_id:
            categoria_pai = categoria_atual.get_categoria_pai()
            if categoria_pai:
                nivel += 1
                categoria_atual = categoria_pai
            else:
                break
        
        return nivel
    
    def pode_ser_pai_de(self, categoria_id: str) -> bool:
        """Verifica se esta categoria pode ser pai de outra (evita loops)"""
        if str(self._id) == categoria_id:
            return False
        
        # Verifica se a categoria não é descendente desta
        categoria_candidata = self.find_by_id(categoria_id)
        if not categoria_candidata:
            return True
        
        hierarquia_candidata = categoria_candidata.get_hierarquia_completa()
        return self.nome not in hierarquia_candidata
    
    def get_produtos_count(self) -> int:
        """Retorna o número de produtos nesta categoria"""
        from .produto import ProdutoMongo
        return ProdutoMongo.count({'categoria_id': str(self._id), 'ativo': True})
    
    def get_produtos_count_recursivo(self) -> int:
        """Retorna o número de produtos nesta categoria e subcategorias"""
        count = self.get_produtos_count()
        
        for subcategoria in self.get_subcategorias():
            count += subcategoria.get_produtos_count_recursivo()
        
        return count
    
    def tem_produtos(self) -> bool:
        """Verifica se a categoria tem produtos associados"""
        return self.get_produtos_count() > 0
    
    def pode_ser_excluida(self) -> bool:
        """Verifica se a categoria pode ser excluída"""
        # Não pode excluir se tem produtos
        if self.tem_produtos():
            return False
        
        # Não pode excluir se tem subcategorias
        if len(self.get_subcategorias()) > 0:
            return False
        
        return True
    
    @classmethod
    def find_by_nome(cls, nome: str, central_id: str = None) -> Optional['CategoriaProdutoMongo']:
        """Encontra categoria pelo nome"""
        filter_dict = {'nome': nome}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_one(filter_dict)
    
    @classmethod
    def find_ativas(cls, central_id: str = None) -> List['CategoriaProdutoMongo']:
        """Retorna todas as categorias ativas"""
        filter_dict = {'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict, sort=[('ordem_exibicao', 1), ('nome', 1)])
    
    @classmethod
    def find_raizes(cls, central_id: str = None) -> List['CategoriaProdutoMongo']:
        """Retorna categorias raiz (sem pai)"""
        filter_dict = {'categoria_pai_id': None, 'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict, sort=[('ordem_exibicao', 1), ('nome', 1)])
    
    @classmethod
    def find_subcategorias(cls, categoria_pai_id: str) -> List['CategoriaProdutoMongo']:
        """Retorna subcategorias de uma categoria pai"""
        return cls.find_many(
            {'categoria_pai_id': categoria_pai_id, 'ativo': True},
            sort=[('ordem_exibicao', 1), ('nome', 1)]
        )
    
    @classmethod
    def get_arvore_categorias(cls, central_id: str = None) -> List[Dict[str, Any]]:
        """Retorna a árvore completa de categorias"""
        def build_tree(categoria_pai_id=None):
            filter_dict = {'categoria_pai_id': categoria_pai_id, 'ativo': True}
            if central_id:
                filter_dict['central_id'] = central_id
            
            categorias = cls.find_many(filter_dict, sort=[('ordem_exibicao', 1), ('nome', 1)])
            tree = []
            
            for categoria in categorias:
                categoria_dict = categoria.to_dict()
                categoria_dict['subcategorias'] = build_tree(str(categoria._id))
                categoria_dict['produtos_count'] = categoria.get_produtos_count()
                categoria_dict['produtos_count_recursivo'] = categoria.get_produtos_count_recursivo()
                tree.append(categoria_dict)
            
            return tree
        
        return build_tree()
    
    @classmethod
    def reordenar_categorias(cls, categoria_ids: List[str]):
        """Reordena as categorias baseado na lista de IDs"""
        for i, categoria_id in enumerate(categoria_ids):
            categoria = cls.find_by_id(categoria_id)
            if categoria:
                categoria.data['ordem_exibicao'] = i
                categoria.save()
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index([('nome', 1), ('central_id', 1)], unique=True)
        
        # Índices compostos para performance
        collection.create_index([('ativo', 1), ('ordem_exibicao', 1)])
        collection.create_index([('categoria_pai_id', 1), ('ativo', 1)])
        collection.create_index([('central_id', 1), ('ativo', 1)])
        collection.create_index('data_criacao')
    
    def to_dict_with_hierarchy(self) -> Dict[str, Any]:
        """Converte para dicionário incluindo informações de hierarquia"""
        result = self.to_dict()
        result['hierarquia_completa'] = self.get_hierarquia_completa()
        result['path_hierarquia'] = self.get_path_hierarquia()
        result['nivel_hierarquia'] = self.get_nivel_hierarquia()
        result['produtos_count'] = self.get_produtos_count()
        result['pode_ser_excluida'] = self.pode_ser_excluida()
        return result


class ConfiguracaoCategoriaMongo(BaseMongoModel):
    """Modelo MongoDB para configurações específicas de categoria por local"""
    
    collection_name = 'configuracoes_categoria'
    
    def __init__(self, **kwargs):
        # Validações
        if 'categoria_id' not in kwargs:
            raise ValueError("categoria_id é obrigatório")
        if 'local_id' not in kwargs:
            raise ValueError("local_id é obrigatório")
        if 'tipo_local' not in kwargs:
            raise ValueError("tipo_local é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('estoque_minimo', 0)
        kwargs.setdefault('estoque_maximo', 0)
        kwargs.setdefault('permite_estoque_negativo', None)  # None = usar padrão da categoria
        kwargs.setdefault('dias_alerta_vencimento', None)  # None = usar padrão da categoria
        kwargs.setdefault('ativo', True)
        
        super().__init__(**kwargs)
    
    @property
    def categoria_id(self):
        return self.data.get('categoria_id')
    
    @property
    def local_id(self):
        return self.data.get('local_id')
    
    @property
    def tipo_local(self):
        return self.data.get('tipo_local')  # 'almoxarifado', 'sub_almoxarifado', 'setor'
    
    @property
    def estoque_minimo(self):
        return self.data.get('estoque_minimo', 0)
    
    @property
    def estoque_maximo(self):
        return self.data.get('estoque_maximo', 0)
    
    @property
    def permite_estoque_negativo(self):
        return self.data.get('permite_estoque_negativo')
    
    @property
    def dias_alerta_vencimento(self):
        return self.data.get('dias_alerta_vencimento')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @classmethod
    def find_by_categoria_local(cls, categoria_id: str, local_id: str, 
                               tipo_local: str) -> Optional['ConfiguracaoCategoriaMongo']:
        """Encontra configuração por categoria e local"""
        return cls.find_one({
            'categoria_id': categoria_id,
            'local_id': local_id,
            'tipo_local': tipo_local
        })
    
    @classmethod
    def find_by_categoria(cls, categoria_id: str) -> List['ConfiguracaoCategoriaMongo']:
        """Encontra todas as configurações de uma categoria"""
        return cls.find_many({'categoria_id': categoria_id, 'ativo': True})
    
    @classmethod
    def find_by_local(cls, local_id: str, tipo_local: str) -> List['ConfiguracaoCategoriaMongo']:
        """Encontra todas as configurações de um local"""
        return cls.find_many({
            'local_id': local_id,
            'tipo_local': tipo_local,
            'ativo': True
        })
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índice único composto
        collection.create_index([
            ('categoria_id', 1),
            ('local_id', 1),
            ('tipo_local', 1)
        ], unique=True)
        
        # Índices para consultas
        collection.create_index('categoria_id')
        collection.create_index([('local_id', 1), ('tipo_local', 1)])
        collection.create_index('ativo')