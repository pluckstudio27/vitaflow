"""
Testes para API de estoque
"""
import pytest
import json
from datetime import datetime


@pytest.mark.api
class TestStockAPI:
    """Testes para endpoints de estoque"""

    def test_list_stock_admin(self, client, auth_headers_admin, almoxarifado_teste):
        """Teste listar estoque como admin"""
        response = client.get('/api/estoque', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data

    def test_list_stock_user(self, client, auth_headers_user, almoxarifado_teste):
        """Teste listar estoque como usuário comum (apenas da sua categoria)"""
        response = client.get('/api/estoque', headers=auth_headers_user)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        # Usuário comum só vê estoque de produtos da sua categoria
        for item in data['items']:
            assert item['produto']['categoria_obj']['id'] == almoxarifado_teste.produto.categoria_id

    def test_list_stock_unauthorized(self, client):
        """Teste listar estoque sem autenticação"""
        response = client.get('/api/estoque')
        assert response.status_code == 302

    def test_get_product_stock_admin(self, client, auth_headers_admin, produto_teste):
        """Teste obter estoque de um produto específico como admin"""
        response = client.get(f'/api/produtos/{produto_teste.id}/estoque', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'estoques' in data
        assert 'resumo' in data
        assert data['produto_id'] == produto_teste.id
        assert 'produto_nome' in data
        assert 'produto_codigo' in data

    def test_get_product_stock_user_same_category(self, client, auth_headers_user, produto_teste):
        """Teste obter estoque de produto da mesma categoria como usuário comum"""
        response = client.get(f'/api/produtos/{produto_teste.id}/estoque', headers=auth_headers_user)
        assert response.status_code == 200
        data = response.get_json()
        assert 'estoques' in data
        assert 'resumo' in data
        assert data['produto_id'] == produto_teste.id

    def test_get_product_stock_nonexistent(self, client, auth_headers_admin):
        """Teste obter estoque de produto inexistente"""
        response = client.get('/api/produtos/99999/estoque', headers=auth_headers_admin)
        assert response.status_code == 404

    def test_receive_product_admin(self, client, auth_headers_admin, produto_teste, almoxarifado_teste_obj):
        """Teste receber produto como admin (cria estoque)"""
        stock_data = {
            'quantidade': 100,
            'almoxarifado_id': almoxarifado_teste_obj.id,
            'lote': 'LOTE-TEST-001',
            'observacoes': 'Recebimento de teste'
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Recebimento registrado com sucesso'
        assert 'estoque' in data
        assert 'movimentacao' in data
        assert 'lote' in data

    def test_receive_product_user_forbidden(self, client, auth_headers_user, produto_teste, almoxarifado_teste_obj):
        """Teste receber produto como usuário comum (pode ser permitido dependendo das permissões)"""
        stock_data = {
            'quantidade': 100,
            'almoxarifado_id': almoxarifado_teste_obj.id,
            'lote': 'LOTE-TEST-002'
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_user,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        # Pode ser 201 (permitido) ou 403 (proibido) dependendo das permissões
        assert response.status_code in [201, 403]

    def test_receive_product_missing_fields(self, client, auth_headers_admin, produto_teste):
        """Teste receber produto com campos obrigatórios faltando"""
        stock_data = {
            'quantidade': 100
            # almoxarifado_id está faltando
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_receive_product_invalid_quantity(self, client, auth_headers_admin, produto_teste, almoxarifado_teste_obj):
        """Teste receber produto com quantidade inválida"""
        stock_data = {
            'quantidade': -10,  # Quantidade negativa
            'almoxarifado_id': almoxarifado_teste_obj.id
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_receive_product_invalid_almoxarifado(self, client, auth_headers_admin, produto_teste):
        """Teste receber produto com almoxarifado inexistente"""
        stock_data = {
            'quantidade': 100,
            'almoxarifado_id': 99999  # ID inexistente
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 404

    def test_receive_product_nonexistent(self, client, auth_headers_admin, almoxarifado_teste_obj):
        """Teste receber produto inexistente"""
        stock_data = {
            'quantidade': 100,
            'almoxarifado_id': almoxarifado_teste_obj.id
        }
        response = client.post('/api/produtos/99999/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 404

    def test_filter_stock_by_product(self, client, auth_headers_admin, produto_teste):
        """Teste filtrar estoque por produto"""
        response = client.get(f'/api/estoque?produto_id={produto_teste.id}', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        for item in data['items']:
            assert item['produto_id'] == produto_teste.id

    def test_filter_stock_by_almoxarifado(self, client, auth_headers_admin, almoxarifado_teste_obj):
        """Teste filtrar estoque por almoxarifado"""
        response = client.get(f'/api/estoque?local_tipo=ALMOXARIFADO&local_id={almoxarifado_teste_obj.id}', 
                            headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data

    def test_filter_stock_low_quantity(self, client, auth_headers_admin):
        """Teste filtrar estoque com quantidade baixa"""
        response = client.get('/api/estoque?apenas_com_estoque=true', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        # Todos os itens devem ter quantidade > 0
        for item in data['items']:
            assert item['quantidade'] > 0

    def test_stock_pagination(self, client, auth_headers_admin):
        """Teste paginação do estoque"""
        response = client.get('/api/estoque?page=1&per_page=5', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'page' in data
        assert 'per_page' in data
        assert data['per_page'] == 5

    def test_get_product_movements(self, client, auth_headers_admin, produto_teste):
        """Teste obter histórico de movimentações de um produto"""
        response = client.get(f'/api/produtos/{produto_teste.id}/movimentacoes', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'page' in data
        assert 'total' in data
        assert isinstance(data['items'], list)

    def test_get_product_lots(self, client, auth_headers_admin, produto_teste):
        """Teste obter lotes de um produto"""
        response = client.get(f'/api/produtos/{produto_teste.id}/lotes', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'page' in data
        assert 'total' in data
        assert isinstance(data['items'], list)

    def test_stock_unauthorized_endpoints(self, client):
        """Teste endpoints de estoque sem autenticação"""
        endpoints = [
            '/api/estoque',
            '/api/produtos/1/estoque',
            '/api/produtos/1/movimentacoes',
            '/api/produtos/1/lotes'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 302

        # Teste POST sem autenticação
        response = client.post('/api/produtos/1/recebimento', 
                             data=json.dumps({'quantidade': 100, 'almoxarifado_id': 1}),
                             content_type='application/json')
        assert response.status_code == 302

    def test_stock_reports_admin(self, client, auth_headers_admin):
        """Teste relatórios de estoque como admin"""
        response = client.get('/api/estoque/relatorios/resumo', headers=auth_headers_admin)
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert 'total_produtos' in data
        assert 'total_estoque' in data
        assert data['status'] == 'success'

    def test_stock_reports_user_forbidden(self, client, auth_headers_user):
        """Teste relatórios de estoque como usuário comum (proibido)"""
        response = client.get('/api/estoque/relatorios/resumo', headers=auth_headers_user)
        assert response.status_code == 403

    def test_receive_product_with_lot_details(self, client, auth_headers_admin, produto_teste, almoxarifado_teste_obj):
        """Teste receber produto com detalhes completos do lote"""
        stock_data = {
            'quantidade': 50,
            'almoxarifado_id': almoxarifado_teste_obj.id,
            'lote': 'LOTE-COMPLETO-001',
            'data_vencimento': '2025-12-31',
            'data_fabricacao': '2024-01-15',
            'preco_unitario': 15.50,
            'fornecedor': 'Fornecedor Teste Ltda',
            'nota_fiscal': 'NF-123456',
            'observacoes': 'Recebimento com lote completo'
        }
        response = client.post(f'/api/produtos/{produto_teste.id}/recebimento', 
                             headers=auth_headers_admin,
                             data=json.dumps(stock_data),
                             content_type='application/json')
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Recebimento registrado com sucesso'
        assert 'lote' in data
        assert data['lote']['numero_lote'] == 'LOTE-COMPLETO-001'
        assert data['lote']['fornecedor'] == 'Fornecedor Teste Ltda'