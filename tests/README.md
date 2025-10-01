# Sistema de Testes Automatizados - Almox SMS

Este diretório contém um sistema abrangente de testes automatizados para a aplicação Almox SMS.

## 📁 Estrutura dos Testes

```
tests/
├── conftest.py                 # Configurações e fixtures do pytest
├── test_auth.py               # Testes de autenticação e autorização
├── test_api_users.py          # Testes da API de usuários
├── test_api_categories.py     # Testes da API de categorias
├── test_api_products.py       # Testes da API de produtos
├── test_api_stock.py          # Testes da API de estoque
├── test_web_pages.py          # Testes das páginas web
├── test_report_generator.py   # Gerador de relatórios personalizados
└── README.md                  # Esta documentação
```

## 🚀 Como Executar os Testes

### Execução Completa

Para executar todos os testes e gerar relatórios completos:

```bash
python run_tests.py
```

### Execução por Tipo

Execute apenas tipos específicos de teste:

```bash
# Testes de autenticação
python run_tests.py --type auth

# Testes de API
python run_tests.py --type api

# Testes de páginas web
python run_tests.py --type web

# Testes unitários
python run_tests.py --type unit

# Testes de integração
python run_tests.py --type integration

# Testes lentos
python run_tests.py --type slow
```

### Opções Avançadas

```bash
# Execução verbosa
python run_tests.py --verbose

# Pular análise de cobertura
python run_tests.py --no-coverage

# Pular testes de performance
python run_tests.py --no-performance

# Pular verificação de saúde
python run_tests.py --no-health
```

### Execução Manual com Pytest

```bash
# Todos os testes
pytest tests/

# Testes específicos
pytest tests/test_auth.py

# Com cobertura
pytest --cov=. tests/

# Com relatório HTML
pytest --html=report.html tests/
```

## 📊 Tipos de Teste

### 🔐 Testes de Autenticação (`test_auth.py`)
- Login/logout
- Proteção de rotas
- Controle de acesso por nível de usuário
- Validação de sessões

### 👥 Testes de API de Usuários (`test_api_users.py`)
- CRUD de usuários
- Validação de dados
- Controle de acesso
- Paginação e busca

### 🏷️ Testes de API de Categorias (`test_api_categories.py`)
- CRUD de categorias
- Validação de códigos únicos
- Controle de acesso administrativo
- Relacionamentos com produtos

### 📦 Testes de API de Produtos (`test_api_products.py`)
- CRUD de produtos
- Filtros por categoria
- Validação de dados
- Controle de acesso por categoria do usuário

### 📊 Testes de API de Estoque (`test_api_stock.py`)
- CRUD de estoque
- Movimentações
- Relatórios
- Alertas de estoque baixo

### 🌐 Testes de Páginas Web (`test_web_pages.py`)
- Carregamento de páginas
- Elementos da interface
- Responsividade
- Acessibilidade
- Performance

## 🛠️ Configuração

### Dependências

Instale as dependências de teste:

```bash
pip install -r requirements.txt
```

As dependências de teste incluem:
- `pytest` - Framework de testes
- `pytest-flask` - Integração Flask/pytest
- `pytest-cov` - Cobertura de código
- `pytest-html` - Relatórios HTML
- `pytest-mock` - Mocking
- `coverage` - Análise de cobertura
- `factory-boy` - Factories para dados de teste
- `faker` - Geração de dados falsos

### Configuração do Banco de Dados

Os testes usam um banco SQLite temporário em memória para isolamento completo.

### Variáveis de Ambiente

Configure as seguintes variáveis para testes:

```bash
export FLASK_ENV=testing
export DATABASE_URL=sqlite:///:memory:
export SECRET_KEY=test-secret-key
```

## 📈 Relatórios

O sistema gera múltiplos tipos de relatório:

### 📄 Relatório HTML
- Interface visual interativa
- Gráficos de cobertura
- Detalhes de cada teste
- Métricas de performance

### 📊 Relatório JSON
- Dados estruturados
- Integração com CI/CD
- Análise programática

### 📝 Relatório Markdown
- Documentação legível
- Integração com Git
- Fácil compartilhamento

### 📋 Relatório de Cobertura
- Cobertura por arquivo
- Linhas não cobertas
- Relatório HTML detalhado

## 🎯 Fixtures Disponíveis

