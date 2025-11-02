from flask import session


def _get_csrf_token(client):
    client.get('/')
    with client.session_transaction() as sess:
        return sess.get('csrf_token')


def _json_headers(token=None):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    if token:
        headers['X-CSRF-Token'] = token
    return headers


def test_csrf_enforcement_on_mutating_api_requires_token(client):
    # Login admin
    r = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200

    # POST without CSRF header should be blocked (expects JSON)
    r = client.post('/api/centrais', json={'nome': 'NoCSRF', 'descricao': 'Teste', 'ativo': True}, headers=_json_headers(None))
    assert r.status_code == 403
    assert 'CSRF' in (r.get_json().get('error') or '')


def test_csrf_invalid_token_is_rejected(client):
    # Login admin
    r = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200

    csrf = _get_csrf_token(client)
    assert csrf

    # Use a wrong token
    r = client.post('/api/centrais', json={'nome': 'InvalidCSRF', 'descricao': 'Teste', 'ativo': True}, headers=_json_headers('wrong-token'))
    assert r.status_code == 403
    assert 'CSRF' in (r.get_json().get('error') or '')


def test_role_based_authorization_blocks_operador_actions(client):
    # Login admin to create a low-privilege user
    r = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200
    csrf = _get_csrf_token(client)
    assert csrf

    # Create operador_setor user (only super_admin may create users)
    payload = {
        'username': 'oper',
        'nome_completo': 'Operador Teste',
        'email': 'oper@example.com',
        'nivel_acesso': 'operador_setor',
        'senha': 'oper',
        'ativo': True,
    }
    r = client.post('/api/usuarios', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200

    # Logout admin and login as operador
    r = client.get('/auth/logout')
    assert r.status_code in (302, 200)
    r = client.post('/auth/login', json={'username': 'oper', 'password': 'oper'})
    assert r.status_code == 200
    csrf2 = _get_csrf_token(client)
    assert csrf2

    # operador_setor should be blocked from creating produtos
    produto_payload = {
        'central_id': 'ANY',
        'codigo': 'OP-BLOCK-001',
        'nome': 'Bloqueado',
    }
    r = client.post('/api/produtos', json=produto_payload, headers=_json_headers(csrf2))
    assert r.status_code == 403

    # operador_setor should be blocked from distribuição endpoint entirely
    dist_payload = {
        'produto_id': 'any',
        'origem': {'tipo': 'almoxarifado', 'id': 'any'},
        'destinos': [{'id': 'any', 'quantidade': 1.0}],
    }
    r = client.post('/api/movimentacoes/distribuicao', json=dist_payload, headers=_json_headers(csrf2))
    assert r.status_code == 403