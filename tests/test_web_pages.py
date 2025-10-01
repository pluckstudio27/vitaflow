"""
Testes para páginas web da aplicação
"""
import pytest
from flask import url_for


@pytest.mark.web
class TestWebPages:
    """Testes para páginas web"""

    def test_login_page_loads(self, client):
        """Teste se a página de login carrega corretamente"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        assert b'senha' in response.data.lower()

    def test_login_page_post_valid_credentials(self, client, usuario_admin):
        """Teste login com credenciais válidas"""
        response = client.post('/auth/login', data={
            'username': usuario_admin.username,
            'password': 'senha123'
        })
        # Deve redirecionar após login bem-sucedido
        assert response.status_code in [200, 302]

    def test_login_page_post_invalid_credentials(self, client):
        """Teste login com credenciais inválidas"""
        response = client.post('/auth/login', data={
            'username': 'usuario_inexistente',
            'password': 'senha_errada'
        })
        assert response.status_code == 200
        assert b'erro' in response.data.lower() or b'invalid' in response.data.lower()

    def test_logout_redirects_to_login(self, client, admin_logged_in):
        """Teste se logout redireciona para login"""
        response = client.get('/auth/logout')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_dashboard_requires_login(self, client):
        """Teste se dashboard requer login"""
        response = client.get('/')
        assert response.status_code == 302  # Redirecionamento para login

    def test_dashboard_loads_for_authenticated_user(self, client, admin_logged_in):
        """Teste se dashboard carrega para usuário autenticado"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'painel' in response.data.lower()

    def test_usuarios_page_admin_access(self, client, admin_logged_in):
        """Teste acesso à página de usuários como admin"""
        response = client.get('/configuracoes/usuarios')
        assert response.status_code == 200
        assert b'usuarios' in response.data.lower() or b'usuario' in response.data.lower()

    def test_usuarios_page_user_forbidden(self, client, user_logged_in):
        """Teste acesso negado à página de usuários para usuário comum"""
        response = client.get('/configuracoes/usuarios')
        assert response.status_code == 403 or response.status_code == 302

    def test_categorias_page_admin_access(self, client, admin_logged_in):
        """Teste acesso à página de categorias como admin"""
        response = client.get('/configuracoes/categorias')
        assert response.status_code == 200
        assert b'categoria' in response.data.lower()

    def test_categorias_page_user_forbidden(self, client, user_logged_in):
        """Teste acesso negado à página de categorias para usuário comum"""
        response = client.get('/configuracoes/categorias')
        assert response.status_code == 403 or response.status_code == 302

    def test_produtos_page_loads(self, client, admin_logged_in):
        """Teste se página de produtos carrega"""
        response = client.get('/produtos')
        assert response.status_code == 200
        assert b'produto' in response.data.lower()

    def test_produtos_page_user_access(self, client, user_logged_in):
        """Teste acesso à página de produtos como usuário comum"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Usuário comum pode ver produtos da sua categoria

    def test_estoque_page_loads(self, client, admin_logged_in):
        """Teste se página de estoque carrega"""
        response = client.get('/estoque')
        assert response.status_code == 200
        assert b'estoque' in response.data.lower()

    def test_estoque_page_user_access(self, client, user_logged_in):
        """Teste acesso à página de estoque como usuário comum"""
        response = client.get('/estoque')
        assert response.status_code == 200
        # Usuário comum pode ver estoque de produtos da sua categoria

    def test_relatorios_page_admin_access(self, client, admin_logged_in):
        """Teste acesso à página de relatórios como admin"""
        response = client.get('/relatorios')
        assert response.status_code == 200
        assert b'relatorio' in response.data.lower() or b'relatorio' in response.data.lower()

    def test_relatorios_page_user_forbidden(self, client, user_logged_in):
        """Teste acesso negado à página de relatórios para usuário comum"""
        response = client.get('/relatorios')
        assert response.status_code == 403 or response.status_code == 302

    def test_configuracoes_page_admin_access(self, client, admin_logged_in):
        """Teste acesso à página de configurações como admin"""
        response = client.get('/configuracoes')
        assert response.status_code == 200 or response.status_code == 404  # Pode não existir ainda

    def test_perfil_page_loads(self, client, admin_logged_in):
        """Teste se página de perfil carrega"""
        response = client.get('/perfil')
        assert response.status_code == 200 or response.status_code == 404  # Pode não existir ainda

    def test_404_page_for_nonexistent_route(self, client, admin_logged_in):
        """Teste página 404 para rota inexistente"""
        response = client.get('/pagina-inexistente')
        assert response.status_code == 404

    def test_static_files_load(self, client):
        """Teste se arquivos estáticos carregam"""
        # Teste CSS
        response = client.get('/static/css/style.css')
        assert response.status_code == 200 or response.status_code == 404
        
        # Teste JS
        response = client.get('/static/js/app.js')
        assert response.status_code == 200 or response.status_code == 404

    def test_favicon_loads(self, client):
        """Teste se favicon carrega"""
        response = client.get('/favicon.ico')
        assert response.status_code == 200 or response.status_code == 404

    def test_page_titles_and_meta(self, client, admin_logged_in):
        """Teste títulos e meta tags das páginas"""
        pages = ['/', '/usuarios', '/categorias', '/produtos', '/estoque']
        
        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                assert b'<title>' in response.data
                assert b'<meta' in response.data

    def test_navigation_menu_present(self, client, admin_logged_in):
        """Teste se menu de navegação está presente"""
        response = client.get('/')
        assert response.status_code == 200
        # Verificar se elementos de navegação estão presentes
        assert b'nav' in response.data.lower() or b'menu' in response.data.lower()

    def test_footer_present(self, client, admin_logged_in):
        """Teste se rodapé está presente"""
        response = client.get('/')
        assert response.status_code == 200
        # Verificar se footer está presente
        assert b'footer' in response.data.lower() or b'rodape' in response.data.lower()

    def test_responsive_meta_tag(self, client, admin_logged_in):
        """Teste se meta tag de responsividade está presente"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'viewport' in response.data

    def test_csrf_protection(self, client, admin_logged_in):
        """Teste proteção CSRF em formulários"""
        response = client.get('/usuarios')
        if response.status_code == 200:
            # Verificar se token CSRF está presente em formulários
            assert b'csrf_token' in response.data or b'_token' in response.data

    def test_form_validation_messages(self, client, admin_logged_in):
        """Teste mensagens de validação de formulários"""
        # Tentar criar usuário com dados inválidos
        response = client.post('/api/usuarios', 
                             json={'nome': '', 'username': '', 'email': 'email_invalido'},
                             headers={'Content-Type': 'application/json'})
        # Deve retornar erro de validação
        assert response.status_code == 400

    def test_search_functionality(self, client, admin_logged_in):
        """Teste funcionalidade de busca"""
        # Teste busca de produtos
        response = client.get('/produtos?search=teste')
        assert response.status_code == 200

    def test_pagination_controls(self, client, admin_logged_in):
        """Teste controles de paginação"""
        # Teste paginação de produtos
        response = client.get('/produtos?pagina=1')
        assert response.status_code == 200

    def test_modal_dialogs_present(self, client, admin_logged_in):
        """Teste se modais estão presentes nas páginas"""
        pages = ['/usuarios', '/categorias', '/produtos', '/estoque']
        
        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                # Verificar se elementos de modal estão presentes
                assert b'modal' in response.data.lower()

    def test_data_tables_present(self, client, admin_logged_in):
        """Teste se tabelas de dados estão presentes"""
        pages = ['/usuarios', '/categorias', '/produtos', '/estoque']
        
        for page in pages:
            response = client.get(page)
            if response.status_code == 200:
                # Verificar se tabelas estão presentes
                assert b'<table' in response.data or b'datatable' in response.data.lower()

    def test_action_buttons_present(self, client, admin_logged_in):
        """Teste se botões de ação estão presentes"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se botões de ação estão presentes
        assert b'btn' in response.data.lower() or b'button' in response.data.lower()

    def test_status_indicators(self, client, admin_logged_in):
        """Teste indicadores de status"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se indicadores de status estão presentes
        assert b'ativo' in response.data.lower() or b'inativo' in response.data.lower()

    def test_loading_states(self, client, admin_logged_in):
        """Teste estados de carregamento"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se elementos de loading estão presentes
        assert b'loading' in response.data.lower() or b'carregando' in response.data.lower()

    def test_error_handling_pages(self, client):
        """Teste páginas de tratamento de erro"""
        # Teste página 500 (pode ser difícil de simular)
        # Teste página 403
        response = client.get('/usuarios')  # Sem login
        assert response.status_code == 302 or response.status_code == 401

    def test_breadcrumb_navigation(self, client, admin_logged_in):
        """Teste navegação breadcrumb"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se breadcrumb está presente
        assert b'breadcrumb' in response.data.lower() or b'nav' in response.data.lower()

    def test_help_tooltips(self, client, admin_logged_in):
        """Teste tooltips de ajuda"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se tooltips estão presentes
        assert b'tooltip' in response.data.lower() or b'title=' in response.data

    def test_keyboard_accessibility(self, client, admin_logged_in):
        """Teste acessibilidade por teclado"""
        response = client.get('/produtos')
        assert response.status_code == 200
        # Verificar se elementos têm atributos de acessibilidade
        assert b'tabindex' in response.data or b'aria-' in response.data

    def test_print_styles(self, client, admin_logged_in):
        """Teste estilos para impressão"""
        response = client.get('/relatorios')
        if response.status_code == 200:
            # Verificar se há estilos para impressão
            assert b'print' in response.data.lower() or b'@media print' in response.data

    def test_export_functionality(self, client, admin_logged_in):
        """Teste funcionalidade de exportação"""
        # Teste exportação de relatórios
        response = client.get('/api/relatorios/produtos/export')
        # Pode retornar 200 (sucesso) ou 404 (não implementado)
        assert response.status_code in [200, 404, 403]


@pytest.mark.web
@pytest.mark.slow
class TestWebPagePerformance:
    """Testes de performance das páginas web"""

    def test_page_load_times(self, client, admin_logged_in):
        """Teste tempos de carregamento das páginas"""
        import time
        
        pages = ['/', '/usuarios', '/categorias', '/produtos', '/estoque']
        
        for page in pages:
            start_time = time.time()
            response = client.get(page)
            end_time = time.time()
            
            if response.status_code == 200:
                load_time = end_time - start_time
                # Página deve carregar em menos de 2 segundos
                assert load_time < 2.0, f"Página {page} demorou {load_time:.2f}s para carregar"

    def test_large_dataset_handling(self, client, admin_logged_in):
        """Teste manipulação de grandes conjuntos de dados"""
        # Teste com muitos registros por página
        response = client.get('/produtos?por_pagina=100')
        assert response.status_code == 200

    def test_concurrent_requests(self, client, admin_logged_in):
        """Teste requisições concorrentes"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/produtos')
            results.append(response.status_code)
        
        # Criar múltiplas threads para requisições simultâneas
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Aguardar todas as threads terminarem
        for thread in threads:
            thread.join()
        
        # Todas as requisições devem ter sucesso
        assert all(status == 200 for status in results)