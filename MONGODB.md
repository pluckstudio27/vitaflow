# MongoDB Integration Guide

Este documento descreve a integração completa do MongoDB no sistema Almox SMS.

## Visão Geral

O sistema Almox SMS oferece suporte dual para bancos de dados:
- **SQLAlchemy**: SQLite (desenvolvimento) e PostgreSQL (produção)
- **MongoDB**: Banco de dados NoSQL com modelos nativos

## Configuração

### Variáveis de Ambiente

```env
# Ativar MongoDB como banco principal
USE_MONGODB_PRIMARY=true

# URI de conexão MongoDB
MONGODB_URI=mongodb://localhost:27017/almox_sms

# Para MongoDB Atlas
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/almox_sms
```

### Instalação do MongoDB

#### Local (Windows)
1. Baixe o MongoDB Community Server
2. Instale e inicie o serviço
3. Configure a URI: `mongodb://localhost:27017/almox_sms`

#### MongoDB Atlas (Cloud)
1. Crie uma conta no MongoDB Atlas
2. Configure um cluster
3. Obtenha a string de conexão
4. Configure a URI no `.env`

## Arquitetura dos Modelos

### Classe Base (BaseModel)

Todos os modelos MongoDB herdam de `BaseModel`:

```python
class BaseModel:
    def __init__(self, collection_name):
        self.collection = db[collection_name]
    
    def save(self, data):
        # Salva documento com validação
    
    def find_all(self, filter_dict=None):
        # Busca documentos com filtros
    
    def find_by_id(self, doc_id):
        # Busca por ObjectId
    
    def update(self, doc_id, data):
        # Atualiza documento
    
    def delete(self, doc_id):
        # Remove documento
```

### Modelos Disponíveis

#### Estrutura Hierárquica
- **CentralMongo**: Centrais do sistema
- **AlmoxarifadoMongo**: Almoxarifados vinculados às centrais
- **SubAlmoxarifadoMongo**: Sub-almoxarifados vinculados aos almoxarifados
- **SetorMongo**: Setores vinculados aos sub-almoxarifados

#### Outros Modelos
- **UsuarioMongo**: Usuários do sistema
- **ProdutoMongo**: Produtos do estoque
- **CategoriaMongo**: Categorias de produtos

### Estrutura dos Documentos

#### Central
```json
{
  "_id": ObjectId,
  "nome": "string",
  "descricao": "string",
  "ativo": boolean,
  "created_at": datetime,
  "updated_at": datetime
}
```

#### Almoxarifado
```json
{
  "_id": ObjectId,
  "nome": "string",
  "descricao": "string",
  "central_id": ObjectId,
  "ativo": boolean,
  "created_at": datetime,
  "updated_at": datetime
}
```

#### Usuário
```json
{
  "_id": ObjectId,
  "username": "string",
  "email": "string",
  "password_hash": "string",
  "nome": "string",
  "nivel_acesso": "string",
  "central_id": ObjectId,
  "almoxarifado_id": ObjectId,
  "sub_almoxarifado_id": ObjectId,
  "ativo": boolean,
  "created_at": datetime,
  "updated_at": datetime
}
```

## Migração de Dados

### Script de Migração

Execute o script para migrar dados do SQLAlchemy para MongoDB:

```bash
python migrate_to_mongodb.py
```

### Processo de Migração

1. **Conexão**: Conecta aos bancos SQLAlchemy e MongoDB
2. **Usuários**: Migra usuários preservando senhas hash
3. **Hierarquia**: Migra centrais, almoxarifados, sub-almoxarifados e setores
4. **Produtos**: Migra produtos e categorias
5. **Relacionamentos**: Preserva referências entre documentos
6. **Índices**: Cria índices otimizados

### Verificação da Migração

```python
# Verificar contagem de documentos
from models_mongo import *

print(f"Centrais: {CentralMongo().collection.count_documents({})}")
print(f"Usuários: {UsuarioMongo().collection.count_documents({})}")
print(f"Produtos: {ProdutoMongo().collection.count_documents({})}")
```

## Sistema de Autenticação

### Filtros de Escopo MongoDB

O sistema inclui filtros específicos para MongoDB:

```python
class ScopeFilter:
    @staticmethod
    def filter_centrais_mongo():
        # Filtra centrais baseado no escopo do usuário
    
    @staticmethod
    def filter_almoxarifados_mongo():
        # Filtra almoxarifados baseado no escopo do usuário
    
    @staticmethod
    def filter_setores_mongo():
        # Filtra setores baseado no escopo do usuário
```

### Níveis de Acesso

- **admin_sistema**: Acesso total a todos os documentos
- **admin_central**: Acesso limitado à central do usuário
- **admin_almoxarifado**: Acesso limitado ao almoxarifado do usuário
- **usuario**: Acesso limitado ao setor do usuário

## API REST

### Endpoints Compatíveis

Todos os endpoints da API funcionam com MongoDB:

```
GET /api/centrais          # Lista centrais (com filtro de escopo)
POST /api/centrais         # Cria nova central
PUT /api/centrais/<id>     # Atualiza central
DELETE /api/centrais/<id>  # Remove central

GET /api/almoxarifados     # Lista almoxarifados
GET /api/produtos          # Lista produtos
GET /api/estoque           # Lista estoque
```

### Formato de Resposta

```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "nome": "Central Principal",
      "descricao": "Central principal do sistema",
      "ativo": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

## Índices e Performance

### Índices Automáticos

O sistema cria automaticamente índices otimizados:

```python
# Centrais
collection.create_index("nome")
collection.create_index("ativo")

# Almoxarifados
collection.create_index("central_id")
collection.create_index("nome")

# Usuários
collection.create_index("username", unique=True)
collection.create_index("email", unique=True)
collection.create_index("central_id")
```

### Consultas Otimizadas

```python
# Busca com filtros compostos
filter_dict = {
    "central_id": ObjectId(central_id),
    "ativo": True
}
almoxarifados = AlmoxarifadoMongo().find_all(filter_dict)

# Busca com projeção
projection = {"nome": 1, "descricao": 1}
centrais = CentralMongo().collection.find({}, projection)
```

## Troubleshooting

### Problemas Comuns

#### Erro de Conexão
```
pymongo.errors.ServerSelectionTimeoutError
```
**Solução**: Verificar se o MongoDB está rodando e a URI está correta.

#### Erro de Autenticação
```
pymongo.errors.OperationFailure: Authentication failed
```
**Solução**: Verificar credenciais na URI de conexão.

#### Erro de ObjectId
```
bson.errors.InvalidId: ObjectIds have invalid ObjectId
```
**Solução**: Validar formato do ObjectId antes de usar.

### Logs e Debug

Ativar logs detalhados:

```python
import logging
logging.getLogger('pymongo').setLevel(logging.DEBUG)
```

### Backup e Restore

```bash
# Backup
mongodump --uri="mongodb://localhost:27017/almox_sms" --out=backup/

# Restore
mongorestore --uri="mongodb://localhost:27017/almox_sms" backup/almox_sms/
```

## Considerações de Produção

### Segurança
- Use autenticação MongoDB
- Configure SSL/TLS
- Limite acesso por IP
- Use usuários com permissões mínimas

### Performance
- Configure réplicas para alta disponibilidade
- Use sharding para grandes volumes
- Monitore performance com MongoDB Compass
- Configure alertas de performance

### Backup
- Configure backup automático
- Teste procedimentos de restore
- Mantenha backups em locais seguros
- Documente procedimentos de recuperação