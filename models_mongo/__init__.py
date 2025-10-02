# MongoDB Models package
from .base import BaseMongoModel
from .usuario import UsuarioMongo, LogAuditoriaMongo
from .estrutura import CentralMongo, AlmoxarifadoMongo, SubAlmoxarifadoMongo, SetorMongo
from .categoria import CategoriaProdutoMongo, ConfiguracaoCategoriaMongo
from .produto import ProdutoMongo, EstoqueProdutoMongo, LoteProdutoMongo, MovimentacaoProdutoMongo

__all__ = [
    'BaseMongoModel',
    'UsuarioMongo',
    'CentralMongo',
    'AlmoxarifadoMongo', 
    'SubAlmoxarifadoMongo',
    'SetorMongo',
    'CategoriaProdutoMongo',
    'ProdutoMongo',
    'EstoqueProdutoMongo',
    'LoteProdutoMongo',
    'MovimentacaoProdutoMongo',
    'LogAuditoriaMongo'
]


def create_all_indexes():
    """Cria todos os índices necessários para os modelos MongoDB"""
    models = [
        UsuarioMongo,
        LogAuditoriaMongo,
        CategoriaProdutoMongo,
        ProdutoMongo,
        EstoqueProdutoMongo,
        LoteProdutoMongo,
        MovimentacaoProdutoMongo,
        CentralMongo,
        AlmoxarifadoMongo,
        SubAlmoxarifadoMongo,
        SetorMongo
    ]
    
    for model in models:
        try:
            model.create_indexes()
            print(f"Índices criados para {model.__name__}")
        except Exception as e:
            print(f"Erro ao criar índices para {model.__name__}: {e}")


def init_mongodb():
    """Inicializa o MongoDB criando índices e estruturas necessárias"""
    print("Inicializando MongoDB...")
    create_all_indexes()
    print("MongoDB inicializado com sucesso!")