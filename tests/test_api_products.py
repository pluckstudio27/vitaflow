"""
Testes para API de produtos
"""
import pytest
import json
from datetime import datetime


@pytest.mark.api
class TestProductsAPI:
    """Testes para endpoints de produtos"""

    def test_list_products_admin(self, client, auth_headers_admin, categoria_teste, produto_teste):
        """Teste listar produtos como admin"""
        response = client.get('/api/produtos', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'produtos' in data
        assert 'total' in data
        assert 'pagina' in data
        assert 'por_pagina' in data
        assert len(data['produtos']) >= 1

    def test_list_products_user(self, client, auth_headers_user, categoria_teste, produto_teste):
        """Teste listar produtos como usuário comum (apenas da sua categoria)"""
        response = client.get('/api/produtos', headers=auth_headers_user)
        assert response.status_code == 200
        data = response.get_json()
        assert 'produtos' in data
        # Usuário comum só vê produtos da sua categoria
        for produto in data['produtos']:
            assert produto['categoria_obj']['id'] == categoria_teste.id

    def test_list_products_unauthorized(self, client):
        """Teste listar produtos sem autenticação"""
        response = client.get('/api/produtos')
        assert response.status_code == 401

    def test_get_product_by_id_admin(self, client, auth_headers_admin, produto_teste):
        """Teste obter produto por ID como admin"""
        response = client.get(f'/api/produtos/{produto_teste.id}', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == produto_teste.id
        assert data['nome'] == produto_teste.nome
        assert data['codigo'] == produto_teste.codigo
        assert 'categoria_obj' in data

    def test_get_product_by_id_user_same_category(self, client, auth_headers_user, produto_teste):
        """Teste obter produto da mesma categoria como usuário comum"""
        response = client.get(f'/api/produtos/{produto_teste.id}', headers=auth_headers_user)
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == produto_teste.id

    def test_get_product_by_id_user_different_category(self, client, auth_headers_user, categoria_teste, db_session):
        """Teste obter produto de categoria diferente como usuário comum"""
        from models.produto import Produto
        from models.categoria import CategoriaProduto
        
        # Criar categoria diferente
        categoria_2 = CategoriaProduto(nome='Categoria 2', codigo='CAT002', ativo=True)
        db_session.add(categoria_2)
        db_session.commit()
        
        produto_outra_categoria = Produto(
            nome='Produto Outra Categoria',
            codigo='PROD002',
            categoria_id=categoria_2.id,
            ativo=True
        )
        db_session.add(produto_outra_categoria)
        db_session.commit()
        
        response = client.get(f'/api/produtos/{produto_outra_categoria.id}', headers=auth_headers_user)
        assert response.status_code == 403

    def test_get_product_nonexistent(self, client, auth_headers_admin):
        """Teste obter produto inexistente"""
        response = client.get('/api/produtos/99999', headers=auth_headers_admin)
        assert response.status_code == 404

    def test_create_product_admin(self, client, auth_headers_admin, categoria_teste, central_teste):
        """Teste criar produto como admin"""
        data = {
            'nome': 'Produto Teste Criado',
            'codigo': 'PROD_CRIADO',
            'categoria_id': categoria_teste.id,
            'central_id': central_teste.id,
            'descricao': 'Produto criado via teste'
        }
        response = client.post('/api/produtos',
                             data=json.dumps(data),
                             content_type='application/json',
                             headers=auth_headers_admin)
        assert response.status_code == 201
        response_data = response.get_json()
        assert response_data['nome'] == data['nome']
        assert response_data['codigo'] == data['codigo']

    def test_create_product_user_forbidden(self, client, auth_headers_user, categoria_teste, central_teste):
        """Teste criar produto como usuário comum (deve ser negado)"""
        data = {
            'nome': 'Produto Teste User',
            'codigo': 'PROD_USER',
            'categoria_id': categoria_teste.id,
            'central_id': central_teste.id,
            'descricao': 'Produto criado por usuário'
        }
        response = client.post('/api/produtos',
                             data=json.dumps(data),
                             content_type='application/json',
                             headers=auth_headers_user)
        assert response.status_code == 403

    def test_create_product_duplicate_code(self, client, auth_headers_admin, produto_teste, categoria_teste, central_teste):
        """Teste criar produto com código duplicado"""
        data = {
            'nome': 'Produto Duplicado',
            'codigo': produto_teste.codigo,  # Código já existe
            'categoria_id': categoria_teste.id,
            'central_id': central_teste.id,
            'descricao': 'Produto com código duplicado'
        }
        response = client.post('/api/produtos',
                             data=json.dumps(data),
                             content_type='application/json',
                             headers=auth_headers_admin)
        assert response.status_code == 400

    def test_create_product_missing_fields(self, client, auth_headers_admin):
        """Teste criar produto com campos obrigatórios faltando"""
        data = {
            'nome': 'Produto Incompleto'
            # Faltando código e categoria_id
        }
        response = client.post('/api/produtos',
                             data=json.dumps(data),
                             content_type='application/json',
                             headers=auth_headers_admin)
        assert response.status_code == 400

    def test_create_product_invalid_category(self, client, auth_headers_admin):
        """Teste criar produto com categoria inexistente"""
        data = {
            'nome': 'Produto Categoria Inválida',
            'codigo': 'PROD_INVALID',
            'categoria_id': 99999,  # Categoria inexistente
            'descricao': 'Produto com categoria inválida'
        }
        response = client.post('/api/produtos',
                             data=json.dumps(data),
                             content_type='application/json',
                             headers=auth_headers_admin)
        assert response.status_code == 400

    def test_update_product_admin(self, client, auth_headers_admin, produto_teste):
        """Teste atualizar produto como admin"""
        data = {
            'nome': 'Produto Atualizado',
            'descricao': 'Descrição atualizada'
        }
        response = client.put(f'/api/produtos/{produto_teste.id}',
                            data=json.dumps(data),
                            content_type='application/json',
                            headers=auth_headers_admin)
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['nome'] == data['nome']
        assert response_data['descricao'] == data['descricao']

    def test_update_product_user_forbidden(self, client, auth_headers_user, produto_teste):
        """Teste atualizar produto como usuário comum (deve ser negado)"""
        data = {
            'nome': 'Produto Atualizado User'
        }
        response = client.put(f'/api/produtos/{produto_teste.id}',
                            data=json.dumps(data),
                            content_type='application/json',
                            headers=auth_headers_user)
        assert response.status_code == 403

    def test_update_product_nonexistent(self, client, auth_headers_admin):
        """Teste atualizar produto inexistente"""
        data = {
            'nome': 'Produto Inexistente'
        }
        response = client.put('/api/produtos/99999',
                            data=json.dumps(data),
                            content_type='application/json',
                            headers=auth_headers_admin)
        assert response.status_code == 404

    def test_delete_product_admin(self, client, auth_headers_admin, db_session, categoria_teste, central_teste):
        """Teste excluir produto como admin"""
        from models.produto import Produto
        
        # Criar produto para deletar
        produto_deletar = Produto(
            nome='Produto Para Deletar',
            codigo='PROD_DELETE',
            categoria_id=categoria_teste.id,
            central_id=central_teste.id,
            ativo=True
        )
        db_session.add(produto_deletar)
        db_session.commit()
        
        response = client.delete(f'/api/produtos/{produto_deletar.id}', headers=auth_headers_admin)
        assert response.status_code == 200

    def test_delete_product_user_forbidden(self, client, auth_headers_user, produto_teste):
        """Teste excluir produto como usuário comum (deve ser negado)"""
        response = client.delete(f'/api/produtos/{produto_teste.id}', headers=auth_headers_user)
        assert response.status_code == 403

    def test_delete_product_nonexistent(self, client, auth_headers_admin):
        """Teste excluir produto inexistente"""
        response = client.delete('/api/produtos/99999', headers=auth_headers_admin)
        assert response.status_code == 404

    def test_toggle_product_status_admin(self, client, auth_headers_admin, produto_teste):
        """Teste alternar status do produto como admin"""
        original_status = produto_teste.ativo
        response = client.patch(f'/api/produtos/{produto_teste.id}/toggle-status',
                              headers=auth_headers_admin)
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['ativo'] != original_status

    def test_toggle_product_status_user_forbidden(self, client, auth_headers_user, produto_teste):
        """Teste alternar status do produto como usuário comum (deve ser negado)"""
        response = client.patch(f'/api/produtos/{produto_teste.id}/toggle-status',
                              headers=auth_headers_user)
        assert response.status_code == 403

    def test_search_products(self, client, auth_headers_admin, produto_teste):
        """Teste buscar produtos por nome"""
        response = client.get(f'/api/produtos?search={produto_teste.nome[:5]}',
                            headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'produtos' in data
        
        # Verificar se o produto encontrado contém o termo de busca
        found = False
        for produto in data['produtos']:
            if produto_teste.nome.lower() in produto['nome'].lower():
                found = True
                break
        assert found

    def test_filter_products_by_category(self, client, auth_headers_admin, categoria_teste, produto_teste):
        """Teste filtrar produtos por categoria"""
        response = client.get(f'/api/produtos?categoria_id={categoria_teste.id}',
                            headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        for produto in data['produtos']:
            assert produto['categoria_obj']['id'] == categoria_teste.id

    def test_filter_products_by_status(self, client, auth_headers_admin):
        """Teste filtrar produtos por status"""
        # Testar produtos ativos
        response = client.get('/api/produtos?ativo=true', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        for produto in data['produtos']:
            assert produto['ativo'] == True
        
        # Testar produtos inativos
        response = client.get('/api/produtos?ativo=false', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        for produto in data['produtos']:
            assert produto['ativo'] == False

    def test_products_pagination(self, client, auth_headers_admin):
        """Teste paginação de produtos"""
        # Testar primeira página
        response = client.get('/api/produtos?pagina=1&por_pagina=5', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'produtos' in data
        assert 'total' in data
        assert 'pagina' in data
        assert 'por_pagina' in data
        assert data['pagina'] == 1
        assert data['por_pagina'] == 5

    def test_products_unauthorized_endpoints(self, client):
        """Teste endpoints de produtos sem autenticação"""
        endpoints = [
            '/api/produtos',
            '/api/produtos/1',
            '/api/produtos/1/toggle-status'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401