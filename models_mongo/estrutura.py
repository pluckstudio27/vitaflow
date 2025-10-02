"""
Modelos MongoDB para estrutura organizacional
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId
from .base import BaseMongoModel


class CentralMongo(BaseMongoModel):
    """Modelo MongoDB para centrais"""
    
    collection_name = 'centrais'
    
    def __init__(self, **kwargs):
        # Validações específicas da central
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome da central é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('endereco', {})
        kwargs.setdefault('contato', {})
        kwargs.setdefault('configuracoes', {})
        kwargs.setdefault('codigo', '')
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def codigo(self):
        return self.data.get('codigo', '')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def endereco(self):
        return self.data.get('endereco', {})
    
    @property
    def contato(self):
        return self.data.get('contato', {})
    
    @property
    def configuracoes(self):
        return self.data.get('configuracoes', {})
    
    def get_almoxarifados(self) -> List['AlmoxarifadoMongo']:
        """Retorna todos os almoxarifados desta central"""
        return AlmoxarifadoMongo.find_many({'central_id': str(self._id), 'ativo': True})
    
    def get_usuarios(self) -> List:
        """Retorna todos os usuários desta central"""
        from .usuario import UsuarioMongo
        return UsuarioMongo.find_many({'central_id': str(self._id), 'ativo': True})
    
    def get_produtos(self) -> List:
        """Retorna todos os produtos desta central"""
        from .produto import ProdutoMongo
        return ProdutoMongo.find_many({'central_id': str(self._id), 'ativo': True})
    
    def get_categorias(self) -> List:
        """Retorna todas as categorias desta central"""
        from .categoria import CategoriaProdutoMongo
        return CategoriaProdutoMongo.find_many({'central_id': str(self._id), 'ativo': True})
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas da central"""
        return {
            'total_almoxarifados': len(self.get_almoxarifados()),
            'total_usuarios': len(self.get_usuarios()),
            'total_produtos': len(self.get_produtos()),
            'total_categorias': len(self.get_categorias())
        }
    
    @classmethod
    def find_by_nome(cls, nome: str) -> Optional['CentralMongo']:
        """Encontra central pelo nome"""
        return cls.find_one({'nome': nome})
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['CentralMongo']:
        """Encontra central pelo código"""
        return cls.find_one({'codigo': codigo})
    
    @classmethod
    def find_ativas(cls) -> List['CentralMongo']:
        """Retorna todas as centrais ativas"""
        return cls.find_many({'ativo': True}, sort=[('nome', 1)])
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index('nome', unique=True)
        collection.create_index('codigo', unique=True, sparse=True)
        
        # Índices para consultas
        collection.create_index('ativo')
        collection.create_index('data_criacao')


