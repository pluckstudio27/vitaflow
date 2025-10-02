"""
Modelos MongoDB para produtos e controle de estoque
"""
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from decimal import Decimal
from bson import ObjectId
from .base import BaseMongoModel


class ProdutoMongo(BaseMongoModel):
    """Modelo MongoDB para produtos"""
    
    collection_name = 'produtos'
    
    def __init__(self, **kwargs):
        # Validações específicas do produto
        if 'nome' not in kwargs or not kwargs['nome'].strip():
            raise ValueError("Nome do produto é obrigatório")
        if 'categoria_id' not in kwargs:
            raise ValueError("categoria_id é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('descricao', '')
        kwargs.setdefault('unidade_medida', 'UN')
        kwargs.setdefault('codigo_barras', '')
        kwargs.setdefault('codigo_interno', '')
        kwargs.setdefault('marca', '')
        kwargs.setdefault('modelo', '')
        kwargs.setdefault('especificacoes', {})
        kwargs.setdefault('preco_unitario', 0.0)
        kwargs.setdefault('preco_medio', 0.0)
        kwargs.setdefault('estoque_minimo', 0)
        kwargs.setdefault('estoque_maximo', 0)
        kwargs.setdefault('permite_estoque_negativo', False)
        kwargs.setdefault('requer_lote', False)
        kwargs.setdefault('requer_validade', False)
        kwargs.setdefault('dias_alerta_vencimento', 30)
        kwargs.setdefault('observacoes', '')
        kwargs.setdefault('imagens', [])
        kwargs.setdefault('documentos', [])
        
        super().__init__(**kwargs)
    
    @property
    def nome(self):
        return self.data.get('nome')
    
    @property
    def descricao(self):
        return self.data.get('descricao', '')
    
    @property
    def categoria_id(self):
        return self.data.get('categoria_id')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def unidade_medida(self):
        return self.data.get('unidade_medida', 'UN')
    
    @property
    def codigo_barras(self):
        return self.data.get('codigo_barras', '')
    
    @property
    def codigo_interno(self):
        return self.data.get('codigo_interno', '')
    
    @property
    def marca(self):
        return self.data.get('marca', '')
    
    @property
    def modelo(self):
        return self.data.get('modelo', '')
    
    @property
    def especificacoes(self):
        return self.data.get('especificacoes', {})
    
    @property
    def preco_unitario(self):
        return float(self.data.get('preco_unitario', 0.0))
    
    @property
    def preco_medio(self):
        return float(self.data.get('preco_medio', 0.0))
    
    @property
    def estoque_minimo(self):
        return self.data.get('estoque_minimo', 0)
    
    @property
    def estoque_maximo(self):
        return self.data.get('estoque_maximo', 0)
    
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
    def observacoes(self):
        return self.data.get('observacoes', '')
    
    @property
    def imagens(self):
        return self.data.get('imagens', [])
    
    @property
    def documentos(self):
        return self.data.get('documentos', [])
    
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    def get_categoria(self):
        """Retorna a categoria do produto"""
        from .categoria import CategoriaProdutoMongo
        return CategoriaProdutoMongo.find_by_id(self.categoria_id)
    
    def get_estoque_total(self) -> float:
        """Retorna o estoque total do produto em todos os locais"""
        return EstoqueProdutoMongo.get_estoque_total_produto(str(self._id))
    
    def get_estoque_por_local(self, local_id: str, tipo_local: str) -> float:
        """Retorna o estoque do produto em um local específico"""
        return EstoqueProdutoMongo.get_estoque_local(str(self._id), local_id, tipo_local)
    
    def get_lotes_disponiveis(self, local_id: str = None, tipo_local: str = None) -> List['LoteProdutoMongo']:
        """Retorna os lotes disponíveis do produto"""
        return LoteProdutoMongo.find_lotes_disponiveis(str(self._id), local_id, tipo_local)
    
    def get_movimentacoes(self, limit: int = 50) -> List['MovimentacaoProdutoMongo']:
        """Retorna as movimentações do produto"""
        return MovimentacaoProdutoMongo.find_by_produto(str(self._id), limit)
    
    def calcular_preco_medio(self):
        """Calcula e atualiza o preço médio baseado nas movimentações de entrada"""
        movimentacoes = MovimentacaoProdutoMongo.find_many({
            'produto_id': str(self._id),
            'tipo_movimentacao': 'entrada',
            'preco_unitario': {'$gt': 0}
        }, limit=10, sort=[('data_movimentacao', -1)])
        
        if movimentacoes:
            total_valor = sum(mov.preco_unitario * mov.quantidade for mov in movimentacoes)
            total_quantidade = sum(mov.quantidade for mov in movimentacoes)
            
            if total_quantidade > 0:
                self.data['preco_medio'] = float(total_valor / total_quantidade)
                self.save()
    
    @classmethod
    def find_by_nome(cls, nome: str) -> List['ProdutoMongo']:
        """Encontra produtos pelo nome (busca parcial)"""
        return cls.find_many({
            'nome': {'$regex': nome, '$options': 'i'},
            'ativo': True
        })
    
    @classmethod
    def find_by_categoria(cls, categoria_id: str) -> List['ProdutoMongo']:
        """Encontra produtos por categoria"""
        return cls.find_many({'categoria_id': categoria_id, 'ativo': True})
    
    @classmethod
    def find_by_codigo_barras(cls, codigo_barras: str) -> Optional['ProdutoMongo']:
        """Encontra produto pelo código de barras"""
        return cls.find_one({'codigo_barras': codigo_barras, 'ativo': True})
    
    @classmethod
    def find_by_codigo_interno(cls, codigo_interno: str) -> Optional['ProdutoMongo']:
        """Encontra produto pelo código interno"""
        return cls.find_one({'codigo_interno': codigo_interno, 'ativo': True})
    
    @classmethod
    def find_estoque_baixo(cls, central_id: str = None) -> List['ProdutoMongo']:
        """Encontra produtos com estoque baixo"""
        # Esta consulta seria mais complexa, precisaria agregar com estoque
        # Por simplicidade, retornamos produtos ativos
        filter_dict = {'ativo': True}
        if central_id:
            filter_dict['central_id'] = central_id
        return cls.find_many(filter_dict)
    
    @classmethod
    def search(cls, termo: str, categoria_id: str = None, central_id: str = None) -> List['ProdutoMongo']:
        """Busca produtos por termo"""
        filter_dict = {
            '$or': [
                {'nome': {'$regex': termo, '$options': 'i'}},
                {'descricao': {'$regex': termo, '$options': 'i'}},
                {'codigo_barras': {'$regex': termo, '$options': 'i'}},
                {'codigo_interno': {'$regex': termo, '$options': 'i'}},
                {'marca': {'$regex': termo, '$options': 'i'}},
                {'modelo': {'$regex': termo, '$options': 'i'}}
            ],
            'ativo': True
        }
        
        if categoria_id:
            filter_dict['categoria_id'] = categoria_id
        if central_id:
            filter_dict['central_id'] = central_id
        
        return cls.find_many(filter_dict)
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index([('codigo_barras', 1)], unique=True, sparse=True)
        collection.create_index([('codigo_interno', 1), ('central_id', 1)], unique=True, sparse=True)
        
        # Índices para busca
        collection.create_index([('nome', 'text'), ('descricao', 'text'), ('marca', 'text')])
        collection.create_index([('categoria_id', 1), ('ativo', 1)])
        collection.create_index([('central_id', 1), ('ativo', 1)])
        collection.create_index('data_criacao')


class EstoqueProdutoMongo(BaseMongoModel):
    """Modelo MongoDB para controle de estoque por local"""
    
    collection_name = 'estoque_produtos'
    
    def __init__(self, **kwargs):
        # Validações
        if 'produto_id' not in kwargs:
            raise ValueError("produto_id é obrigatório")
        if 'local_id' not in kwargs:
            raise ValueError("local_id é obrigatório")
        if 'tipo_local' not in kwargs:
            raise ValueError("tipo_local é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('quantidade_atual', 0.0)
        kwargs.setdefault('quantidade_reservada', 0.0)
        kwargs.setdefault('quantidade_disponivel', 0.0)
        kwargs.setdefault('estoque_minimo', 0)
        kwargs.setdefault('estoque_maximo', 0)
        kwargs.setdefault('ultima_movimentacao', None)
        kwargs.setdefault('ativo', True)
        
        super().__init__(**kwargs)
    
    @property
    def produto_id(self):
        return self.data.get('produto_id')
    
    @property
    def local_id(self):
        return self.data.get('local_id')
    
    @property
    def tipo_local(self):
        return self.data.get('tipo_local')  # 'almoxarifado', 'sub_almoxarifado', 'setor'
    
    @property
    def quantidade_atual(self):
        return float(self.data.get('quantidade_atual', 0.0))
    
    @property
    def quantidade_reservada(self):
        return float(self.data.get('quantidade_reservada', 0.0))
    
    @property
    def quantidade_disponivel(self):
        return float(self.data.get('quantidade_disponivel', 0.0))
    
    @property
    def estoque_minimo(self):
        return self.data.get('estoque_minimo', 0)
    
    @property
    def estoque_maximo(self):
        return self.data.get('estoque_maximo', 0)
    
    @property
    def ultima_movimentacao(self):
        return self.data.get('ultima_movimentacao')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    def atualizar_quantidade(self, quantidade: float, tipo_operacao: str = 'entrada'):
        """Atualiza a quantidade em estoque"""
        if tipo_operacao == 'entrada':
            self.data['quantidade_atual'] += quantidade
        elif tipo_operacao == 'saida':
            self.data['quantidade_atual'] -= quantidade
        
        # Recalcula quantidade disponível
        self.data['quantidade_disponivel'] = self.quantidade_atual - self.quantidade_reservada
        self.data['ultima_movimentacao'] = datetime.utcnow()
        
        return self.save()
    
    def reservar_quantidade(self, quantidade: float) -> bool:
        """Reserva uma quantidade do estoque"""
        if self.quantidade_disponivel >= quantidade:
            self.data['quantidade_reservada'] += quantidade
            self.data['quantidade_disponivel'] -= quantidade
            self.save()
            return True
        return False
    
    def liberar_reserva(self, quantidade: float):
        """Libera uma quantidade reservada"""
        quantidade_liberada = min(quantidade, self.quantidade_reservada)
        self.data['quantidade_reservada'] -= quantidade_liberada
        self.data['quantidade_disponivel'] += quantidade_liberada
        self.save()
    
    def is_estoque_baixo(self) -> bool:
        """Verifica se o estoque está baixo"""
        return self.quantidade_atual <= self.estoque_minimo
    
    def is_estoque_alto(self) -> bool:
        """Verifica se o estoque está alto"""
        return self.estoque_maximo > 0 and self.quantidade_atual >= self.estoque_maximo
    
    @classmethod
    def find_by_produto_local(cls, produto_id: str, local_id: str, 
                             tipo_local: str) -> Optional['EstoqueProdutoMongo']:
        """Encontra estoque por produto e local"""
        return cls.find_one({
            'produto_id': produto_id,
            'local_id': local_id,
            'tipo_local': tipo_local
        })
    
    @classmethod
    def get_estoque_total_produto(cls, produto_id: str) -> float:
        """Retorna o estoque total de um produto em todos os locais"""
        pipeline = [
            {'$match': {'produto_id': produto_id, 'ativo': True}},
            {'$group': {'_id': None, 'total': {'$sum': '$quantidade_atual'}}}
        ]
        
        result = list(cls.get_collection().aggregate(pipeline))
        return float(result[0]['total']) if result else 0.0
    
    @classmethod
    def get_estoque_local(cls, produto_id: str, local_id: str, tipo_local: str) -> float:
        """Retorna o estoque de um produto em um local específico"""
        estoque = cls.find_by_produto_local(produto_id, local_id, tipo_local)
        return estoque.quantidade_atual if estoque else 0.0
    
    @classmethod
    def find_estoque_baixo(cls, local_id: str = None, tipo_local: str = None) -> List['EstoqueProdutoMongo']:
        """Encontra produtos com estoque baixo"""
        pipeline = [
            {'$match': {'ativo': True}},
            {'$addFields': {
                'estoque_baixo': {'$lte': ['$quantidade_atual', '$estoque_minimo']}
            }},
            {'$match': {'estoque_baixo': True}}
        ]
        
        if local_id and tipo_local:
            pipeline[0]['$match'].update({'local_id': local_id, 'tipo_local': tipo_local})
        
        results = list(cls.get_collection().aggregate(pipeline))
        return [cls.from_dict(doc) for doc in results]
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índice único composto
        collection.create_index([
            ('produto_id', 1),
            ('local_id', 1),
            ('tipo_local', 1)
        ], unique=True)
        
        # Índices para consultas
        collection.create_index('produto_id')
        collection.create_index([('local_id', 1), ('tipo_local', 1)])
        collection.create_index([('quantidade_atual', 1), ('estoque_minimo', 1)])
        collection.create_index('ultima_movimentacao')


class LoteProdutoMongo(BaseMongoModel):
    """Modelo MongoDB para controle de lotes"""
    
    collection_name = 'lotes_produtos'
    
    def __init__(self, **kwargs):
        # Validações
        if 'produto_id' not in kwargs:
            raise ValueError("produto_id é obrigatório")
        if 'numero_lote' not in kwargs:
            raise ValueError("numero_lote é obrigatório")
        
        # Define valores padrão
        kwargs.setdefault('quantidade_inicial', 0.0)
        kwargs.setdefault('quantidade_atual', 0.0)
        kwargs.setdefault('data_fabricacao', None)
        kwargs.setdefault('data_validade', None)
        kwargs.setdefault('preco_unitario', 0.0)
        kwargs.setdefault('fornecedor', '')
        kwargs.setdefault('nota_fiscal', '')
        kwargs.setdefault('observacoes', '')
        kwargs.setdefault('ativo', True)
        
        super().__init__(**kwargs)
    
    @property
    def produto_id(self):
        return self.data.get('produto_id')
    
    @property
    def numero_lote(self):
        return self.data.get('numero_lote')
    
    @property
    def quantidade_inicial(self):
        return float(self.data.get('quantidade_inicial', 0.0))
    
    @property
    def quantidade_atual(self):
        return float(self.data.get('quantidade_atual', 0.0))
    
    @property
    def data_fabricacao(self):
        return self.data.get('data_fabricacao')
    
    @property
    def data_validade(self):
        return self.data.get('data_validade')
    
    @property
    def preco_unitario(self):
        return float(self.data.get('preco_unitario', 0.0))
    
    @property
    def fornecedor(self):
        return self.data.get('fornecedor', '')
    
    @property
    def nota_fiscal(self):
        return self.data.get('nota_fiscal', '')
    
    @property
    def observacoes(self):
        return self.data.get('observacoes', '')
    
    @property
    def local_id(self):
        return self.data.get('local_id')
    
    @property
    def tipo_local(self):
        return self.data.get('tipo_local')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    def is_vencido(self) -> bool:
        """Verifica se o lote está vencido"""
        if not self.data_validade:
            return False
        return datetime.now().date() > self.data_validade
    
    def dias_para_vencimento(self) -> int:
        """Retorna quantos dias faltam para o vencimento"""
        if not self.data_validade:
            return float('inf')
        
        delta = self.data_validade - datetime.now().date()
        return delta.days
    
    def is_proximo_vencimento(self, dias_alerta: int = 30) -> bool:
        """Verifica se o lote está próximo do vencimento"""
        if not self.data_validade:
            return False
        
        return 0 <= self.dias_para_vencimento() <= dias_alerta
    
    def consumir_quantidade(self, quantidade: float) -> bool:
        """Consome uma quantidade do lote"""
        if self.quantidade_atual >= quantidade:
            self.data['quantidade_atual'] -= quantidade
            self.save()
            return True
        return False
    
    @classmethod
    def find_by_produto(cls, produto_id: str) -> List['LoteProdutoMongo']:
        """Encontra lotes por produto"""
        return cls.find_many({'produto_id': produto_id, 'ativo': True})
    
    @classmethod
    def find_lotes_disponiveis(cls, produto_id: str, local_id: str = None, 
                              tipo_local: str = None) -> List['LoteProdutoMongo']:
        """Encontra lotes disponíveis (com quantidade > 0)"""
        filter_dict = {
            'produto_id': produto_id,
            'quantidade_atual': {'$gt': 0},
            'ativo': True
        }
        
        if local_id and tipo_local:
            filter_dict.update({'local_id': local_id, 'tipo_local': tipo_local})
        
        return cls.find_many(filter_dict, sort=[('data_validade', 1)])
    
    @classmethod
    def find_vencidos(cls, local_id: str = None, tipo_local: str = None) -> List['LoteProdutoMongo']:
        """Encontra lotes vencidos"""
        filter_dict = {
            'data_validade': {'$lt': datetime.now().date()},
            'quantidade_atual': {'$gt': 0},
            'ativo': True
        }
        
        if local_id and tipo_local:
            filter_dict.update({'local_id': local_id, 'tipo_local': tipo_local})
        
        return cls.find_many(filter_dict)
    
    @classmethod
    def find_proximos_vencimento(cls, dias_alerta: int = 30, local_id: str = None, 
                                tipo_local: str = None) -> List['LoteProdutoMongo']:
        """Encontra lotes próximos do vencimento"""
        data_limite = datetime.now().date() + datetime.timedelta(days=dias_alerta)
        
        filter_dict = {
            'data_validade': {
                '$gte': datetime.now().date(),
                '$lte': data_limite
            },
            'quantidade_atual': {'$gt': 0},
            'ativo': True
        }
        
        if local_id and tipo_local:
            filter_dict.update({'local_id': local_id, 'tipo_local': tipo_local})
        
        return cls.find_many(filter_dict, sort=[('data_validade', 1)])
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices compostos
        collection.create_index([('produto_id', 1), ('numero_lote', 1)], unique=True)
        collection.create_index([('produto_id', 1), ('data_validade', 1)])
        collection.create_index([('local_id', 1), ('tipo_local', 1)])
        collection.create_index([('data_validade', 1), ('quantidade_atual', 1)])
        collection.create_index('data_criacao')


class MovimentacaoProdutoMongo(BaseMongoModel):
    """Modelo MongoDB para movimentações de estoque"""
    
    collection_name = 'movimentacoes_produtos'
    
    TIPOS_MOVIMENTACAO = [
        'entrada',           # Entrada no estoque
        'saida',            # Saída do estoque
        'transferencia',    # Transferência entre locais
        'ajuste',           # Ajuste de estoque
        'perda',            # Perda/quebra
        'devolucao'         # Devolução
    ]
    
    def __init__(self, **kwargs):
        # Validações
        if 'produto_id' not in kwargs:
            raise ValueError("produto_id é obrigatório")
        if 'tipo_movimentacao' not in kwargs:
            raise ValueError("tipo_movimentacao é obrigatório")
        if kwargs.get('tipo_movimentacao') not in self.TIPOS_MOVIMENTACAO:
            raise ValueError(f"tipo_movimentacao deve ser um de: {self.TIPOS_MOVIMENTACAO}")
        if 'quantidade' not in kwargs:
            raise ValueError("quantidade é obrigatória")
        
        # Define valores padrão
        kwargs.setdefault('data_movimentacao', datetime.utcnow())
        kwargs.setdefault('preco_unitario', 0.0)
        kwargs.setdefault('valor_total', 0.0)
        kwargs.setdefault('observacoes', '')
        kwargs.setdefault('documento_referencia', '')
        
        super().__init__(**kwargs)
    
    @property
    def produto_id(self):
        return self.data.get('produto_id')
    
    @property
    def tipo_movimentacao(self):
        return self.data.get('tipo_movimentacao')
    
    @property
    def quantidade(self):
        return float(self.data.get('quantidade', 0.0))
    
    @property
    def data_movimentacao(self):
        return self.data.get('data_movimentacao')
    
    @property
    def preco_unitario(self):
        return float(self.data.get('preco_unitario', 0.0))
    
    @property
    def valor_total(self):
        return float(self.data.get('valor_total', 0.0))
    
    @property
    def local_origem_id(self):
        return self.data.get('local_origem_id')
    
    @property
    def tipo_local_origem(self):
        return self.data.get('tipo_local_origem')
    
    @property
    def local_destino_id(self):
        return self.data.get('local_destino_id')
    
    @property
    def tipo_local_destino(self):
        return self.data.get('tipo_local_destino')
    
    @property
    def lote_id(self):
        return self.data.get('lote_id')
    
    @property
    def usuario_id(self):
        return self.data.get('usuario_id')
    
    @property
    def observacoes(self):
        return self.data.get('observacoes', '')
    
    @property
    def documento_referencia(self):
        return self.data.get('documento_referencia', '')
    
    @classmethod
    def find_by_produto(cls, produto_id: str, limit: int = 50) -> List['MovimentacaoProdutoMongo']:
        """Encontra movimentações por produto"""
        return cls.find_many(
            {'produto_id': produto_id},
            limit=limit,
            sort=[('data_movimentacao', -1)]
        )
    
    @classmethod
    def find_by_local(cls, local_id: str, tipo_local: str, limit: int = 50) -> List['MovimentacaoProdutoMongo']:
        """Encontra movimentações por local"""
        filter_dict = {
            '$or': [
                {'local_origem_id': local_id, 'tipo_local_origem': tipo_local},
                {'local_destino_id': local_id, 'tipo_local_destino': tipo_local}
            ]
        }
        
        return cls.find_many(
            filter_dict,
            limit=limit,
            sort=[('data_movimentacao', -1)]
        )
    
    @classmethod
    def find_by_periodo(cls, data_inicio: datetime, data_fim: datetime, 
                       produto_id: str = None) -> List['MovimentacaoProdutoMongo']:
        """Encontra movimentações por período"""
        filter_dict = {
            'data_movimentacao': {
                '$gte': data_inicio,
                '$lte': data_fim
            }
        }
        
        if produto_id:
            filter_dict['produto_id'] = produto_id
        
        return cls.find_many(filter_dict, sort=[('data_movimentacao', -1)])
    
    @classmethod
    def find_by_tipo(cls, tipo_movimentacao: str, limit: int = 50) -> List['MovimentacaoProdutoMongo']:
        """Encontra movimentações por tipo"""
        return cls.find_many(
            {'tipo_movimentacao': tipo_movimentacao},
            limit=limit,
            sort=[('data_movimentacao', -1)]
        )
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices compostos
        collection.create_index([('produto_id', 1), ('data_movimentacao', -1)])
        collection.create_index([('local_origem_id', 1), ('tipo_local_origem', 1)])
        collection.create_index([('local_destino_id', 1), ('tipo_local_destino', 1)])
        collection.create_index([('tipo_movimentacao', 1), ('data_movimentacao', -1)])
        collection.create_index([('usuario_id', 1), ('data_movimentacao', -1)])
        collection.create_index('data_movimentacao')
        collection.create_index('lote_id')