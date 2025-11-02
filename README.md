# Almox SMS - Sistema de Gerenciamento de Almoxarifado

Sistema modular de gerenciamento de almoxarifado desenvolvido em Flask com arquitetura baseada em blueprints.

## Características

- **Arquitetura Modular**: Utiliza Flask Blueprints para organização do código
- **Hierarquia Flexível**: Sistema de 4 níveis (Central > Almoxarifado > Sub-Almoxarifado > Setor)
- **Interface Moderna**: Frontend responsivo com Bootstrap 5
- **API RESTful**: Endpoints para operações CRUD
- **Banco de Dados**: SQLite para desenvolvimento, PostgreSQL para produção

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
├── models/               # Modelos de dados
│   ├── __init__.py
│   └── hierarchy.py      # Modelos da hierarquia
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

## Tecnologias Utilizadas

- **Backend**: Flask, SQLAlchemy, Flask-Migrate
- **Frontend**: Bootstrap 5, jQuery, Font Awesome
- **Banco de Dados**: SQLite (dev), PostgreSQL (prod)
- **Arquitetura**: Blueprints, API REST

## Notas de CSRF e MongoDB

- CSRF em APIs JSON:
  - Requisições `POST`, `PUT`, `PATCH` e `DELETE` para endpoints de API que recebem `Content-Type: application/json` exigem o cabeçalho `X-CSRF-Token` quando o usuário está autenticado.
  - Para obter o token no backend de testes, realize um `GET /` para provisionar o token na sessão e, em seguida, leia `session['csrf_token']`.
  - No frontend, o token é exposto em `window.CSRF_TOKEN` e anexado automaticamente em chamadas `fetch` de métodos que alteram estado.
  - Exemplo (teste):
    ```python
    client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    client.get('/')  # provisiona CSRF na sessão
    with client.session_transaction() as sess:
        csrf = sess.get('csrf_token')
    headers = {'Accept': 'application/json','Content-Type': 'application/json','X-CSRF-Token': csrf}
    r = client.post('/api/centrais', json={'nome': 'Central'}, headers=headers)
    ```

- Alinhamento de IDs (MongoDB):
  - O sistema aceita IDs em múltiplos formatos (sequencial `id`, `ObjectId` e `str`) e normaliza para persistir e consultar.
  - Endpoints e consultas consideram campos como `id`, `_id`, e também variantes stringificadas (`str(ObjectId)`), garantindo compatibilidade.
  - Em coleções como `estoques`, `movimentacoes` e `lotes`, o campo `produto_id` pode estar como inteiro, `ObjectId` ou string; as APIs fazem resolução de candidatos de ID e deduplicação por tipo/valor.
  - Em integrações e testes, é seguro enviar qualquer uma das formas de ID suportadas; o backend cuidará da normalização.

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.