class AlmoxarifadoMongo(BaseMongoModel):
    """Modelo MongoDB para almoxarifados"""
    
    collection_name = 'almoxarifados'
    
    def __init__(self, **kwargs):
        # Validações específicas do almoxarifado
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome do almoxarifado é obrigatório")
        if 'central_id' not in kwargs:
            raise ValueError("central_id é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('endereco', {})
        kwargs.setdefault('contato', {})
        kwargs.setdefault('configuracoes', {})
        kwargs.setdefault('codigo', '')
        kwargs.setdefault('tipo', 'geral')  # geral, farmacia, manutencao, etc.
        kwargs.setdefault('capacidade_maxima', 0)
        kwargs.setdefault('area_m2', 0.0)
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def codigo(self):
        return self.data.get('codigo', '')
    
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def tipo(self):
        return self.data.get('tipo', 'geral')
    
    @property
    def endereco(self):
        return self.data.get('endereco', {})
    
    @property
    def contato(self):
        return self.data.get('contato', {})
    
    @property
    def configuracoes(self):
        return self.data.get('configuracoes', {})
    
    @property
    def capacidade_maxima(self):
        return self.data.get('capacidade_maxima', 0)
    
    @property
    def area_m2(self):
        return float(self.data.get('area_m2', 0.0))
    
    def get_central(self) -> Optional['CentralMongo']:
        """Retorna a central deste almoxarifado"""
        return CentralMongo.find_by_id(self.central_id)
    
    def get_sub_almoxarifados(self) -> List['SubAlmoxarifadoMongo']:
        """Retorna todos os sub-almoxarifados deste almoxarifado"""
        return SubAlmoxarifadoMongo.find_many({'almoxarifado_id': str(self._id), 'ativo': True})
    
    def get_usuarios(self) -> List:
        """Retorna todos os usuários deste almoxarifado"""
        from .usuario import UsuarioMongo
        return UsuarioMongo.find_many({'almoxarifado_id': str(self._id), 'ativo': True})
    
    def get_estoque_produtos(self) -> List:
        """Retorna o estoque de produtos deste almoxarifado"""
        from .produto import EstoqueProdutoMongo
        return EstoqueProdutoMongo.find_many({
            'local_id': str(self._id),
            'tipo_local': 'almoxarifado',
            'ativo': True
        })
    
    def get_movimentacoes(self, limit: int = 50) -> List:
        """Retorna as movimentações deste almoxarifado"""
        from .produto import MovimentacaoProdutoMongo
        return MovimentacaoProdutoMongo.find_by_local(str(self._id), 'almoxarifado', limit)
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do almoxarifado"""
        return {
            'total_sub_almoxarifados': len(self.get_sub_almoxarifados()),
            'total_usuarios': len(self.get_usuarios()),
            'total_produtos_estoque': len(self.get_estoque_produtos())
        }
    
    @classmethod
    def find_by_nome_central(cls, nome: str, central_id: str) -> Optional['AlmoxarifadoMongo']:
        """Encontra almoxarifado pelo nome dentro de uma central"""
        return cls.find_one({'nome': nome, 'central_id': central_id})
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['AlmoxarifadoMongo']:
        """Encontra almoxarifado pelo código"""
        return cls.find_one({'codigo': codigo})
    
    @classmethod
    def find_by_central(cls, central_id: str) -> List['AlmoxarifadoMongo']:
        """Retorna todos os almoxarifados de uma central"""
        return cls.find_many({'central_id': central_id, 'ativo': True}, sort=[('nome', 1)])
    
    @classmethod
    def find_by_tipo(cls, tipo: str, central_id: str = None) -> List['AlmoxarifadoMongo']:
        """Retorna almoxarifados por tipo"""
        filter_dict = {'tipo': tipo, 'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict, sort=[('nome', 1)])
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index([('nome', 1), ('central_id', 1)], unique=True)
        collection.create_index('codigo', unique=True, sparse=True)
        
        # Índices para consultas
        collection.create_index([('central_id', 1), ('ativo', 1)])
        collection.create_index([('tipo', 1), ('ativo', 1)])
        collection.create_index('data_criacao')


class SubAlmoxarifadoMongo(BaseMongoModel):
    """Modelo MongoDB para sub-almoxarifados"""
    
    collection_name = 'sub_almoxarifados'
    
    def __init__(self, **kwargs):
        # Validações específicas do sub-almoxarifado
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome do sub-almoxarifado é obrigatório")
        if 'almoxarifado_id' not in kwargs:
            raise ValueError("almoxarifado_id é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('localizacao', '')
        kwargs.setdefault('configuracoes', {})
        kwargs.setdefault('codigo', '')
        kwargs.setdefault('tipo', 'geral')
        kwargs.setdefault('capacidade_maxima', 0)
        kwargs.setdefault('area_m2', 0.0)
        kwargs.setdefault('temperatura_controlada', False)
        kwargs.setdefault('umidade_controlada', False)
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def codigo(self):
        return self.data.get('codigo', '')
    
    @property
    def almoxarifado_id(self):
        return self.data.get('almoxarifado_id')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def tipo(self):
        return self.data.get('tipo', 'geral')
    
    @property
    def localizacao(self):
        return self.data.get('localizacao', '')
    
    @property
    def configuracoes(self):
        return self.data.get('configuracoes', {})
    
    @property
    def capacidade_maxima(self):
        return self.data.get('capacidade_maxima', 0)
    
    @property
    def area_m2(self):
        return float(self.data.get('area_m2', 0.0))
    
    @property
    def temperatura_controlada(self):
        return self.data.get('temperatura_controlada', False)
    
    @property
    def umidade_controlada(self):
        return self.data.get('umidade_controlada', False)
    
    def get_almoxarifado(self) -> Optional['AlmoxarifadoMongo']:
        """Retorna o almoxarifado deste sub-almoxarifado"""
        return AlmoxarifadoMongo.find_by_id(self.almoxarifado_id)
    
    def get_central(self) -> Optional['CentralMongo']:
        """Retorna a central através do almoxarifado"""
        almoxarifado = self.get_almoxarifado()
        return almoxarifado.get_central() if almoxarifado else None
    
    def get_usuarios(self) -> List:
        """Retorna todos os usuários deste sub-almoxarifado"""
        from .usuario import UsuarioMongo
        return UsuarioMongo.find_many({'sub_almoxarifado_id': str(self._id), 'ativo': True})
    
    def get_estoque_produtos(self) -> List:
        """Retorna o estoque de produtos deste sub-almoxarifado"""
        from .produto import EstoqueProdutoMongo
        return EstoqueProdutoMongo.find_many({
            'local_id': str(self._id),
            'tipo_local': 'sub_almoxarifado',
            'ativo': True
        })
    
    def get_movimentacoes(self, limit: int = 50) -> List:
        """Retorna as movimentações deste sub-almoxarifado"""
        from .produto import MovimentacaoProdutoMongo
        return MovimentacaoProdutoMongo.find_by_local(str(self._id), 'sub_almoxarifado', limit)
    
    def get_path_completo(self) -> str:
        """Retorna o path completo: Central / Almoxarifado / Sub-Almoxarifado"""
        almoxarifado = self.get_almoxarifado()
        if not almoxarifado:
            return self.nome
        
        central = almoxarifado.get_central()
        if not central:
            return f"{almoxarifado.nome} / {self.nome}"
        
        return f"{central.nome} / {almoxarifado.nome} / {self.nome}"
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do sub-almoxarifado"""
        return {
            'total_usuarios': len(self.get_usuarios()),
            'total_produtos_estoque': len(self.get_estoque_produtos())
        }
    
    @classmethod
    def find_by_nome_almoxarifado(cls, nome: str, almoxarifado_id: str) -> Optional['SubAlmoxarifadoMongo']:
        """Encontra sub-almoxarifado pelo nome dentro de um almoxarifado"""
        return cls.find_one({'nome': nome, 'almoxarifado_id': almoxarifado_id})
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['SubAlmoxarifadoMongo']:
        """Encontra sub-almoxarifado pelo código"""
        return cls.find_one({'codigo': codigo})
    
    @classmethod
    def find_by_almoxarifado(cls, almoxarifado_id: str) -> List['SubAlmoxarifadoMongo']:
        """Retorna todos os sub-almoxarifados de um almoxarifado"""
        return cls.find_many({'almoxarifado_id': almoxarifado_id, 'ativo': True}, sort=[('nome', 1)])
    
    @classmethod
    def find_by_tipo(cls, tipo: str, almoxarifado_id: str = None) -> List['SubAlmoxarifadoMongo']:
        """Retorna sub-almoxarifados por tipo"""
        filter_dict = {'tipo': tipo, 'ativo': True}
        if almoxarifado_id:
            filter_dict['almoxarifado_id'] = almoxarifado_id
        return cls.find_many(filter_dict, sort=[('nome', 1)])
    
    @classmethod
    def find_temperatura_controlada(cls, almoxarifado_id: str = None) -> List['SubAlmoxarifadoMongo']:
        """Retorna sub-almoxarifados com temperatura controlada"""
        filter_dict = {'temperatura_controlada': True, 'ativo': True}
        if almoxarifado_id:
            filter_dict['almoxarifado_id'] = almoxarifado_id
        return cls.find_many(filter_dict, sort=[('nome', 1)])
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index([('nome', 1), ('almoxarifado_id', 1)], unique=True)
        collection.create_index('codigo', unique=True, sparse=True)
        
        # Índices para consultas
        collection.create_index([('almoxarifado_id', 1), ('ativo', 1)])
        collection.create_index([('tipo', 1), ('ativo', 1)])
        collection.create_index([('temperatura_controlada', 1), ('ativo', 1)])
        collection.create_index([('umidade_controlada', 1), ('ativo', 1)])
        collection.create_index('data_criacao')


class SetorMongo(BaseMongoModel):
    """Modelo MongoDB para setores (locais que consomem produtos)"""
    
    collection_name = 'setores'
    
    def __init__(self, **kwargs):
        # Validações específicas do setor
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome do setor é obrigatório")
        if 'central_id' not in kwargs:
            raise ValueError("central_id é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('tipo', 'administrativo')  # administrativo, clinico, manutencao, etc.
        kwargs.setdefault('responsavel', '')
        kwargs.setdefault('contato', {})
        kwargs.setdefault('configuracoes', {})
        kwargs.setdefault('codigo', '')
        kwargs.setdefault('permite_estoque', False)  # Se o setor pode manter estoque próprio
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def codigo(self):
        return self.data.get('codigo', '')
    
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def tipo(self):
        return self.data.get('tipo', 'administrativo')
    
    @property
    def responsavel(self):
        return self.data.get('responsavel', '')
    
    @property
    def contato(self):
        return self.data.get('contato', {})
    
    @property
    def configuracoes(self):
        return self.data.get('configuracoes', {})
    
    @property
    def permite_estoque(self):
        return self.data.get('permite_estoque', False)
    
    def get_central(self) -> Optional['CentralMongo']:
        """Retorna a central deste setor"""
        return CentralMongo.find_by_id(self.central_id)
    
    def get_usuarios(self) -> List:
        """Retorna todos os usuários deste setor"""
        from .usuario import UsuarioMongo
        return UsuarioMongo.find_many({'setor_id': str(self._id), 'ativo': True})
    
    def get_estoque_produtos(self) -> List:
        """Retorna o estoque de produtos deste setor (se permitir estoque)"""
        if not self.permite_estoque:
            return []
        
        from .produto import EstoqueProdutoMongo
        return EstoqueProdutoMongo.find_many({
            'local_id': str(self._id),
            'tipo_local': 'setor',
            'ativo': True
        })
    
    def get_movimentacoes(self, limit: int = 50) -> List:
        """Retorna as movimentações deste setor"""
        from .produto import MovimentacaoProdutoMongo
        return MovimentacaoProdutoMongo.find_by_local(str(self._id), 'setor', limit)
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do setor"""
        return {
            'total_usuarios': len(self.get_usuarios()),
            'total_produtos_estoque': len(self.get_estoque_produtos()) if self.permite_estoque else 0
        }
    
    @classmethod
    def find_by_nome_central(cls, nome: str, central_id: str) -> Optional['SetorMongo']:
        """Encontra setor pelo nome dentro de uma central"""
        return cls.find_one({'nome': nome, 'central_id': central_id})
    
    @classmethod
    def find_by_codigo(cls, codigo: str) -> Optional['SetorMongo']:
        """Encontra setor pelo código"""
        return cls.find_one({'codigo': codigo})
    
    @classmethod
    def find_by_central(cls, central_id: str) -> List['SetorMongo']:
        """Retorna todos os setores de uma central"""
        return cls.find_many({'central_id': central_id, 'ativo': True}, sort=[('nome', 1)])
    
    @classmethod
    def find_by_tipo(cls, tipo: str, central_id: str = None) -> List['SetorMongo']:
        """Retorna setores por tipo"""
        filter_dict = {'tipo': tipo, 'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict, sort=[('nome', 1)])
    
    @classmethod
    def find_com_estoque(cls, central_id: str = None) -> List['SetorMongo']:
        """Retorna setores que permitem estoque"""
        filter_dict = {'permite_estoque': True, 'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict, sort=[('nome', 1)])
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index([('nome', 1), ('central_id', 1)], unique=True)
        collection.create_index('codigo', unique=True, sparse=True)
        
        # Índices para consultas
        collection.create_index([('central_id', 1), ('ativo', 1)])
        collection.create_index([('tipo', 1), ('ativo', 1)])
        collection.create_index([('permite_estoque', 1), ('ativo', 1)])
        collection.create_index('data_criacao')