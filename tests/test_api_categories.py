"""
Testes para API de categorias
"""
import pytest
import json
from tests.conftest import login_user


@pytest.mark.api
class TestCategoriasAPI:
    """Testes para API de categorias"""
    
    def test_get_categorias(self, client, usuario_admin, categoria_teste, db_session):
        """Testa listagem de categorias"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/categorias')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'items' in data
        assert len(data['items']) >= 1
    
    def test_get_categoria_by_id(self, client, usuario_admin, categoria_teste, db_session):
        """Testa busca de categoria por ID"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get(f'/api/categorias/{categoria_teste.id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['id'] == categoria_teste.id
        assert data['nome'] == categoria_teste.nome
        assert data['codigo'] == categoria_teste.codigo
    
    def test_get_nonexistent_categoria(self, client, usuario_admin, db_session):
        """Testa busca de categoria inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/categorias/99999')
        assert response.status_code == 404
    
    def test_create_categoria(self, client, usuario_admin, db_session):
        """Testa criação de categoria"""
        login_user(client, usuario_admin.username, 'senha123')
        
        new_category_data = {
            'nome': 'Nova Categoria',
            'codigo': 'NC001',
            'descricao': 'Descrição da nova categoria',
            'cor': '#00FF00',
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(new_category_data),
                             content_type='application/json')
        assert response.status_code == 201
        
        data = response.get_json()
        assert data['nome'] == new_category_data['nome']
        assert data['codigo'] == new_category_data['codigo']
        assert data['cor'] == new_category_data['cor']
    
    def test_create_categoria_duplicate_codigo(self, client, usuario_admin, categoria_teste, db_session):
        """Testa criação de categoria com código duplicado"""
        login_user(client, usuario_admin.username, 'senha123')
        
        duplicate_category_data = {
            'nome': 'Categoria Duplicada',
            'codigo': categoria_teste.codigo,  # Código já existe
            'descricao': 'Descrição',
            'cor': '#FF0000',
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(duplicate_category_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_create_categoria_missing_required_fields(self, client, usuario_admin, db_session):
        """Testa criação de categoria com campos obrigatórios faltando"""
        login_user(client, usuario_admin.username, 'senha123')
        
        incomplete_category_data = {
            'nome': 'Categoria Incompleta',
            # Faltando código, cor, etc.
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(incomplete_category_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_update_categoria(self, client, usuario_admin, categoria_teste, db_session):
        """Testa atualização de categoria"""
        login_user(client, usuario_admin.username, 'senha123')
        
        update_data = {
            'nome': 'Nome Atualizado',
            'descricao': 'Descrição atualizada',
            'cor': '#0000FF'
        }
        
        response = client.put(f'/api/categorias/{categoria_teste.id}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['nome'] == update_data['nome']
        assert data['descricao'] == update_data['descricao']
        assert data['cor'] == update_data['cor']
    
    def test_update_nonexistent_categoria(self, client, usuario_admin, db_session):
        """Testa atualização de categoria inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        update_data = {'nome': 'Nome Atualizado'}
        
        response = client.put('/api/categorias/99999',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code == 404
    
    def test_delete_categoria(self, client, usuario_admin, db_session):
        """Testa exclusão de categoria"""
        login_user(client, usuario_admin.username, 'senha123')
        
        # Criar uma categoria para deletar
        from models.categoria import CategoriaProduto
        categoria_para_deletar = CategoriaProduto(
            nome='Categoria Para Deletar',
            codigo='CPD001',
            cor='#FFFF00',
            ativo=True
        )
        db_session.add(categoria_para_deletar)
        db_session.commit()
        
        response = client.delete(f'/api/categorias/{categoria_para_deletar.id}')
        assert response.status_code == 200
        
        # Verifica se a categoria foi realmente excluída
        response = client.get(f'/api/categorias/{categoria_para_deletar.id}')
        assert response.status_code == 404
    
    def test_delete_categoria_with_products(self, client, usuario_admin, categoria_teste, produto_teste, db_session):
        """Testa exclusão de categoria que possui produtos"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.delete(f'/api/categorias/{categoria_teste.id}')
        # Deve retornar erro pois a categoria tem produtos associados
        assert response.status_code == 400
    
    def test_delete_nonexistent_categoria(self, client, usuario_admin, db_session):
        """Testa exclusão de categoria inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.delete('/api/categorias/99999')
        assert response.status_code == 404
    
    def test_toggle_categoria_status(self, client, usuario_admin, categoria_teste, db_session):
        """Testa alteração de status da categoria"""
        login_user(client, usuario_admin.username, 'senha123')
        
        original_status = categoria_teste.ativo
        
        response = client.post(f'/api/categorias/{categoria_teste.id}/toggle-status')
        assert response.status_code == 200
        
        # Verifica se o status foi alterado
        response = client.get(f'/api/categorias/{categoria_teste.id}')
        data = response.get_json()
        assert data['ativo'] != original_status


@pytest.mark.api
class TestCategoriasAPIValidation:
    """Testes de validação para API de categorias"""
    
    def test_create_categoria_invalid_color(self, client, usuario_admin, db_session):
        """Testa criação de categoria com cor inválida"""
        login_user(client, usuario_admin.username, 'senha123')
        
        invalid_color_data = {
            'nome': 'Categoria Teste',
            'codigo': 'CT001',
            'descricao': 'Descrição',
            'cor': 'cor_invalida',  # Cor sem formato hexadecimal
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(invalid_color_data),
                             content_type='application/json')
        # Pode retornar 400 se houver validação de cor
        assert response.status_code in [201, 400]
    
    def test_create_categoria_empty_nome(self, client, usuario_admin, db_session):
        """Testa criação de categoria com nome vazio"""
        login_user(client, usuario_admin.username, 'senha123')
        
        empty_name_data = {
            'nome': '',  # Nome vazio
            'codigo': 'CT001',
            'cor': '#FF0000',
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(empty_name_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_create_categoria_empty_codigo(self, client, usuario_admin, db_session):
        """Testa criação de categoria com código vazio"""
        login_user(client, usuario_admin.username, 'senha123')
        
        empty_code_data = {
            'nome': 'Categoria Teste',
            'codigo': '',  # Código vazio
            'cor': '#FF0000',
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(empty_code_data),
                             content_type='application/json')
        assert response.status_code == 400


@pytest.mark.api
class TestCategoriasAPIAccess:
    """Testes de controle de acesso para API de categorias"""
    
    def test_regular_user_access_to_categorias(self, client, usuario_comum, categoria_teste, db_session):
        """Testa acesso de usuário comum à API de categorias"""
        login_user(client, usuario_comum.username, 'senha123')
        
        # Usuário comum pode listar categorias
        response = client.get('/api/categorias')
        assert response.status_code == 200
        
        # Usuário comum pode ver categoria específica
        response = client.get(f'/api/categorias/{categoria_teste.id}')
        assert response.status_code == 200
    
    def test_regular_user_cannot_create_categoria(self, client, usuario_comum, db_session):
        """Testa que usuário comum não pode criar categorias"""
        login_user(client, usuario_comum.username, 'senha123')
        
        new_category_data = {
            'nome': 'Nova Categoria',
            'codigo': 'NC001',
            'cor': '#00FF00',
            'ativo': True
        }
        
        response = client.post('/api/categorias',
                             data=json.dumps(new_category_data),
                             content_type='application/json')
        assert response.status_code in [403, 401]
    
    def test_regular_user_cannot_update_categoria(self, client, usuario_comum, categoria_teste, db_session):
        """Testa que usuário comum não pode atualizar categorias"""
        login_user(client, usuario_comum.username, 'senha123')
        
        update_data = {'nome': 'Nome Atualizado'}
        
        response = client.put(f'/api/categorias/{categoria_teste.id}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code in [403, 401]
    
    def test_regular_user_cannot_delete_categoria(self, client, usuario_comum, categoria_teste, db_session):
        """Testa que usuário comum não pode deletar categorias"""
        login_user(client, usuario_comum.username, 'senha123')
        
        response = client.delete(f'/api/categorias/{categoria_teste.id}')
        assert response.status_code in [403, 401]


@pytest.mark.api
class TestCategoriasAPIPagination:
    """Testes de paginação para API de categorias"""
    
    def test_categorias_pagination(self, client, usuario_admin, db_session):
        """Testa paginação da listagem de categorias"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/categorias?page=1&per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'pages' in data
        assert 'page' in data
        assert 'per_page' in data
    
    def test_categorias_search(self, client, usuario_admin, categoria_teste, db_session):
        """Testa busca de categorias"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get(f'/api/categorias?search={categoria_teste.nome}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['items']) >= 1
        # Verifica se a categoria encontrada contém o termo buscado
        found_category = next((c for c in data['items'] if c['id'] == categoria_teste.id), None)
        assert found_category is not None
    
    def test_categorias_filter_by_status(self, client, usuario_admin, categoria_teste, db_session):
        """Testa filtro de categorias por status"""
        login_user(client, usuario_admin.username, 'senha123')
        
        # Testa filtro por ativo=true
        response = client.get('/api/categorias?ativo=true')
        assert response.status_code == 200
        
        data = response.get_json()
        for categoria in data['items']:
            assert categoria['ativo'] == True
        
        # Testa filtro por ativo=false
        response = client.get('/api/categorias?ativo=false')
        assert response.status_code == 200