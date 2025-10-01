"""
Configurações e fixtures para os testes do sistema Almox SMS
"""
import pytest
import tempfile
import os
from app import create_app
from extensions import db
from models.usuario import Usuario
from models.categoria import CategoriaProduto
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from models.produto import Produto, EstoqueProduto
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """Cria uma instância da aplicação para testes"""
    # Criar um arquivo temporário para o banco de dados de teste
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        
    # Limpar após os testes
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Cliente de teste para requisições HTTP"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Runner para comandos CLI"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Sessão de banco de dados para testes"""
    with app.app_context():
        # Limpar todas as tabelas antes de cada teste
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield db.session
        db.session.remove()


@pytest.fixture
def central_teste(db_session):
    """Cria uma central para testes"""
    central = Central(
        nome='Central Teste',
        descricao='Central para testes',
        ativo=True
    )
    db_session.add(central)
    db_session.commit()
    return central


@pytest.fixture
def categoria_teste(db_session):
    """Cria uma categoria para testes"""
    categoria = CategoriaProduto(
        nome='Categoria Teste',
        codigo='CAT001',
        descricao='Categoria para testes',
        cor='#FF0000',
        ativo=True
    )
    db_session.add(categoria)
    db_session.commit()
    return categoria


@pytest.fixture
def categoria_teste_2(db_session):
    """Fixture para segunda categoria de teste"""
    categoria = CategoriaProduto(
        nome='Categoria Teste 2',
        descricao='Segunda categoria para testes',
        codigo='CAT002',
        cor='#33FF57',
        ativo=True
    )
    db_session.add(categoria)
    db_session.commit()
    return categoria


@pytest.fixture
def usuario_admin(db_session):
    """Cria um usuário administrador para testes"""
    usuario = Usuario(
        nome_completo='Admin Teste',
        username='admin_teste',
        email='admin@teste.com',
        password_hash=generate_password_hash('senha123'),
        nivel_acesso='super_admin',
        ativo=True
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


@pytest.fixture
def usuario_comum(db_session, categoria_teste, central_teste):
    """Cria um usuário comum para testes"""
    # Primeiro criar a hierarquia completa para o operador
    from models.hierarchy import Setor, Almoxarifado, SubAlmoxarifado
    
    almoxarifado = Almoxarifado(
        nome='Almoxarifado Usuario',
        central_id=central_teste.id
    )
    db_session.add(almoxarifado)
    db_session.flush()
    
    sub_almoxarifado = SubAlmoxarifado(
        nome='Sub-Almoxarifado Usuario',
        almoxarifado_id=almoxarifado.id
    )
    db_session.add(sub_almoxarifado)
    db_session.flush()
    
    setor = Setor(
        nome='Setor Usuario',
        sub_almoxarifado_id=sub_almoxarifado.id
    )
    db_session.add(setor)
    db_session.flush()
    
    usuario = Usuario(
        nome_completo='Usuario Teste',
        username='usuario_teste',
        email='usuario@teste.com',
        password_hash=generate_password_hash('senha123'),
        nivel_acesso='operador_setor',
        setor_id=setor.id,
        categoria_id=categoria_teste.id,
        ativo=True
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


@pytest.fixture
def produto_teste(db_session, central_teste, categoria_teste):
    """Cria um produto para testes"""
    produto = Produto(
        codigo='PROD001',
        nome='Produto Teste',
        descricao='Produto para testes',
        unidade_medida='UN',
        categoria_id=categoria_teste.id,
        central_id=central_teste.id,
        ativo=True
    )
    db_session.add(produto)
    db_session.commit()
    return produto


@pytest.fixture
def almoxarifado_teste(db_session, produto_teste, central_teste, usuario_comum):
    """Cria um estoque de produto para testes"""
    # Criar o estoque no setor do usuario_comum para que o filtro de escopo funcione
    estoque = EstoqueProduto(
        produto_id=produto_teste.id,
        setor_id=usuario_comum.setor_id,
        quantidade=100,
        quantidade_disponivel=100,
        ativo=True
    )
    db_session.add(estoque)
    db_session.commit()
    return estoque


@pytest.fixture
def almoxarifado_teste_obj(db_session, central_teste):
    """Cria um almoxarifado para testes"""
    from models.hierarchy import Almoxarifado
    almoxarifado = Almoxarifado(
        nome='Almoxarifado Teste Obj',
        central_id=central_teste.id,
        ativo=True
    )
    db_session.add(almoxarifado)
    db_session.commit()
    return almoxarifado


@pytest.fixture
def auth_headers_admin(client, usuario_admin):
    """Faz login como admin e retorna headers vazios (usa sessão Flask-Login)"""
    response = client.post('/auth/login', data={
        'username': usuario_admin.username,
        'password': 'senha123'
    }, follow_redirects=True)
    return {}

@pytest.fixture
def auth_headers_user(client, usuario_comum):
    """Faz login como usuário comum e retorna headers vazios (usa sessão Flask-Login)"""
    response = client.post('/auth/login', data={
        'username': usuario_comum.username,
        'password': 'senha123'
    }, follow_redirects=True)
    return {}


def login_user(client, username, password):
    """Helper para fazer login de usuário"""
    return client.post('/auth/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def login_admin(client, test_admin_user):
    """Helper para fazer login como admin"""
    return login_user(client, test_admin_user.username, 'senha123')

def login_common_user(client, test_common_user):
    """Helper para fazer login como usuário comum"""
    return login_user(client, test_common_user.username, 'senha123')

def logout_user(client):
    """Helper para fazer logout de usuário"""
    return client.get('/auth/logout', follow_redirects=True)

@pytest.fixture
def admin_logged_in(client, usuario_admin):
    """Fixture que faz login como admin e mantém a sessão ativa"""
    login_user(client, usuario_admin.username, 'senha123')
    return usuario_admin

@pytest.fixture
def user_logged_in(client, usuario_comum):
    """Fixture que faz login como usuário comum e mantém a sessão ativa"""
    login_user(client, usuario_comum.username, 'senha123')
    return usuario_comum