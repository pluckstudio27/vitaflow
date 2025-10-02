"""
Modelo base para MongoDB com funcionalidades comuns
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId
from extensions import get_mongo_db
import json


class BaseMongoModel:
    """Classe base para todos os modelos MongoDB"""
    
    collection_name = None  # Deve ser definido nas subclasses
    
    def __init__(self, **kwargs):
        """Inicializa o modelo com os dados fornecidos"""
        self._id = kwargs.get('_id')
        self.data = kwargs
        
        # Adiciona timestamps se não existirem
        if 'data_criacao' not in self.data:
            self.data['data_criacao'] = datetime.utcnow()
        if 'data_atualizacao' not in self.data:
            self.data['data_atualizacao'] = datetime.utcnow()
    
    @property
    def id(self):
        """Retorna o ID do documento"""
        return str(self._id) if self._id else None
    
    @classmethod
    def get_collection(cls):
        """Retorna a coleção MongoDB para este modelo"""
        if not cls.collection_name:
            raise ValueError(f"collection_name não definido para {cls.__name__}")
        mongo_db = get_mongo_db()
        if mongo_db is None:
            raise RuntimeError("MongoDB não está inicializado")
        return mongo_db[cls.collection_name]
    
    def save(self) -> 'BaseMongoModel':
        """Salva o documento no MongoDB"""
        collection = self.get_collection()
        self.data['data_atualizacao'] = datetime.utcnow()
        
        if self._id:
            # Atualiza documento existente
            collection.update_one(
                {'_id': self._id},
                {'$set': self.data}
            )
        else:
            # Insere novo documento
            result = collection.insert_one(self.data)
            self._id = result.inserted_id
        
        return self
    
    def delete(self) -> bool:
        """Remove o documento do MongoDB"""
        if not self._id:
            return False
        
        collection = self.get_collection()
        result = collection.delete_one({'_id': self._id})
        return result.deleted_count > 0
    
    @classmethod
    def find_by_id(cls, doc_id: str) -> Optional['BaseMongoModel']:
        """Encontra um documento pelo ID"""
        try:
            object_id = ObjectId(doc_id)
            collection = cls.get_collection()
            doc = collection.find_one({'_id': object_id})
            
            if doc:
                instance = cls(**doc)
                instance._id = doc['_id']
                return instance
            return None
        except Exception:
            return None
    
    @classmethod
    def find_one(cls, filter_dict: Dict[str, Any]) -> Optional['BaseMongoModel']:
        """Encontra um documento pelos filtros"""
        collection = cls.get_collection()
        doc = collection.find_one(filter_dict)
        
        if doc:
            instance = cls(**doc)
            instance._id = doc['_id']
            return instance
        return None
    
    @classmethod
    def find_many(cls, filter_dict: Dict[str, Any] = None, 
                  limit: int = None, skip: int = None, 
                  sort: List[tuple] = None) -> List['BaseMongoModel']:
        """Encontra múltiplos documentos"""
        collection = cls.get_collection()
        cursor = collection.find(filter_dict or {})
        
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        
        results = []
        for doc in cursor:
            instance = cls(**doc)
            instance._id = doc['_id']
            results.append(instance)
        
        return results
    
    @classmethod
    def count(cls, filter_dict: Dict[str, Any] = None) -> int:
        """Conta documentos na coleção"""
        collection = cls.get_collection()
        return collection.count_documents(filter_dict or {})
    
    @classmethod
    def aggregate(cls, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executa uma operação de agregação"""
        collection = cls.get_collection()
        return list(collection.aggregate(pipeline))
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para dicionário"""
        result = self.data.copy()
        if self._id:
            result['id'] = str(self._id)
        
        # Converte datetime para string ISO
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, ObjectId):
                result[key] = str(value)
        
        return result
    
    def to_json(self) -> str:
        """Converte o modelo para JSON"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para a coleção - deve ser implementado nas subclasses"""
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"