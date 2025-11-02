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


def test_csrf_login_and_transfer_workflow(app, client):
    # 1) Login as seeded admin (super_admin)
    resp = client.post('/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert resp.status_code == 200
    assert resp.get_json().get('message') == 'Login realizado com sucesso'

    # 2) Acquire CSRF token from session
    csrf = _get_csrf_token(client)
    assert csrf, 'CSRF token should be present in session after GET to /'

    # 3) Create a Central
    resp = client.post('/api/centrais', json={'nome': 'Central Teste', 'descricao': 'Central E2E', 'ativo': True}, headers=_json_headers(csrf))
    assert resp.status_code == 200
    central_id = resp.get_json().get('id')
    assert central_id is not None

    # 4) Create an Almoxarifado linked to central
    resp = client.post('/api/almoxarifados', json={'nome': 'Almox Principal', 'descricao': 'Almox E2E', 'ativo': True, 'central_id': central_id}, headers=_json_headers(csrf))
    assert resp.status_code == 200
    almox_id = resp.get_json().get('id')
    assert almox_id is not None

    # 5) Create a Sub-Almoxarifado under the almoxarifado
    resp = client.post('/api/sub-almoxarifados', json={'nome': 'Sub 1', 'descricao': 'Sub E2E', 'ativo': True, 'almoxarifado_id': almox_id}, headers=_json_headers(csrf))
    assert resp.status_code == 200
    sub_id = resp.get_json().get('id')
    assert sub_id is not None

    # 6) Create a Setor linked to the sub-almoxarifado
    resp = client.post('/api/setores', json={'nome': 'Enfermaria', 'descricao': 'Setor E2E', 'ativo': True, 'sub_almoxarifado_ids': [sub_id]}, headers=_json_headers(csrf))
    assert resp.status_code == 200
    setor_id = resp.get_json().get('id')
    assert setor_id is not None

    # 7) Create a Produto (free-text categoria optional)
    produto_payload = {
        'central_id': central_id,
        'codigo': 'TEST-E2E-0001',
        'nome': 'Seringa 10ml',
        'descricao': 'Produto de teste',
        'ativo': True,
        'categoria': 'Insumos',
    }
    resp = client.post('/api/produtos', json=produto_payload, headers=_json_headers(csrf))
    assert resp.status_code == 200
    produto_id = resp.get_json().get('id')
    assert produto_id is not None

    # 8) Register a recebimento into the almoxarifado
    rec_payload = {
        'almoxarifado_id': almox_id,
        'quantidade': 10,
        'fornecedor': 'Fornecedor X',
        'lote': 'L001',
        'data_fabricacao': '2025-10-01T00:00:00',
        'data_vencimento': '2026-10-01T00:00:00',
        'observacoes': 'Recebimento inicial E2E',
    }
    resp = client.post(f'/api/produtos/{produto_id}/recebimento', json=rec_payload, headers=_json_headers(csrf))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    estoque = data.get('estoque') or {}
    assert float(estoque.get('quantidade', 0)) == 10

    # 9) Transfer 4 units from almoxarifado to sub-almoxarifado
    transf_payload = {
        'produto_id': produto_id,
        'quantidade': 4,
        'motivo': 'Teste de transferência',
        'origem': {'tipo': 'almoxarifado', 'id': almox_id},
        'destino': {'tipo': 'sub_almoxarifado', 'id': sub_id},
    }
    resp = client.post('/api/movimentacoes/transferencia', json=transf_payload, headers=_json_headers(csrf))
    assert resp.status_code == 200
    tdata = resp.get_json()
    assert tdata.get('success') is True
    dest = tdata.get('estoque_destino') or {}
    assert dest.get('local_tipo') == 'sub_almoxarifado'
    assert str(dest.get('local_id')) == str(sub_id)
    assert float(dest.get('quantidade', 0)) == 4

    # 10) Validate movimentacoes include 'entrada' and 'transferencia'
    resp = client.get(f'/api/produtos/{produto_id}/movimentacoes')
    assert resp.status_code == 200
    movs = resp.get_json().get('items') or resp.get_json().get('movimentacoes') or []
    tipos = {m.get('tipo') for m in movs}
    assert 'entrada' in tipos
    assert 'transferencia' in tipos

    # 11) Validate origem estoque decreased to 6 and destino has 4 via Mongo
    with app.app_context():
        estoques = extensions.mongo_db['estoques']
        pid_out = produto_id  # produto_id stored as string _id in mov/estoque per code
        origem_doc = estoques.find_one({'produto_id': pid_out, 'local_tipo': 'almoxarifado', 'local_id': almox_id})
        destino_doc = estoques.find_one({'produto_id': pid_out, 'local_tipo': 'sub_almoxarifado', 'local_id': sub_id})
        assert origem_doc is not None
        assert destino_doc is not None
        assert float(origem_doc.get('quantidade', 0)) == 6
        assert float(destino_doc.get('quantidade', 0)) == 4