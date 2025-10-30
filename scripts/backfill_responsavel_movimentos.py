import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId

# Garantir que o diretório raiz do projeto esteja no PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Inicializa o app para configurar Mongo automaticamente
from app import app  # noqa: F401
import extensions


def parse_dt(v):
    if isinstance(v, datetime):
        return v
    if v is None:
        return None
    try:
        s = str(v)
        # aceita ISO com 'Z'
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def same_day_range(dt: datetime):
    start = datetime(dt.year, dt.month, dt.day)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def resolve_full_name(users_coll, username: str):
    if not username:
        return None
    try:
        doc = users_coll.find_one({'username': username}, {'password_hash': 0})
        if not doc:
            return None
        return doc.get('nome_completo') or doc.get('nome') or doc.get('username')
    except Exception:
        return None


def backfill_consumo(db):
    movs = db['movimentacoes']
    registros = db['setor_registros']
    usuarios = db['usuarios']

    criteria = {
        'origem_tipo': {'$in': ['setor', 'Setor', 'SETOR']},
        'destino_tipo': {'$in': ['consumo', 'Consumo', 'CONSUMO']},
        '$or': [
            {'usuario_responsavel': {'$exists': False}},
            {'usuario_responsavel': None},
            {'usuario_responsavel': ''},
        ]
    }
    total = movs.count_documents(criteria)
    updated = 0
    scanned = 0

    print(f"[Backfill Consumo] Movimentos candidatos: {total}")

    cursor = movs.find(criteria).sort('data_movimentacao', 1)
    for m in cursor:
        scanned += 1
        pid = m.get('produto_id')
        setor_id = m.get('origem_id') or m.get('setor_id') or m.get('local_id')
        dt = parse_dt(m.get('data_movimentacao') or m.get('created_at'))
        qty = float(m.get('quantidade', 0) or 0)

        if not (pid and setor_id and dt and qty > 0):
            continue

        start, end = same_day_range(dt)
        try:
            regs = list(registros.find({
                'produto_id': pid,
                'setor_id': {'$in': [setor_id, str(setor_id)]},
                'data_registro': {'$gte': start, '$lte': end},
            }).sort('data_registro', 1))
        except Exception:
            regs = []

        selected = None
        # 1) exata por quantidade
        for r in regs:
            try:
                if abs(float(r.get('saida_dia', 0) or 0) - qty) < 1e-6 and float(r.get('saida_dia', 0) or 0) > 0:
                    selected = r
                    break
            except Exception:
                pass
        # 2) primeira com saida positiva
        if not selected:
            for r in regs:
                try:
                    if float(r.get('saida_dia', 0) or 0) > 0:
                        selected = r
                        break
                except Exception:
                    pass

        if not selected:
            continue

        username = selected.get('usuario')
        if not username:
            continue
        full_name = resolve_full_name(usuarios, username)

        try:
            movs.update_one({'_id': m['_id']}, {
                '$set': {
                    'usuario_responsavel': username,
                    'usuario_nome': full_name or username,
                }
            })
            updated += 1
        except Exception as e:
            print(f"[Backfill Consumo] Falha ao atualizar {m.get('_id')}: {e}")

        if scanned % 500 == 0:
            print(f"[Backfill Consumo] Progresso: {scanned}/{total}, atualizados={updated}")

    print(f"[Backfill Consumo] Finalizado: candidatos={total}, atualizados={updated}")


def backfill_entrada_setor(db):
    movs = db['movimentacoes']
    registros = db['setor_registros']
    usuarios = db['usuarios']

    criteria = {
        'tipo': 'entrada',
        'destino_tipo': {'$in': ['setor', 'Setor', 'SETOR']},
        '$or': [
            {'usuario_responsavel': {'$exists': False}},
            {'usuario_responsavel': None},
            {'usuario_responsavel': ''},
        ]
    }
    total = movs.count_documents(criteria)
    updated = 0
    scanned = 0

    print(f"[Backfill Entrada] Movimentos candidatos: {total}")

    cursor = movs.find(criteria).sort('data_movimentacao', 1)
    for m in cursor:
        scanned += 1
        pid = m.get('produto_id')
        setor_id = m.get('destino_id') or m.get('setor_id') or m.get('local_id')
        dt = parse_dt(m.get('data_movimentacao') or m.get('created_at'))
        qty = float(m.get('quantidade', 0) or 0)

        if not (pid and setor_id and dt and qty > 0):
            continue

        start, end = same_day_range(dt)
        try:
            regs = list(registros.find({
                'produto_id': pid,
                'setor_id': {'$in': [setor_id, str(setor_id)]},
                'data_registro': {'$gte': start, '$lte': end},
            }).sort('data_registro', 1))
        except Exception:
            regs = []

        selected = None
        # 1) exata por quantidade_recebida
        for r in regs:
            try:
                if abs(float(r.get('quantidade_recebida', 0) or 0) - qty) < 1e-6 and float(r.get('quantidade_recebida', 0) or 0) > 0:
                    selected = r
                    break
            except Exception:
                pass
        # 2) fallback: qualquer registro do dia
        if not selected and regs:
            selected = regs[0]

        if not selected:
            continue

        username = selected.get('usuario')
        if not username:
            continue
        full_name = resolve_full_name(usuarios, username)

        try:
            movs.update_one({'_id': m['_id']}, {
                '$set': {
                    'usuario_responsavel': username,
                    'usuario_nome': full_name or username,
                }
            })
            updated += 1
        except Exception as e:
            print(f"[Backfill Entrada] Falha ao atualizar {m.get('_id')}: {e}")

        if scanned % 500 == 0:
            print(f"[Backfill Entrada] Progresso: {scanned}/{total}, atualizados={updated}")

    print(f"[Backfill Entrada] Finalizado: candidatos={total}, atualizados={updated}")


def main():
    client, db = extensions.mongo_client, extensions.mongo_db
    if db is None:
        print('[Backfill] MongoDB não inicializado. Verifique configuração do app.')
        sys.exit(1)

    print('[Backfill] Iniciando...')
    backfill_consumo(db)
    backfill_entrada_setor(db)
    print('[Backfill] Concluído.')


if __name__ == '__main__':
    main()