### Aplicação e Cliente
- `app` - Instância da aplicação Flask
- `client` - Cliente de teste Flask
- `runner` - Runner de comandos CLI

### Banco de Dados
- `db_session` - Sessão de banco limpa
- `clean_db` - Banco limpo antes de cada teste

### Dados de Teste
- `central_teste` - Central de teste
- `categoria_teste` - Categoria de teste
- `categoria_teste_2` - Segunda categoria
- `usuario_admin` - Usuário administrador
- `usuario_user` - Usuário comum
- `produto_teste` - Produto de teste
- `almoxarifado_teste` - Item de estoque

### Autenticação
- `auth_headers_admin` - Headers de autenticação admin
- `auth_headers_user` - Headers de autenticação usuário
- `admin_logged_in` - Sessão admin ativa
- `user_logged_in` - Sessão usuário ativa

## 🏷️ Marcadores (Markers)

Use marcadores para categorizar testes:

```python
@pytest.mark.unit          # Testes unitários
@pytest.mark.integration   # Testes de integração
@pytest.mark.api          # Testes de API
@pytest.mark.web          # Testes de interface web
@pytest.mark.auth         # Testes de autenticação
@pytest.mark.slow         # Testes lentos
```

## 📝 Escrevendo Novos Testes

### Estrutura Básica

```python
import pytest

@pytest.mark.api
class TestMinhaAPI:
    """Testes para minha API"""
    
    def test_minha_funcionalidade(self, client, auth_headers_admin):
    """Teste de exemplo"""
    response = client.get('/api/endpoint', headers=auth_headers_admin)
    assert response.status_code == 200
        data = response.get_json()
        assert 'campo_esperado' in data
```

### Boas Práticas

1. **Nomes Descritivos**: Use nomes que descrevam claramente o que está sendo testado
2. **Isolamento**: Cada teste deve ser independente
3. **Arrange-Act-Assert**: Organize o código do teste em seções claras
4. **Fixtures**: Use fixtures para dados de teste reutilizáveis
5. **Marcadores**: Categorize testes com marcadores apropriados

### Testando APIs

```python
def test_create_resource(self, client, auth_headers_admin):
    """Teste criação de recurso"""
    data = {'nome': 'Teste', 'ativo': True}
    response = client.post('/api/recursos',
                          headers=auth_headers_admin,
                          json=data)
    assert response.status_code == 201
    result = response.get_json()
    assert result['nome'] == data['nome']
```

### Testando Páginas Web

```python
def test_page_loads(self, client, admin_logged_in):
    """Teste carregamento de página"""
    response = client.get('/pagina')
    assert response.status_code == 200
    assert b'conteudo_esperado' in response.data
```

## 🔧 Troubleshooting

### Problemas Comuns

1. **Testes Falhando por Dependências**
   - Verifique se todas as dependências estão instaladas
   - Execute `pip install -r requirements.txt`

2. **Erro de Banco de Dados**
   - Verifique se o SQLite está disponível
   - Confirme que não há conflitos de schema

3. **Testes Lentos**
   - Use marcador `@pytest.mark.slow` para testes demorados
   - Execute testes rápidos com `pytest -m "not slow"`

4. **Problemas de Autenticação**
   - Verifique se as fixtures de autenticação estão sendo usadas
   - Confirme que o SECRET_KEY está configurado

### Debug

Para debug detalhado:

```bash
# Execução com output detalhado
pytest -v -s tests/

# Parar no primeiro erro
pytest -x tests/

# Debug com pdb
pytest --pdb tests/
```

## 📞 Suporte

Para dúvidas sobre os testes:

1. Consulte esta documentação
2. Verifique os exemplos nos arquivos de teste
3. Execute `pytest --help` para opções do pytest
4. Consulte a documentação oficial do pytest

## 🔄 Integração Contínua

Para integrar com CI/CD:

```yaml
# Exemplo GitHub Actions
- name: Run Tests
  run: |
    python run_tests.py --no-performance
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: test_reports/coverage.xml
```

## 📊 Métricas de Qualidade

O sistema monitora:

- **Cobertura de Código**: Meta > 80%
- **Taxa de Sucesso**: Meta > 95%
- **Performance**: APIs < 500ms
- **Qualidade**: Zero erros críticos

---

**Última atualização**: Janeiro 2024  
**Versão**: 1.0.0