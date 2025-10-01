"""
Testes para autenticação e autorização
"""
import pytest
from flask import url_for
from tests.conftest import login_user, logout_user


@pytest.mark.auth
class TestAuthentication:
    """Testes de autenticação"""
    
    def test_login_page_loads(self, client):
        """Testa se a página de login carrega corretamente"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_login_with_valid_credentials(self, client, usuario_admin, db_session):
        """Testa login com credenciais válidas"""
        response = login_user(client, usuario_admin.username, 'senha123')
        assert response.status_code == 200
        # Verifica se foi redirecionado para a página principal
        assert b'dashboard' in response.data.lower() or b'almox' in response.data.lower()
    
    def test_login_with_invalid_username(self, client, db_session):
        """Testa login com username inválido"""
        response = login_user(client, 'usuario_inexistente', 'senha123')
        assert response.status_code == 200
        assert b'erro' in response.data.lower() or b'inv' in response.data.lower()
    
    def test_login_with_invalid_password(self, client, usuario_admin, db_session):
        """Testa login com senha inválida"""
        response = login_user(client, usuario_admin.username, 'senha_errada')
        assert response.status_code == 200
        assert b'erro' in response.data.lower() or b'inv' in response.data.lower()
    
    def test_login_with_inactive_user(self, client, usuario_admin, db_session):
        """Testa login com usuário inativo"""
        usuario_admin.ativo = False
        db_session.commit()
        
        response = login_user(client, usuario_admin.username, 'senha123')
        assert response.status_code == 200
        assert b'inativo' in response.data.lower() or b'erro' in response.data.lower()
    
    def test_logout(self, client, usuario_admin, db_session):
        """Testa logout do usuário"""
        # Primeiro faz login
        login_user(client, usuario_admin.username, 'senha123')
        
        # Depois faz logout
        response = logout_user(client)
        assert response.status_code == 200
        
        # Verifica se foi redirecionado para login
        response = client.get('/')
        assert response.status_code == 302 or b'login' in response.data.lower()


@pytest.mark.auth
class TestAuthorization:
    """Testes de autorização e controle de acesso"""
    
    def test_access_without_login(self, client):
        """Testa acesso a páginas protegidas sem login"""
        protected_urls = [
            '/',
            '/usuarios',
            '/produtos',
            '/categorias',
            '/configuracoes',
            '/movimentacoes'
        ]
        
        for url in protected_urls:
            response = client.get(url)
            # Deve redirecionar para login ou retornar 401/403
            assert response.status_code in [302, 401, 403]
    
    def test_admin_access_to_users_page(self, client, usuario_admin, db_session):
        """Testa acesso de admin à página de usuários"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/usuarios')
        assert response.status_code == 200
    
    def test_regular_user_access_to_users_page(self, client, usuario_comum, db_session):
        """Testa acesso de usuário comum à página de usuários (deve ser negado)"""
        login_user(client, usuario_comum.username, 'senha123')
        
        response = client.get('/usuarios')
        # Usuário comum não deve ter acesso à gestão de usuários
        assert response.status_code in [403, 302]
    
    def test_user_access_to_products_page(self, client, usuario_comum, db_session):
        """Testa acesso de usuário comum à página de produtos"""
        login_user(client, usuario_comum.username, 'senha123')
        
        response = client.get('/produtos')
        assert response.status_code == 200
    
    def test_admin_access_to_categories_page(self, client, usuario_admin, db_session):
        """Testa acesso de admin à página de categorias"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/categorias')
        assert response.status_code == 200
    
    def test_user_profile_access(self, client, usuario_comum, db_session):
        """Testa acesso ao perfil do usuário"""
        login_user(client, usuario_comum.username, 'senha123')
        
        response = client.get('/auth/profile')
        assert response.status_code == 200
        assert usuario_comum.nome_completo.encode() in response.data


@pytest.mark.auth
@pytest.mark.api
class TestAPIAuthentication:
    """Testes de autenticação para APIs"""
    
    def test_api_access_without_auth(self, client):
        """Testa acesso a APIs sem autenticação"""
        api_endpoints = [
            '/api/usuarios',
            '/api/produtos',
            '/api/categorias',
            '/api/centrais'
        ]
        
        for endpoint in api_endpoints:
            response = client.get(endpoint)
            # APIs devem retornar 401 sem autenticação
            assert response.status_code in [401, 302]
    
    def test_api_access_with_admin_auth(self, client, usuario_admin, db_session):
        """Testa acesso a APIs com autenticação de admin"""
        login_user(client, usuario_admin.username, 'senha123')
        
        response = client.get('/api/usuarios')
        assert response.status_code == 200
        
        response = client.get('/api/produtos')
        assert response.status_code == 200
    
    def test_api_access_with_user_auth(self, client, usuario_comum, db_session):
        """Testa acesso a APIs com autenticação de usuário comum"""
        login_user(client, usuario_comum.username, 'senha123')
        
        # Usuário comum não deve acessar API de usuários
        response = client.get('/api/usuarios')
        assert response.status_code in [403, 401]
        
        # Mas deve acessar API de produtos
        response = client.get('/api/produtos')
        assert response.status_code == 200


@pytest.mark.auth
class TestPasswordSecurity:
    """Testes de segurança de senhas"""
    
    def test_password_hashing(self, usuario_admin):
        """Testa se as senhas são hasheadas corretamente"""
        # A senha não deve estar em texto plano
        assert usuario_admin.password_hash != 'senha123'
        assert len(usuario_admin.password_hash) > 20  # Hash deve ter tamanho razoável
    
    def test_password_verification(self, usuario_admin):
        """Testa verificação de senha"""
        from werkzeug.security import check_password_hash
        
        # Senha correta deve ser verificada
        assert check_password_hash(usuario_admin.password_hash, 'senha123')
        
        # Senha incorreta não deve ser verificada
        assert not check_password_hash(usuario_admin.password_hash, 'senha_errada')


@pytest.mark.auth
class TestSessionManagement:
    """Testes de gerenciamento de sessão"""
    
    def test_session_persistence(self, client, usuario_admin, db_session):
        """Testa persistência da sessão"""
        # Faz login
        login_user(client, usuario_admin.username, 'senha123')
        
        # Acessa página protegida
        response = client.get('/')
        assert response.status_code == 200
        
        # Acessa outra página protegida (sessão deve persistir)
        response = client.get('/produtos')
        assert response.status_code == 200
    
    def test_session_cleanup_on_logout(self, client, usuario_admin, db_session):
        """Testa limpeza da sessão no logout"""
        # Faz login
        login_user(client, usuario_admin.username, 'senha123')
        
        # Verifica acesso
        response = client.get('/')
        assert response.status_code == 200
        
        # Faz logout
        logout_user(client)
        
        # Verifica se perdeu acesso
        response = client.get('/')
        assert response.status_code in [302, 401, 403]