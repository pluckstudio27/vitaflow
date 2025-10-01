"""
Testes para API de usuários
"""
import pytest
import json
from tests.conftest import login_user


@pytest.mark.api
class TestUsuariosAPI:
    """Testes para API de usuários"""
    
    def test_get_usuarios_as_admin(self, client, usuario_admin, usuario_comum, db_session):
        """Testa listagem de usuários como admin"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/usuarios')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'items' in data
        assert len(data['items']) >= 2  # Pelo menos admin e usuário comum
    
    def test_get_usuarios_as_regular_user(self, client, usuario_comum, db_session):
        """Testa listagem de usuários como usuário comum (deve ser negado)"""
        login_user(client, usuario_comum.username, 'senha123')
        
        response = client.get('/api/usuarios')
        assert response.status_code in [403, 401]
    
    def test_get_usuario_by_id(self, client, usuario_admin, usuario_comum, db_session):
        """Testa busca de usuário por ID"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get(f'/api/usuarios/{usuario_comum.id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['id'] == usuario_comum.id
        assert data['nome_completo'] == usuario_comum.nome_completo
        assert data['email'] == usuario_comum.email
    
    def test_get_nonexistent_usuario(self, client, usuario_admin, db_session):
        """Testa busca de usuário inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/usuarios/99999')
        assert response.status_code == 404
    
    def test_create_usuario_as_admin(self, client, usuario_admin, central_teste, categoria_teste, db_session):
        """Testa criação de usuário como admin"""
        login_user(client, usuario_admin.username, 'senha123')
        
        # Criar hierarquia necessária para operador_setor
        from models.hierarchy import Almoxarifado, SubAlmoxarifado, Setor
        
        almoxarifado = Almoxarifado(nome='Almoxarifado Teste', central_id=central_teste.id)
        db_session.add(almoxarifado)
        db_session.flush()
        
        sub_almoxarifado = SubAlmoxarifado(nome='Sub-Almoxarifado Teste', almoxarifado_id=almoxarifado.id)
        db_session.add(sub_almoxarifado)
        db_session.flush()
        
        setor = Setor(nome='Setor Teste', sub_almoxarifado_id=sub_almoxarifado.id)
        db_session.add(setor)
        db_session.commit()
        
        new_user_data = {
            'nome': 'Novo Usuario',
            'login': 'novo_usuario',
            'email': 'novo@teste.com',
            'senha': 'senha123',
            'nivel': 'operador_setor',
            'setor_id': setor.id,
            'categoria_id': categoria_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios', 
                             json=new_user_data,
                             headers={'Content-Type': 'application/json',
                                    'Accept': 'application/json'})
        
        if response.status_code != 201:
            print(f"Status code: {response.status_code}")
            print(f"Response data: {response.get_json()}")
        
        assert response.status_code == 201
        
        data = response.get_json()
        assert data['nome'] == new_user_data['nome']
        assert data['email'] == new_user_data['email']
    
    def test_create_usuario_with_duplicate_username(self, client, usuario_admin, usuario_comum, central_teste, db_session):
        """Testa criação de usuário com username duplicado"""
        login_user(client, usuario_admin.username, 'senha123')
        
        duplicate_user_data = {
            'nome': 'Usuario Duplicado',
            'login': usuario_comum.username,  # Username já existe
            'email': 'email_unico@teste.com',
            'senha': 'senha123',
            'nivel': 'operador_setor',
            'central_id': central_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(duplicate_user_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_create_usuario_with_duplicate_email(self, client, usuario_admin, usuario_comum, central_teste, db_session):
        """Testa criação de usuário com email duplicado"""
        login_user(client, usuario_admin.username, 'senha123')
        
        duplicate_user_data = {
            'nome': 'Usuario Duplicado',
            'login': 'username_unico',
            'email': usuario_comum.email,  # Email já existe
            'senha': 'senha123',
            'nivel': 'operador_setor',
            'central_id': central_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(duplicate_user_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_create_usuario_missing_required_fields(self, client, usuario_admin, db_session):
        """Testa criação de usuário com campos obrigatórios faltando"""
        login_user(client, usuario_admin.username, 'senha123')
        
        incomplete_user_data = {
            'nome': 'Usuario Incompleto',
            # Faltando username, email, password, etc.
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(incomplete_user_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_update_usuario(self, client, usuario_admin, usuario_comum, db_session):
        """Testa atualização de usuário"""
        login_user(client, usuario_admin.username, 'senha123')
        
        update_data = {
            'nome_completo': 'Nome Atualizado',
            'email': 'email_atualizado@teste.com'
        }
        
        response = client.put(f'/api/usuarios/{usuario_comum.id}',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['nome'] == update_data['nome_completo']
        assert data['email'] == update_data['email']
    
    def test_update_nonexistent_usuario(self, client, usuario_admin, db_session):
        """Testa atualização de usuário inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        update_data = {'nome': 'Nome Atualizado'}
        
        response = client.put('/api/usuarios/99999',
                            data=json.dumps(update_data),
                            content_type='application/json')
        assert response.status_code == 404
    
    def test_delete_usuario(self, client, usuario_admin, usuario_comum, db_session):
        """Testa exclusão de usuário"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.delete(f'/api/usuarios/{usuario_comum.id}')
        assert response.status_code == 200
        
        # Verifica se o usuário foi realmente excluído
        response = client.get(f'/api/usuarios/{usuario_comum.id}')
        assert response.status_code == 404
    
    def test_delete_nonexistent_usuario(self, client, usuario_admin, db_session):
        """Testa exclusão de usuário inexistente"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.delete('/api/usuarios/99999')
        assert response.status_code == 404
    
    def test_toggle_usuario_status(self, client, usuario_admin, usuario_comum, db_session):
        """Testa alteração de status do usuário"""
        login_user(client, usuario_admin.username, 'senha123')
        
        original_status = usuario_comum.ativo
        
        response = client.post(f'/api/usuarios/{usuario_comum.id}/toggle-status')
        assert response.status_code == 200
        
        # Verifica se o status foi alterado
        response = client.get(f'/api/usuarios/{usuario_comum.id}')
        data = response.get_json()
        assert data['ativo'] != original_status
    
    def test_reset_usuario_password(self, client, usuario_admin, usuario_comum, db_session):
        """Testa reset de senha do usuário"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.post(f'/api/usuarios/{usuario_comum.id}/reset-password')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'nova_senha' in data
        assert len(data['nova_senha']) >= 8  # Senha deve ter pelo menos 8 caracteres


@pytest.mark.api
class TestUsuariosAPIValidation:
    """Testes de validação para API de usuários"""
    
    def test_create_usuario_invalid_email(self, client, usuario_admin, central_teste, db_session):
        """Testa criação de usuário com email inválido"""
        login_user(client, usuario_admin.username, 'senha123')
        
        invalid_user_data = {
            'nome': 'Usuario Teste',
            'login': 'usuario_teste',
            'email': 'email_invalido',  # Email sem formato válido
            'senha': 'senha123',
            'nivel': 'operador_setor',
            'central_id': central_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(invalid_user_data),
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_create_usuario_weak_password(self, client, usuario_admin, central_teste, db_session):
        """Testa criação de usuário com senha fraca"""
        login_user(client, usuario_admin.username, 'senha123')
        
        weak_password_data = {
            'nome': 'Usuario Teste',
            'login': 'usuario_teste',
            'email': 'teste@teste.com',
            'senha': '123',  # Senha muito fraca
            'nivel': 'operador_setor',
            'central_id': central_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(weak_password_data),
                             content_type='application/json')
        # Pode retornar 400 se houver validação de senha
        assert response.status_code in [201, 400]
    
    def test_create_usuario_invalid_nivel_acesso(self, client, usuario_admin, central_teste, db_session):
        """Testa criação de usuário com nível de acesso inválido"""
        login_user(client, usuario_admin.username, 'senha123')
        
        invalid_level_data = {
            'nome': 'Usuario Teste',
            'username': 'usuario_teste',
            'email': 'teste@teste.com',
            'password': 'senha123',
            'nivel_acesso': 'nivel_inexistente',  # Nível inválido
            'central_id': central_teste.id,
            'ativo': True
        }
        
        response = client.post('/api/usuarios',
                             data=json.dumps(invalid_level_data),
                             content_type='application/json')
        assert response.status_code == 400


@pytest.mark.api
class TestUsuariosAPIPagination:
    """Testes de paginação para API de usuários"""
    
    def test_usuarios_pagination(self, client, usuario_admin, db_session):
        """Testa paginação da listagem de usuários"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/usuarios?page=1&per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'pages' in data
        assert 'page' in data
        assert 'per_page' in data
    
    def test_usuarios_search(self, client, usuario_admin, usuario_comum, db_session):
        """Testa busca de usuários"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get(f'/api/usuarios?search={usuario_comum.nome_completo}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['items']) >= 1
        # Verifica se o usuário encontrado contém o termo buscado
        found_user = next((u for u in data['items'] if u['id'] == usuario_comum.id), None)
        assert found_user is not None