from flask import session
import extensions


def _get_csrf_token(client):
    # Trigger CSRF provisioning via non-API GET
    client.get('/')
    with client.session_transaction() as sess:
        return sess.get('csrf_token')


def _json_headers(token):
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-Token': token,
    }


def _bootstrap_hierarchy(client, csrf):
    # Central
    r = client.post('/api/centrais', json={'nome': 'Central T', 'descricao': 'Central Teste', 'ativo': True}, headers=_json_headers(csrf))
    assert r.status_code == 200
    central_id = r.get_json().get('id')
    assert central_id

    # Almoxarifado
    r = client.post('/api/almoxarifados', json={'nome': 'Almox T', 'descricao': 'Almox Teste', 'ativo': True, 'central_id': central_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    almox_id = r.get_json().get('id')
    assert almox_id

    # Sub-almoxarifado
    r = client.post('/api/sub-almoxarifados', json={'nome': 'Sub T', 'descricao': 'Sub Teste', 'ativo': True, 'almoxarifado_id': almox_id}, headers=_json_headers(csrf))
    assert r.status_code == 200
    sub_id = r.get_json().get('id')
    assert sub_id

    # Setor
    r = client.post('/api/setores', json={'nome': 'Setor T1', 'descricao': 'Setor Teste 1', 'ativo': True, 'sub_almoxarifado_ids': [sub_id]}, headers=_json_headers(csrf))
    assert r.status_code == 200
    setor1_id = r.get_json().get('id')
    assert setor1_id

    # Setor 2 (opcional)
    r = client.post('/api/setores', json={'nome': 'Setor T2', 'descricao': 'Setor Teste 2', 'ativo': True, 'sub_almoxarifado_ids': [sub_id]}, headers=_json_headers(csrf))
    assert r.status_code == 200
    setor2_id = r.get_json().get('id')
    assert setor2_id

    return central_id, almox_id, sub_id, setor1_id, setor2_id


def _create_produto(client, csrf, central_id):
    payload = {
        'central_id': central_id,
        'codigo': 'TEST-DIST-0001',
        'nome': 'Gaze 10x10',
        'descricao': 'Produto para distribuição',
        'ativo': True,
        'categoria': 'Insumos',
    }
    r = client.post('/api/produtos', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200
    produto_id = r.get_json().get('id')
    assert produto_id
    return produto_id


def _receber_no_almox(client, csrf, produto_id, almox_id, quantidade):
    rec = {
        'almoxarifado_id': almox_id,
        'quantidade': quantidade,
        'fornecedor': 'Fornecedor Teste',
        'lote': 'L-DIST-001',
        'observacoes': 'Recebimento para testes de distribuição',
    }
    r = client.post(f'/api/produtos/{produto_id}/recebimento', json=rec, headers=_json_headers(csrf))
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('success') is True
    return data


def test_distribuicao_novo_formato_e_resumo_dia(app, client):
    # Login admin
    resp = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert resp.status_code == 200

    csrf = _get_csrf_token(client)
    assert csrf

    # Hierarquia e produto
    central_id, almox_id, sub_id, setor1_id, _ = _bootstrap_hierarchy(client, csrf)
    produto_id = _create_produto(client, csrf, central_id)
    _receber_no_almox(client, csrf, produto_id, almox_id, 20)

    # Distribuir 5 unidades para setor1 (novo formato)
    payload = {
        'produto_id': produto_id,
        'origem': {'tipo': 'almoxarifado', 'id': almox_id},
        'destinos': [{'id': setor1_id, 'quantidade': 5.0}],
        'motivo': 'Teste distrib',
        'observacoes': 'Novo formato',
    }
    r = client.post('/api/movimentacoes/distribuicao', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('success') is True
    assert int(j.get('movimentacoes_criadas', 0)) == 1
    assert float(j.get('total_distribuido', 0)) == 5.0
    assert float(j.get('saldo_origem', -1)) == 15.0

    # Verificar estoques via Mongo
    with app.app_context():
        estoques = extensions.mongo_db['estoques']
        pid = produto_id
        origem = estoques.find_one({'produto_id': pid, 'local_tipo': 'almoxarifado', 'local_id': almox_id})
        destino = estoques.find_one({'produto_id': pid, 'local_tipo': 'setor', 'local_id': setor1_id})
        assert origem and destino
        assert float(origem.get('quantidade', 0)) == 15.0
        assert float(destino.get('quantidade', 0)) == 5.0
        assert float(destino.get('quantidade_disponivel', destino.get('quantidade', 0))) == 5.0

    # Resumo do dia para setor1
    r = client.get(f'/api/setores/{setor1_id}/produtos/{produto_id}/resumo-dia')
    assert r.status_code == 200
    resumo = r.get_json()
    assert float(resumo.get('estoque_disponivel', 0)) == 5.0
    assert float(resumo.get('recebido_hoje_almoxarifado', 0)) == 5.0
    assert float(resumo.get('recebido_hoje_sub_almoxarifado', 0)) == 0.0
    assert float(resumo.get('usado_hoje_total', 0)) == 0.0

    # Registrar consumo de 2 unidades no setor1
    consumo = {
        'produto_id': produto_id,
        'setor_id': setor1_id,
        'quantidade': 2.0,
        'observacoes': 'Consumo test',
    }
    r = client.post('/api/setor/registro', json=consumo, headers=_json_headers(csrf))
    assert r.status_code == 200
    assert r.get_json().get('success') is True

    # Resumo depois do consumo
    r = client.get(f'/api/setores/{setor1_id}/produtos/{produto_id}/resumo-dia')
    assert r.status_code == 200
    resumo2 = r.get_json()
    assert float(resumo2.get('estoque_disponivel', 0)) == 3.0
    assert float(resumo2.get('usado_hoje_total', 0)) == 2.0


def test_distribuicao_formato_antigo_divisao_igual(app, client):
    # Login admin
    resp = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert resp.status_code == 200

    csrf = _get_csrf_token(client)
    assert csrf

    # Hierarquia e produto
    central_id, almox_id, sub_id, setor1_id, setor2_id = _bootstrap_hierarchy(client, csrf)
    produto_id = _create_produto(client, csrf, central_id)
    _receber_no_almox(client, csrf, produto_id, almox_id, 6)

    # Distribuição em formato antigo: total=4 dividido igualmente
    payload = {
        'produto_id': produto_id,
        'origem': {'tipo': 'almoxarifado', 'id': almox_id},
        'quantidade_total': 4.0,
        'setores_destino': [setor1_id, setor2_id],
        'motivo': 'Antigo formato',
    }
    r = client.post('/api/movimentacoes/distribuicao', json=payload, headers=_json_headers(csrf))
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('success') is True
    assert int(j.get('movimentacoes_criadas', 0)) == 2
    assert float(j.get('total_distribuido', 0)) == 4.0

    # Verificar estoques via Mongo
    with app.app_context():
        estoques = extensions.mongo_db['estoques']
        pid = produto_id
        origem = estoques.find_one({'produto_id': pid, 'local_tipo': 'almoxarifado', 'local_id': almox_id})
        dest1 = estoques.find_one({'produto_id': pid, 'local_tipo': 'setor', 'local_id': setor1_id})
        dest2 = estoques.find_one({'produto_id': pid, 'local_tipo': 'setor', 'local_id': setor2_id})
        assert origem and dest1 and dest2
        assert float(origem.get('quantidade', 0)) == 2.0
        assert float(dest1.get('quantidade', 0)) == 2.0
        assert float(dest2.get('quantidade', 0)) == 2.0

    # Resumo de cada setor deve refletir recebimento
    r1 = client.get(f'/api/setores/{setor1_id}/produtos/{produto_id}/resumo-dia')
    r2 = client.get(f'/api/setores/{setor2_id}/produtos/{produto_id}/resumo-dia')
    assert r1.status_code == 200 and r2.status_code == 200
    res1 = r1.get_json()
    res2 = r2.get_json()
    assert float(res1.get('recebido_hoje_almoxarifado', 0)) == 2.0
    assert float(res2.get('recebido_hoje_almoxarifado', 0)) == 2.0