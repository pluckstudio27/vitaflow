from datetime import datetime, timedelta


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


def _setup_hierarchy_and_stock(client, csrf):
    # Central, almox, sub, setor
    r = client.post('/api/centrais', json={'nome': 'Central Op', 'descricao': 'Central', 'ativo': True}, headers=_json_headers(csrf))
    assert r.status_code == 200
    central_id = r.get_json().get('id')
    r = client.post('/api/almoxarifados', json={'nome': 'Almox Op', 'descricao': 'Almox', 'ativo': True, 'central_id': central_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    almox_id = r.get_json().get('id')
    r = client.post('/api/sub-almoxarifados', json={'nome': 'Sub Op', 'descricao': 'Sub', 'ativo': True, 'almoxarifado_id': almox_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    sub_id = r.get_json().get('id')
    r = client.post('/api/setores', json={'nome': 'Setor Op', 'descricao': 'Setor', 'ativo': True, 'sub_almoxarifado_ids': [sub_id]}, headers=_json_headers(csrf))
    assert r.status_code == 200
    setor_id = r.get_json().get('id')

    # Produto e recebimento
    prod = {'central_id': central_id, 'codigo': 'OPC-0001', 'nome': 'Produto Op', 'ativo': True}
    r = client.post('/api/produtos', json=prod, headers=_json_headers(csrf))
    assert r.status_code == 200
    produto_id = r.get_json().get('id')

    rec = {'almoxarifado_id': almox_id, 'quantidade': 5, 'lote': 'LOP1', 'data_vencimento': (datetime.utcnow() + timedelta(days=90)).isoformat()}
    r = client.post(f'/api/produtos/{produto_id}/recebimento', json=rec, headers=_json_headers(csrf))
    assert r.status_code == 200

    # Distribuir para setor (3 unidades)
    payload = {
        'produto_id': produto_id,
        'origem': {'tipo': 'almoxarifado', 'id': almox_id},
        'destinos': [{'id': setor_id, 'quantidade': 3.0}],
    }
    r = client.post('/api/movimentacoes/distribuicao', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200

    return setor_id, produto_id


def test_operador_setor_consumo_requires_csrf_and_updates_stock(client):
    # Login admin e CSRF
    r = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200
    csrf = _get_csrf_token(client)
    assert csrf

    setor_id, produto_id = _setup_hierarchy_and_stock(client, csrf)

    # Criar usuário operador vinculado ao setor
    new_user = {
        'username': 'oper2',
        'nome_completo': 'Operador 2',
        'email': 'oper2@example.com',
        'nivel_acesso': 'operador_setor',
        'senha': 'oper2',
        'ativo': True,
        'setor_id': setor_id,
    }
    r = client.post('/api/usuarios', json=new_user, headers=_json_headers(csrf))
    assert r.status_code == 200

    # Trocar para operador
    client.get('/auth/logout')
    r = client.post('/auth/login', json={'username': 'oper2', 'password': 'oper2'})
    assert r.status_code == 200

    # Sem CSRF deve falhar
    consumo = {'produto_id': produto_id, 'quantidade': 1.5, 'observacoes': 'Consumo sem CSRF'}
    r = client.post('/api/setor/registro', json=consumo, headers=_json_headers(None))
    assert r.status_code == 403

    # Com CSRF deve registrar
    csrf2 = _get_csrf_token(client)
    assert csrf2
    consumo2 = {'produto_id': produto_id, 'quantidade': 1.5, 'observacoes': 'Consumo com CSRF'}
    r = client.post('/api/setor/registro', json=consumo2, headers=_json_headers(csrf2))
    assert r.status_code == 200
    assert r.get_json().get('success') is True
    assert float(r.get_json().get('quantidade_registrada', 0)) == 1.5

    # Resumo do dia deve refletir consumo
    r = client.get(f'/api/setores/{setor_id}/produtos/{produto_id}/resumo-dia')
    assert r.status_code == 200
    resumo = r.get_json()
    assert float(resumo.get('usado_hoje_total', 0)) >= 1.5
    # estoque disponível deve ter reduzido de 3 para ~1.5
    assert 1.4 <= float(resumo.get('estoque_disponivel', 0)) <= 1.6