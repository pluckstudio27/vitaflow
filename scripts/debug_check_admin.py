import os
import json
from pymongo import MongoClient

env = {}
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
env_path = os.path.abspath(env_path)
try:
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k] = v
except Exception as e:
    print(json.dumps({'error': f'cannot read .env: {e}'}))
    raise SystemExit(1)

uri = env.get('MONGO_URI', 'mongodb://localhost:27017/almox_sms')
dbname = env.get('MONGO_DB', 'almox_sms')

client = MongoClient(uri)
db = client[dbname]
admin = db['usuarios'].find_one({'username': 'admin'})

out = {
    'found': bool(admin),
    'ativo': admin.get('ativo') if admin else None,
    'nivel_acesso': admin.get('nivel_acesso') if admin else None,
    'has_hash': bool(admin.get('password_hash')) if admin else None,
    'hash_prefix': admin.get('password_hash', '')[:25] if admin else None,
}
print(json.dumps(out, ensure_ascii=False))

# Additional check: verify password hash works with 'admin'
try:
    from werkzeug.security import check_password_hash
    ok = check_password_hash(admin.get('password_hash',''), 'admin') if admin else None
    print(json.dumps({'check_password_admin_admin': ok}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'check_error': str(e)}, ensure_ascii=False))