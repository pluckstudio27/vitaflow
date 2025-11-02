from datetime import datetime, timedelta


def _get_csrf_token(client):
    client.get('/')
    with client.session_transaction() as sess:
        return sess.get('csrf_token')


def _json_headers(token):
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-Token': token,
    }


def _bootstrap_minimal(client, csrf):
    # Central
    r = client.post('/api/centrais', json={'nome': 'Central Dash', 'descricao': 'Central', 'ativo': True}, headers=_json_headers(csrf))
    assert r.status_code == 200
    central_id = r.get_json().get('id')
    assert central_id

    # Almoxarifado
    r = client.post('/api/almoxarifados', json={'nome': 'Almox Dash', 'descricao': 'Almox', 'ativo': True, 'central_id': central_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    almox_id = r.get_json().get('id')
    assert almox_id

    # Sub-almoxarifado
    r = client.post('/api/sub-almoxarifados', json={'nome': 'Sub Dash', 'descricao': 'Sub', 'ativo': True, 'almoxarifado_id': almox_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    sub_id = r.get_json().get('id')
    assert sub_id

    # Setor
    r = client.post('/api/setores', json={'nome': 'Setor Dash', 'descricao': 'Setor', 'ativo': True, 'sub_almoxarifado_ids': [sub_id]}, headers=_json_headers(csrf))
    assert r.status_code == 200
    setor_id = r.get_json().get('id')
    assert setor_id

    # Produto
    payload = {
        'central_id': central_id,
        'codigo': 'DASH-0001',
        'nome': 'Item Dash',
        'descricao': 'Produto para dashboard',
        'ativo': True,
        'categoria': 'Insumos',
    }
    r = client.post('/api/produtos', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200
    produto_id = r.get_json().get('id')
    assert produto_id

    # Recebimento com quantidade baixa para acionar estoque-baixo
    rec = {
        'almoxarifado_id': almox_id,
        'quantidade': 3,
        'fornecedor': 'Fornecedor Dash',
        'lote': 'LDASH1',
        'data_vencimento': (datetime.utcnow() + timedelta(days=10)).isoformat(),
        'observacoes': 'Recebimento para dashboard',
    }
    r = client.post(f'/api/produtos/{produto_id}/recebimento', json=rec, headers=_json_headers(csrf))
    assert r.status_code == 200

    return central_id, almox_id, sub_id, setor_id, produto_id


def test_dashboard_endpoints_shape(client):
    # Login admin
    r = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert r.status_code == 200
    csrf = _get_csrf_token(client)
    assert csrf

    # Seed minimal data
    central_id, almox_id, sub_id, setor_id, produto_id = _bootstrap_minimal(client, csrf)

    # stats-general
    r = client.get('/api/dashboard/stats-general')
    assert r.status_code == 200
    data = r.get_json()
    for key in ('almoxarifados', 'sub_almoxarifados', 'setores', 'produtos'):
        assert key in data
        assert isinstance(data[key], (int, float))

    # estoque-baixo
    r = client.get('/api/dashboard/estoque-baixo')
    assert r.status_code == 200
    eb = r.get_json()
    assert 'success' in eb and eb['success'] is True
    assert 'produtos' in eb and isinstance(eb['produtos'], list)

    # vencimentos (deve listar lote próximo ao vencimento)
    r = client.get('/api/dashboard/vencimentos?dias_aviso=30&limit=10')
    assert r.status_code == 200
    v = r.get_json()
    assert 'success' in v and v['success'] is True
    assert 'items' in v and isinstance(v['items'], list)
    # Se houver itens, validar formato do primeiro
    if v['items']:
        it = v['items'][0]
        for key in ('produto_id', 'produto_nome', 'numero_lote', 'data_vencimento', 'dias_para_vencer', 'status'):
            assert key in it

    # movimentacoes-recentes (deve incluir entrada recém criada)
    r = client.get('/api/dashboard/movimentacoes-recentes?limit=5')
    assert r.status_code == 200
    m = r.get_json()
    assert 'success' in m and m['success'] is True
    assert 'movimentacoes' in m and isinstance(m['movimentacoes'], list)
    # Se houver itens, validar formato do primeiro
    if m['movimentacoes']:
        it = m['movimentacoes'][0]
        for key in ('tipo', 'produto_nome', 'quantidade', 'local', 'data_formatada'):
            assert key in it