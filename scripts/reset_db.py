import sys
import os
from datetime import datetime

# Garantir que o diretório raiz do projeto esteja no PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa o app para inicializar o Mongo via extensions.init_mongo
from app import app  # noqa: F401
import extensions
from werkzeug.security import generate_password_hash


def reset_database(preserve_admin: bool = True) -> dict:
    """Limpa todas as coleções do banco MongoDB.

    - Preserva o usuário 'admin' por padrão (remove os demais em 'usuarios').
    - Mantém índices (usa delete_many, não drop_database).
    - Garante que o usuário 'admin' exista ao final.
    """
    db = extensions.mongo_db
    if db is None:
        raise RuntimeError('MongoDB não inicializado. Verifique MONGO_URI/MONGO_DB e inicialização do app.')

    result = {
        'database': db.name,
        'collections_cleared': {},
        'admin_upserted': False,
    }

    # Coleta todas as coleções existentes
    collections = db.list_collection_names()

    for name in collections:
        coll = db[name]
        if name == 'usuarios' and preserve_admin:
            del_res = coll.delete_many({'username': {'$ne': 'admin'}})
        else:
            del_res = coll.delete_many({})
        result['collections_cleared'][name] = del_res.deleted_count

    # Garante coleções/índices essenciais novamente (idempotente)
    extensions.ensure_collections_and_indexes(db)

    # Upsert do usuário admin (caso tenha sido removido ou inexistente)
    admin_fields = {
        'email': 'admin@local',
        'nome': 'Administrador',
        'password_hash': generate_password_hash('admin'),
        'ativo': True,
        'nivel_acesso': 'super_admin',
        'data_criacao': datetime.utcnow(),
        'ultimo_login': None,
        'central_id': None,
        'almoxarifado_id': None,
        'sub_almoxarifado_id': None,
        'setor_id': None,
    }
    res = db['usuarios'].update_one(
        {'username': 'admin'},
        {'$set': {'username': 'admin', **admin_fields}},
        upsert=True
    )
    result['admin_upserted'] = (res.upserted_id is not None) or (res.matched_count >= 1)

    return result


if __name__ == '__main__':
    # CLI: python scripts/reset_db.py [--remove-admin]
    preserve_admin = True
    if len(sys.argv) > 1 and sys.argv[1] == '--remove-admin':
        preserve_admin = False
    summary = reset_database(preserve_admin=preserve_admin)
    print('[Reset Mongo] Banco:', summary['database'])
    print('[Reset Mongo] Coleções limpas:')
    for k, v in sorted(summary['collections_cleared'].items()):
        print(f'  - {k}: {v} documentos removidos')
    print('[Reset Mongo] Admin garantido:', summary['admin_upserted'])