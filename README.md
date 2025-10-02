# Almox SMS - Sistema de Gerenciamento de Almoxarifado

Sistema modular de gerenciamento de almoxarifado desenvolvido em Flask com arquitetura baseada em blueprints.

## Características

- **Arquitetura Modular**: Utiliza Flask Blueprints para organização do código
- **Hierarquia Flexível**: Sistema de 4 níveis (Central > Almoxarifado > Sub-Almoxarifado > Setor)
- **Interface Moderna**: Frontend responsivo com Bootstrap 5
- **API RESTful**: Endpoints para operações CRUD
- **Banco de Dados**: SQLite/PostgreSQL (SQLAlchemy) ou MongoDB (PyMongo) - Suporte dual

## Estrutura da Hierarquia

```
Central (Nível 1)
├── Almoxarifado (Nível 2)
    ├── Sub-Almoxarifado (Nível 3)
        ├── Setor (Nível 4)
```

## Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd almox-sms
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
copy .env.example .env
# Edite o arquivo .env com suas configurações
```

### Configuração de Banco de Dados

O sistema suporta dois tipos de banco de dados:

#### SQLAlchemy (SQLite/PostgreSQL)
```env
USE_MONGODB_PRIMARY=false
DATABASE_URL=sqlite:///almoxarifado.db
# ou para PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/almoxarifado
```

#### MongoDB
```env
USE_MONGODB_PRIMARY=true
MONGODB_URI=mongodb://localhost:27017/almoxarifado
# ou para MongoDB Atlas:
# MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/almoxarifado
```

5. Execute a aplicação:
```bash
python app.py
```

A aplicação estará disponível em `http://localhost:5000`

## Estrutura do Projeto

```
almox-sms/
├── app.py                 # Arquivo principal da aplicação
├── config.py              # Configurações da aplicação
├── extensions.py          # Extensões Flask
├── requirements.txt       # Dependências
├── blueprints/           # Blueprints da aplicação
│   ├── __init__.py
│   ├── main.py           # Rotas principais
│   ├── api.py            # API REST
│   └── hierarchy.py      # Gerenciamento de hierarquia
├── models/               # Modelos SQLAlchemy
│   ├── __init__.py
│   ├── hierarchy.py      # Modelos da hierarquia
│   ├── produto.py        # Modelos de produtos
│   ├── usuario.py        # Modelos de usuários
│   └── categoria.py      # Modelos de categorias
├── models_mongo/         # Modelos MongoDB
│   ├── __init__.py
│   ├── base.py           # Classe base MongoDB
│   ├── estrutura.py      # Modelos da hierarquia
│   ├── produto.py        # Modelos de produtos
│   ├── usuario.py        # Modelos de usuários
│   └── categoria.py      # Modelos de categorias
└── templates/            # Templates HTML
    ├── base.html         # Template base
    ├── index.html        # Dashboard
    ├── configuracoes.html # Configurações
    ├── hierarquia.html   # Visualização da hierarquia
    └── hierarchy/        # Templates de gerenciamento
        └── index.html    # Gerenciar hierarquia
```

## Funcionalidades Implementadas

### ✅ Etapa 1 - Concluída
- [x] Estrutura base da aplicação Flask com blueprints
- [x] Sistema de configuração com SQLite/PostgreSQL
- [x] Modelos de dados para hierarquia
- [x] API CRUD para centrais e almoxarifados
- [x] Frontend com menu lateral
- [x] Página de configurações
- [x] Interface para gerenciar hierarquia

### 🔄 Próximas Etapas
- [ ] Completar API CRUD para sub-almoxarifados e setores
- [ ] Sistema de autenticação e autorização
- [ ] Gerenciamento de produtos
- [ ] Sistema de movimentações
- [ ] Relatórios e dashboards
- [ ] Testes automatizados

## API Endpoints

### Centrais
- `GET /api/centrais` - Listar centrais
- `POST /api/centrais` - Criar central
- `PUT /api/centrais/<id>` - Atualizar central
- `DELETE /api/centrais/<id>` - Deletar central

### Almoxarifados
- `GET /api/almoxarifados` - Listar almoxarifados
- `POST /api/almoxarifados` - Criar almoxarifado

## Suporte ao MongoDB

O sistema oferece suporte completo ao MongoDB como alternativa ao SQLAlchemy. As principais características incluem:

### Funcionalidades MongoDB
- **Modelos Nativos**: Modelos MongoDB com validação e índices automáticos
- **Migração de Dados**: Script automático para migrar dados do SQLite/PostgreSQL para MongoDB
- **Autenticação**: Sistema de autenticação compatível com MongoDB
- **Filtros de Escopo**: Filtros de permissão adaptados para consultas MongoDB
- **API Unificada**: Mesma API REST funciona com ambos os bancos de dados

### Migração para MongoDB
Para migrar dados existentes do SQLAlchemy para MongoDB:

```bash
python migrate_to_mongodb.py
```

Este script:
1. Conecta aos dois bancos de dados
2. Migra usuários, hierarquia, produtos e categorias
3. Preserva relacionamentos e referências
4. Cria índices otimizados no MongoDB

### Estrutura dos Modelos MongoDB
- **BaseModel**: Classe base com funcionalidades comuns
- **CentralMongo**: Centrais com validação e índices
- **AlmoxarifadoMongo**: Almoxarifados com referência à central
- **SubAlmoxarifadoMongo**: Sub-almoxarifados com referência ao almoxarifado
- **SetorMongo**: Setores com referência ao sub-almoxarifado
- **UsuarioMongo**: Usuários com autenticação e permissões
- **ProdutoMongo**: Produtos com categorização
- **CategoriaMongo**: Categorias de produtos

## Tecnologias Utilizadas

- **Backend**: Flask, SQLAlchemy, Flask-Migrate, PyMongo
- **Frontend**: Bootstrap 5, jQuery, Font Awesome
- **Banco de Dados**: SQLite/PostgreSQL (SQLAlchemy) ou MongoDB (PyMongo)
- **Arquitetura**: Blueprints, API REST, Suporte dual de banco de dados

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.