from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import json
# Removido: from models.usuario import Usuario, LogAuditoria
import extensions
from bson.objectid import ObjectId
from config.ui_blocks import get_ui_blocks_config
import secrets

# ConfiguraÃ§Ã£o do Flask-Login
login_manager = LoginManager()

# CSRF helpers
def ensure_csrf_token(renew: bool = False) -> str:
    """Ensure there is a CSRF token in session; optionally renew.

    Returns the current token (new or existing).
    """
    token = session.get('csrf_token')
    if renew or not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token

def get_csrf_token() -> str | None:
    """Get CSRF token from session without generating."""
    return session.get('csrf_token')

def extract_csrf_header() -> str | None:
    """Retrieve CSRF token from common header names."""
    return (
        request.headers.get('X-CSRF-Token')
        or request.headers.get('X-CSRFToken')
        or request.headers.get('X-CSRF')
    )

# Classe de usuÃ¡rio para MongoDB
class MongoUser:
    def __init__(self, data: dict):
        self.data = data or {}
    
    def get_id(self):
        return str(self.data.get('_id'))
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return bool(self.data.get('ativo', True))
    
    @property
    def is_anonymous(self):
        return False
    
    # Campos bÃ¡sicos
    @property
    def username(self):
        return self.data.get('username')
    
    @property
    def email(self):
        return self.data.get('email')
    
    @property
    def nome_completo(self):
        return self.data.get('nome_completo')
    
    @property
    def nivel_acesso(self):
        raw = (self.data.get('nivel_acesso') or '').strip()
        # Normalizar sinônimos e variações comuns
        normalized = raw.lower().replace(' ', '_').replace('-', '_')
        synonyms = {
            'gerente_almoxarifado': 'gerente_almox',
            'gerente_do_almoxarifado': 'gerente_almox',
            'gerente_almox': 'gerente_almox',
            'responsavel_sub_almox': 'resp_sub_almox',
            'responsavel_subalmox': 'resp_sub_almox',
            'resp_subalmox': 'resp_sub_almox',
            'resp_sub_almoxarifado': 'resp_sub_almox',
            'operador_de_setor': 'operador_setor',
            'operador_setor': 'operador_setor',
            'admin': 'admin_central',
            'secretário': 'secretario',
            'secretaria': 'secretario',
            'secretario': 'secretario',
        }
        return synonyms.get(normalized, raw or None)
    
    # Hierarquia (IDs, opcional)
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def almoxarifado_id(self):
        return self.data.get('almoxarifado_id')
    
    @property
    def sub_almoxarifado_id(self):
        return self.data.get('sub_almoxarifado_id')
    
    @property
    def setor_id(self):
        return self.data.get('setor_id')
    
    @property
    def data_criacao(self):
        return self.data.get('data_criacao')
    
    @property
    def ultimo_login(self):
        return self.data.get('ultimo_login')
    
    # Senha
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.data.get('password_hash', ''), password)
    
    def set_password(self, new_password: str):
        self.data['password_hash'] = generate_password_hash(new_password)
    
    def save_password_change(self):
        if extensions.mongo_db is None:
            raise RuntimeError('MongoDB não inicializado')
        extensions.mongo_db['usuarios'].update_one({'_id': self.data['_id']}, {'$set': {'password_hash': self.data['password_hash']}})
    
    def to_dict(self):
        return {
            'id': str(self.data.get('_id')),
            'username': self.username,
            'email': self.email,
            'nome_completo': self.nome_completo,
            'nivel_acesso': self.nivel_acesso,
            'ativo': self.is_active
        }
    
    # Acesso por escopo (MongoDB)
    def _find_by_id(self, coll_name: str, raw_id):
        """Resolve um documento por id numérico, ObjectId ou string direta."""
        try:
            db = extensions.mongo_db
            if db is None:
                return None
            coll = db[coll_name]
            doc = None
            # id sequencial
            try:
                if isinstance(raw_id, int) or (isinstance(raw_id, str) and raw_id.isdigit()):
                    doc = coll.find_one({'id': int(raw_id)})
            except Exception:
                doc = None
            # ObjectId
            if not doc:
                try:
                    oid = ObjectId(str(raw_id))
                    doc = coll.find_one({'_id': oid})
                except Exception:
                    doc = None
            # String direta (fallback)
            if not doc and isinstance(raw_id, str):
                doc = coll.find_one({'id': raw_id})
            return doc
        except Exception:
            return None

    def _central_id_of_local(self, tipo: str, raw_id):
        """Obtém o central_id do local (almoxarifado/sub_almoxarifado/setor/central)."""
        tipo = (tipo or '').lower()
        if tipo == 'central':
            c = self._find_by_id('centrais', raw_id)
            try:
                return str((c or {}).get('_id')) if c else None
            except Exception:
                return (c or {}).get('id')
        if tipo == 'almoxarifado':
            a = self._find_by_id('almoxarifados', raw_id)
            cid = (a or {}).get('central_id')
            c = self._find_by_id('centrais', cid)
            try:
                return str((c or {}).get('_id')) if c else None
            except Exception:
                return cid
        if tipo == 'sub_almoxarifado':
            s = self._find_by_id('sub_almoxarifados', raw_id)
            if not s:
                return None
            a = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
            cid = (a or {}).get('central_id')
            c = self._find_by_id('centrais', cid)
            try:
                return str((c or {}).get('_id')) if c else None
            except Exception:
                return cid
        if tipo == 'setor':
            se = self._find_by_id('setores', raw_id)
            if not se:
                return None
            # Primeiro, tentar resolver via sub_almoxarifado vinculado ao setor
            a = None
            try:
                s = self._find_by_id('sub_almoxarifados', (se or {}).get('sub_almoxarifado_id'))
            except Exception:
                s = None
            if s:
                a = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
            # Fallback: setor vinculado diretamente a um almoxarifado
            if not a:
                try:
                    a = self._find_by_id('almoxarifados', (se or {}).get('almoxarifado_id'))
                except Exception:
                    a = None
            # Fallback: lista de almoxarifados associados ao setor
            if not a:
                try:
                    aids = (se or {}).get('almoxarifado_ids') or []
                    if isinstance(aids, list) and len(aids) > 0:
                        a = self._find_by_id('almoxarifados', aids[0])
                except Exception:
                    a = None
            # Fallback adicional: lista de sub_almoxarifados associados ao setor
            # (derivar almoxarifado e então central a partir do primeiro sub)
            if not a:
                try:
                    sids = (se or {}).get('sub_almoxarifado_ids') or []
                    if isinstance(sids, list) and len(sids) > 0:
                        s_multi = self._find_by_id('sub_almoxarifados', sids[0])
                        if s_multi:
                            a = self._find_by_id('almoxarifados', (s_multi or {}).get('almoxarifado_id'))
                except Exception:
                    a = None
            cid = (a or {}).get('central_id')
            c = self._find_by_id('centrais', cid)
            try:
                return str((c or {}).get('_id')) if c else None
            except Exception:
                return cid
        return None

    def can_access_central(self, central_id):
        level = self.nivel_acesso
        if level == 'super_admin':
            return True
        if central_id is None:
            return False
        # Admin de central: acesso apenas à própria central
        if level == 'admin_central':
            u_cid = self._central_id_of_local('central', self.central_id)
            t_cid = self._central_id_of_local('central', central_id)
            return (u_cid is not None) and (t_cid is not None) and str(u_cid) == str(t_cid)
        # Secretário: acesso global a qualquer central
        if level == 'secretario':
            return True
        if level == 'gerente_almox' and self.almoxarifado_id is not None:
            u_cid = self._central_id_of_local('almoxarifado', self.almoxarifado_id)
            t_cid = self._central_id_of_local('central', central_id)
            return (u_cid is not None) and (t_cid is not None) and str(u_cid) == str(t_cid)
        if level == 'resp_sub_almox' and self.sub_almoxarifado_id is not None:
            u_cid = self._central_id_of_local('sub_almoxarifado', self.sub_almoxarifado_id)
            t_cid = self._central_id_of_local('central', central_id)
            return (u_cid is not None) and (t_cid is not None) and str(u_cid) == str(t_cid)
        if level == 'operador_setor' and self.setor_id is not None:
            u_cid = self._central_id_of_local('setor', self.setor_id)
            t_cid = self._central_id_of_local('central', central_id)
            return (u_cid is not None) and (t_cid is not None) and str(u_cid) == str(t_cid)
        return False
    
    def can_access_almoxarifado(self, almoxarifado_id):
        level = self.nivel_acesso
        if level == 'super_admin':
            return True
        if level == 'secretario':
            return True
        if almoxarifado_id is None:
            return False
        a = self._find_by_id('almoxarifados', almoxarifado_id)
        if not a:
            return False
        # Admin de central: acesso a almoxarifados da própria central
        if level == 'admin_central':
            c_target = (a or {}).get('central_id')
            c_user = self.central_id
            if (c_target is not None) and (c_user is not None):
                try:
                    cdoc1 = self._find_by_id('centrais', c_target)
                    cdoc2 = self._find_by_id('centrais', c_user)
                    if cdoc1 and cdoc2:
                        return str(cdoc1.get('_id')) == str(cdoc2.get('_id'))
                except Exception:
                    pass
                return str(c_target) == str(c_user)
            return False
        if level == 'gerente_almox':
            # Permitir acesso a QUALQUER almoxarifado da MESMA CENTRAL do gerente
            a1 = self._find_by_id('almoxarifados', almoxarifado_id)
            c_target = (a1 or {}).get('central_id')
            # Resolver central do usuário: pelo almox vinculado OU diretamente pelo central_id do usuário
            c_user = None
            if self.almoxarifado_id is not None:
                a2 = self._find_by_id('almoxarifados', self.almoxarifado_id)
                c_user = (a2 or {}).get('central_id')
            if c_user is None and self.central_id is not None:
                c_user = self.central_id
            # Se ambas centrais forem conhecidas, comparar
            if (c_target is not None) and (c_user is not None):
                try:
                    cdoc1 = self._find_by_id('centrais', c_target)
                    cdoc2 = self._find_by_id('centrais', c_user)
                    if cdoc1 and cdoc2:
                        return str(cdoc1.get('_id')) == str(cdoc2.get('_id'))
                except Exception:
                    pass
                return str(c_target) == str(c_user)
            # Fallback: se não foi possível resolver centrais, permitir quando o almox é exatamente o vinculado
            try:
                return self.almoxarifado_id is not None and str((a1 or {}).get('_id')) == str(self.almoxarifado_id)
            except Exception:
                return False
        if level == 'resp_sub_almox' and self.sub_almoxarifado_id is not None:
            s = self._find_by_id('sub_almoxarifados', self.sub_almoxarifado_id)
            a1 = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
            a2 = self._find_by_id('almoxarifados', almoxarifado_id)
            try:
                return (a1 is not None) and (a2 is not None) and str(a1.get('_id')) == str(a2.get('_id'))
            except Exception:
                return str((s or {}).get('almoxarifado_id')) == str(almoxarifado_id)
        # operador_setor não tem acesso direto a almoxarifado
        return False

    def can_access_sub_almoxarifado(self, sub_almoxarifado_id):
        level = self.nivel_acesso
        if level == 'super_admin':
            return True
        if level == 'secretario':
            return True
        if sub_almoxarifado_id is None:
            return False
        s = self._find_by_id('sub_almoxarifados', sub_almoxarifado_id)
        if not s:
            return False
        # Admin de central: acesso a sub‑almoxarifados da própria central
        if level == 'admin_central':
            a1 = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
            c_target = (a1 or {}).get('central_id')
            c_user = self.central_id
            if (c_target is not None) and (c_user is not None):
                try:
                    cdoc1 = self._find_by_id('centrais', c_target)
                    cdoc2 = self._find_by_id('centrais', c_user)
                    if cdoc1 and cdoc2:
                        return str(cdoc1.get('_id')) == str(cdoc2.get('_id'))
                except Exception:
                    pass
                return str(c_target) == str(c_user)
            return False
        if level == 'gerente_almox':
            # Permitir acesso a QUALQUER sub-almox de almox pertencente à MESMA CENTRAL do gerente
            a1 = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
            c_target = (a1 or {}).get('central_id')
            c_user = None
            if self.almoxarifado_id is not None:
                a2 = self._find_by_id('almoxarifados', self.almoxarifado_id)
                c_user = (a2 or {}).get('central_id')
            if c_user is None and self.central_id is not None:
                c_user = self.central_id
            if (c_target is not None) and (c_user is not None):
                try:
                    cdoc1 = self._find_by_id('centrais', c_target)
                    cdoc2 = self._find_by_id('centrais', c_user)
                    if cdoc1 and cdoc2:
                        return str(cdoc1.get('_id')) == str(cdoc2.get('_id'))
                except Exception:
                    pass
                return str(c_target) == str(c_user)
            # Fallback: permitir acesso quando sub pertence exatamente ao almox vinculado ao usuário
            try:
                return self.almoxarifado_id is not None and str((s or {}).get('almoxarifado_id')) == str(self.almoxarifado_id)
            except Exception:
                return False
        if level == 'resp_sub_almox':
            s1 = self._find_by_id('sub_almoxarifados', sub_almoxarifado_id)
            s2 = self._find_by_id('sub_almoxarifados', self.sub_almoxarifado_id)
            try:
                return (s1 is not None) and (s2 is not None) and str(s1.get('_id')) == str(s2.get('_id'))
            except Exception:
                return str(sub_almoxarifado_id) == str(self.sub_almoxarifado_id)
        # operador_setor não tem acesso direto a sub_almoxarifado
        return False
    
    def can_access_setor(self, setor_id):
        level = self.nivel_acesso
        if level == 'super_admin':
            return True
        if level == 'secretario':
            return True
        if setor_id is None:
            return False
        se = self._find_by_id('setores', setor_id)
        if not se:
            return False
        # Admin central sem restrição: acesso a qualquer setor
        if level == 'admin_central':
            return True
        if level == 'gerente_almox':
            cid_t = self._central_id_of_local('setor', setor_id)
            # Resolver central do usuário via almox vinculado ou diretamente via central_id
            cid_u = None
            if self.almoxarifado_id is not None:
                cid_u = self._central_id_of_local('almoxarifado', self.almoxarifado_id)
            if cid_u is None and self.central_id is not None:
                cid_u = self._central_id_of_local('central', self.central_id)
            return (cid_t is not None) and (cid_u is not None) and str(cid_t) == str(cid_u)
        if level == 'resp_sub_almox':
            # Permitir acesso a setores do MESMO sub_almox do usuário
            s1 = self._find_by_id('sub_almoxarifados', (se or {}).get('sub_almoxarifado_id'))
            s2 = self._find_by_id('sub_almoxarifados', self.sub_almoxarifado_id)
            try:
                if (s1 is not None) and (s2 is not None) and str(s1.get('_id')) == str(s2.get('_id')):
                    return True
            except Exception:
                if str((se or {}).get('sub_almoxarifado_id')) == str(self.sub_almoxarifado_id):
                    return True
            # Permitir acesso se setor listar explicitamente o sub_almox do usuário
            try:
                sub_ids = (se or {}).get('sub_almoxarifado_ids') or []
                for sid in sub_ids:
                    if str(sid) == str(self.sub_almoxarifado_id):
                        return True
            except Exception:
                pass
            # Permitir acesso a setores do mesmo ALMOXARIFADO do sub_almox do usuário
            try:
                u_sub = self._find_by_id('sub_almoxarifados', self.sub_almoxarifado_id)
                u_almox_id = (u_sub or {}).get('almoxarifado_id')
            except Exception:
                u_almox_id = None
            if u_almox_id is not None:
                # Checar vínculo direto
                try:
                    if str((se or {}).get('almoxarifado_id')) == str(u_almox_id):
                        return True
                except Exception:
                    pass
                # Checar lista de vínculos
                try:
                    aids = (se or {}).get('almoxarifado_ids') or []
                    for aid in aids:
                        if str(aid) == str(u_almox_id):
                            return True
                except Exception:
                    pass
            return False
        if level == 'operador_setor':
            se1 = self._find_by_id('setores', setor_id)
            se2 = self._find_by_id('setores', self.setor_id)
            try:
                return (se1 is not None) and (se2 is not None) and str(se1.get('_id')) == str(se2.get('_id'))
            except Exception:
                return str(setor_id) == str(self.setor_id)
        return False

    def can_access_local(self, tipo: str, local_id):
        tipo = (tipo or '').lower()
        if tipo == 'central':
            return self.can_access_central(local_id)
        if tipo == 'almoxarifado':
            return self.can_access_almoxarifado(local_id)
        if tipo == 'sub_almoxarifado':
            return self.can_access_sub_almoxarifado(local_id)
        if tipo == 'setor':
            return self.can_access_setor(local_id)
        return False

    def can_move_between(self, origem: dict, destino: dict) -> bool:
        """
        Verifica se o usuário pode movimentar entre origem e destino.
        Regras por nível:
          - super_admin: pode tudo
          - admin_central: pode entre locais da sua central, incluindo 'central'
          - gerente_almox: apenas entre 'almoxarifado'/'sub_almoxarifado'/'setor' do seu almoxarifado
          - resp_sub_almox: apenas entre seu 'sub_almoxarifado' e seus 'setores'
          - operador_setor: não pode movimentar
        """
        level = self.nivel_acesso
        # Liberar completamente movimentações para super_admin, admin_central e secretario
        if level in ('super_admin', 'admin_central', 'secretario'):
            return True

        o_tipo = (origem or {}).get('tipo')
        o_id = (origem or {}).get('id')
        d_tipo = (destino or {}).get('tipo')
        d_id = (destino or {}).get('id')

        if not (o_tipo and o_id and d_tipo and d_id):
            return False

        # Deve ter acesso a ambos
        if not (self.can_access_local(o_tipo, o_id) and self.can_access_local(d_tipo, d_id)):
            return False

        allowed_types = {
            'admin_central': {'central', 'almoxarifado', 'sub_almoxarifado', 'setor'},
            'gerente_almox': {'almoxarifado', 'sub_almoxarifado', 'setor'},
            'resp_sub_almox': {'almoxarifado', 'sub_almoxarifado', 'setor'},
            'operador_setor': set(),
        }
        if level in allowed_types:
            if o_tipo not in allowed_types[level] or d_tipo not in allowed_types[level]:
                return False
            # Restrição adicional para resp_sub_almox:
            # permitir apenas movimentações entre seu sub_almoxarifado e seus setores,
            # e transferência de almoxarifado -> sub_almoxarifado (mesma central/escopo).
            if level == 'resp_sub_almox':
                allowed_pairs = {
                    ('sub_almoxarifado', 'setor'),
                    ('setor', 'sub_almoxarifado'),
                    ('almoxarifado', 'sub_almoxarifado'),
                }
                if (str(o_tipo).lower(), str(d_tipo).lower()) not in allowed_pairs:
                    return False
        else:
            # níveis não catalogados
            return False

        # Garantir que ambos pertencerem à mesma central para níveis abaixo de super_admin
        o_cid = self._central_id_of_local(o_tipo, o_id)
        d_cid = self._central_id_of_local(d_tipo, d_id)
        if level == 'admin_central':
            # Sem restrição por central
            return True
        if level == 'gerente_almox' or level == 'resp_sub_almox':
            return str(o_cid) == str(d_cid)
        # operador_setor já retornaria False
        return False

    def can_access_produto(self, produto_id):
        level = self.nivel_acesso
        if level == 'super_admin':
            return True
        if level == 'secretario':
            return True
        p = self._find_by_id('produtos', produto_id)
        if not p:
            return False
        p_cid = (p or {}).get('central_id')
        if level == 'admin_central':
            expected_cid = self.central_id
            if expected_cid is None:
                return False
            try:
                p_central = self._find_by_id('centrais', p_cid)
                e_central = self._find_by_id('centrais', expected_cid)
                if p_central and e_central:
                    return str(p_central.get('_id')) == str(e_central.get('_id'))
            except Exception:
                pass
            return str(p_cid) == str(expected_cid)
        if level in ('gerente_almox', 'resp_sub_almox', 'operador_setor'):
            # Produtos vinculados à central do usuário
            # Para níveis inferiores, checamos apenas a central
            # (regra de movimentação já impede operações fora do escopo)
            expected_cid = None
            if self.central_id is not None:
                expected_cid = self.central_id
            else:
                # derivar pelo local do usuário
                if level == 'gerente_almox' and self.almoxarifado_id is not None:
                    a = self._find_by_id('almoxarifados', self.almoxarifado_id)
                    expected_cid = (a or {}).get('central_id')
                elif level == 'resp_sub_almox' and self.sub_almoxarifado_id is not None:
                    s = self._find_by_id('sub_almoxarifados', self.sub_almoxarifado_id)
                    a = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
                    expected_cid = (a or {}).get('central_id')
                elif level == 'operador_setor' and self.setor_id is not None:
                    se = self._find_by_id('setores', self.setor_id)
                    s = self._find_by_id('sub_almoxarifados', (se or {}).get('sub_almoxarifado_id'))
                    a = self._find_by_id('almoxarifados', (s or {}).get('almoxarifado_id'))
                    expected_cid = (a or {}).get('central_id')
            if expected_cid is None:
                return False
            # Normalizar ambos contra coleção de centrais para suportar ids inteiros e ObjectIds
            try:
                p_central = self._find_by_id('centrais', p_cid)
                e_central = self._find_by_id('centrais', expected_cid)
                if p_central and e_central:
                    return str(p_central.get('_id')) == str(e_central.get('_id'))
            except Exception:
                pass
            return str(p_cid) == str(expected_cid)
        return False


def init_login_manager(app):
    """Inicializa o gerenciador de login"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faÃ§a login para acessar esta pÃ¡gina.'
    login_manager.login_message_category = 'info'

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        # Retorna JSON 401 para requisições de API, senão redireciona para login
        is_api_request = (request.is_json or 
                          request.path.startswith('/api/') or 
                          'application/json' in request.headers.get('Accept', ''))
        if is_api_request:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        return redirect(url_for(login_manager.login_view))

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID (MongoDB)"""
    try:
        if extensions.mongo_db is None:
            try:
                dev = session.get('dev_user')
                if dev and str(dev.get('_id')) == str(user_id):
                    return MongoUser(dev)
            except Exception:
                pass
            return None
        doc = extensions.mongo_db['usuarios'].find_one({'_id': ObjectId(user_id)})
        return MongoUser(doc) if doc else None
    except Exception:
        return None


def log_auditoria(acao, tabela=None, registro_id=None, dados_anteriores=None, dados_novos=None):
    """Registra uma ação de auditoria (MongoDB)"""
    try:
        if current_user.is_authenticated and (extensions.mongo_db is not None):
            extensions.mongo_db['logs_auditoria'].insert_one({
                'usuario_id': current_user.get_id(),
                'acao': acao,
                'tabela': tabela,
                'registro_id': registro_id,
                'dados_anteriores': dados_anteriores,
                'dados_novos': dados_novos,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'timestamp': datetime.utcnow(),
            })
    except Exception as e:
        try:
            current_app.logger.error(f"Erro ao registrar log de auditoria: {e}")
        except Exception:
            pass


def authenticate_user(username, password):
    """Autentica um usuário (MongoDB)"""
    try:
        if extensions.mongo_db is None:
            current_app.logger.error('MongoDB não inicializado')
            return None
        current_app.logger.debug(f"AUTH: tentando autenticar username='{username}'")
        doc = extensions.mongo_db['usuarios'].find_one({'username': username})
        current_app.logger.debug(f"AUTH: usuario encontrado? {bool(doc)}")
        if doc:
            current_app.logger.debug(f"AUTH: ativo={doc.get('ativo')} has_hash={'password_hash' in doc}")
            pwd_ok = check_password_hash(doc.get('password_hash', ''), password)
            current_app.logger.debug(f"AUTH: senha confere? {pwd_ok}")
            if doc.get('ativo', True) and pwd_ok:
                usuario = MongoUser(doc)
                extensions.mongo_db['usuarios'].update_one({'_id': doc['_id']}, {'$set': {'ultimo_login': datetime.utcnow()}})
                log_auditoria('LOGIN')
                return usuario
        return None
    except Exception as e:
        try:
            current_app.logger.error(f"Erro na autenticação: {e}")
        except Exception:
            pass
        return None


def logout_user_with_audit():
    """Faz logout do usuÃ¡rio com registro de auditoria (MongoDB)"""
    try:
        if current_user.is_authenticated:
            log_auditoria('LOGOUT')
        logout_user()
    except Exception as e:
        try:
            current_app.logger.error(f"Erro no logout: {e}")
        except Exception:
            pass

# Decoradores de autorizaÃ§Ã£o por nÃ­vel hierÃ¡rquico

def require_level(*allowed_levels):
    """
    Decorador que requer níveis específicos de acesso
    
    Args:
        allowed_levels: Lista de níveis permitidos
                       ('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Detecta se é uma requisição de API
            is_api_request = (request.is_json or 
                            request.path.startswith('/api/') or 
                            'application/json' in request.headers.get('Accept', ''))
            
            # Modo dev/test: leitura pública de GET/HEAD na API
            try:
                if is_api_request and request.method in ('GET', 'HEAD'):
                    from flask import current_app
                    if bool(current_app.config.get('ALLOW_PUBLIC_API_READ')):
                        return f(*args, **kwargs)
                # Se não é leitura pública, segue fluxo normal
            except Exception:
                pass
            
            if not current_user.is_authenticated:
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))
            
            if current_user.nivel_acesso not in allowed_levels:
                if is_api_request:
                    return jsonify({'error': 'Acesso negado - nível insuficiente'}), 403
                flash('Você não tem permissão para acessar esta funcionalidade.', 'error')
                # Redireciona para uma página segura que não causa loop de redirecionamento
                return redirect(url_for('auth.profile'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_super_admin(f):
    """Decorador que requer acesso de super administrador"""
    return require_level('super_admin', 'secretario')(f)

def require_admin_or_above(f):
    """Decorador que requer acesso de administrador ou superior"""
    return require_level('super_admin', 'admin_central', 'secretario')(f)

def require_manager_or_above(f):
    """Decorador que requer acesso de gerente ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'secretario')(f)

def require_responsible_or_above(f):
    """Decorador que requer acesso de responsÃ¡vel ou superior"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'secretario')(f)

def require_any_level(f):
    """Decorador que requer qualquer nÃ­vel de acesso (apenas login)"""
    return require_level('super_admin', 'admin_central', 'gerente_almox', 'resp_sub_almox', 'operador_setor', 'secretario')(f)

# Decoradores de autorizaÃ§Ã£o por escopo hierÃ¡rquico

def require_central_access(central_id_param='central_id'):
    """
    Decorador que verifica acesso a uma central específica
    
    Args:
        central_id_param: Nome do parâmetro que contém o ID da central
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID da central dos parâmetros da URL, form ou JSON
            central_id = None
            if central_id_param in kwargs:
                central_id = kwargs[central_id_param]
            elif request.method == 'GET':
                central_id = request.args.get(central_id_param)
            elif request.is_json:
                central_id = request.json.get(central_id_param)
            else:
                central_id = request.form.get(central_id_param)
            
            if central_id and not current_user.can_access_central(central_id):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - central não autorizada'}), 403
                flash('Você não tem permissão para acessar esta central.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_almoxarifado_access(almoxarifado_id_param='almoxarifado_id'):
    """
    Decorador que verifica acesso a um almoxarifado específico
    
    Args:
        almoxarifado_id_param: Nome do parâmetro que contém o ID do almoxarifado
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID do almoxarifado dos parâmetros da URL, form ou JSON
            almoxarifado_id = None
            if almoxarifado_id_param in kwargs:
                almoxarifado_id = kwargs[almoxarifado_id_param]
            elif request.method == 'GET':
                almoxarifado_id = request.args.get(almoxarifado_id_param)
            elif request.is_json:
                almoxarifado_id = request.json.get(almoxarifado_id_param)
            else:
                almoxarifado_id = request.form.get(almoxarifado_id_param)
            
            if almoxarifado_id and not current_user.can_access_almoxarifado(almoxarifado_id):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - almoxarifado não autorizado'}), 403
                flash('Você não tem permissão para acessar este almoxarifado.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_sub_almoxarifado_access(sub_almoxarifado_id_param='sub_almoxarifado_id'):
    """
    Decorador que verifica acesso a um sub-almoxarifado específico
    
    Args:
        sub_almoxarifado_id_param: Nome do parâmetro que contém o ID do sub-almoxarifado
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Exige login com tratamento de API
            if not current_user.is_authenticated:
                is_api_request = (request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''))
                if is_api_request:
                    return jsonify({'error': 'Usuário não autenticado'}), 401
                return redirect(url_for('auth.login'))

            # Obtém o ID do sub-almoxarifado dos parâmetros da URL, form ou JSON
            sub_almoxarifado_id = None
            if sub_almoxarifado_id_param in kwargs:
                sub_almoxarifado_id = kwargs[sub_almoxarifado_id_param]
            elif request.method == 'GET':
                sub_almoxarifado_id = request.args.get(sub_almoxarifado_id_param)
            elif request.is_json:
                sub_almoxarifado_id = request.json.get(sub_almoxarifado_id_param)
            else:
                sub_almoxarifado_id = request.form.get(sub_almoxarifado_id_param)
            
            if sub_almoxarifado_id and not current_user.can_access_sub_almoxarifado(sub_almoxarifado_id):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - sub-almoxarifado não autorizado'}), 403
                flash('Você não tem permissão para acessar este sub-almoxarifado.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_setor_access(setor_id_param='setor_id'):
    """
    Decorador que verifica acesso a um setor especÃ­fico
    
    Args:
        setor_id_param: Nome do parÃ¢metro que contÃ©m o ID do setor
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # ObtÃ©m o ID do setor dos parÃ¢metros da URL, form ou JSON
            setor_id = None
            if setor_id_param in kwargs:
                setor_id = kwargs[setor_id_param]
            elif request.method == 'GET':
                setor_id = request.args.get(setor_id_param)
            elif request.is_json:
                setor_id = request.json.get(setor_id_param)
            else:
                setor_id = request.form.get(setor_id_param)
            
            if setor_id and not current_user.can_access_setor(setor_id):
                if request.is_json:
                    return jsonify({'error': 'Acesso negado - setor nÃ£o autorizado'}), 403
                flash('VocÃª nÃ£o tem permissÃ£o para acessar este setor.', 'error')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Filtros de escopo automÃ¡ticos

class ScopeFilter:
    """Classe para aplicar filtros de escopo baseados no usuÃ¡rio logado"""
    
    @staticmethod
    def filter_centrais(query):
        """Filtra centrais baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)  # Nenhum resultado
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todas as centrais
        elif current_user.nivel_acesso == 'admin_central':
            return query.filter_by(id=current_user.central_id)
        elif current_user.nivel_acesso == 'gerente_almox' and current_user.almoxarifado:
            return query.filter_by(id=current_user.almoxarifado.central_id)
        elif current_user.nivel_acesso == 'resp_sub_almox' and current_user.sub_almoxarifado:
            return query.filter_by(id=current_user.sub_almoxarifado.almoxarifado.central_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado.almoxarifado.central_id)
        
        return query.filter(False)  # Nenhum resultado por padrÃ£o
    
    @staticmethod
    def filter_almoxarifados(query):
        """Filtra almoxarifados baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os almoxarifados
        elif current_user.nivel_acesso == 'admin_central':
            return query.filter_by(central_id=current_user.central_id)
        elif current_user.nivel_acesso == 'gerente_almox':
            return query.filter_by(id=current_user.almoxarifado_id)
        elif current_user.nivel_acesso == 'resp_sub_almox' and current_user.sub_almoxarifado:
            return query.filter_by(id=current_user.sub_almoxarifado.almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado.almoxarifado_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_sub_almoxarifados(query):
        """Filtra sub-almoxarifados baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os sub-almoxarifados
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import Almoxarifado, SubAlmoxarifado
            almoxarifados_ids = [a.id for a in Almoxarifado.query.filter_by(central_id=current_user.central_id).all()]
            return query.filter(SubAlmoxarifado.almoxarifado_id.in_(almoxarifados_ids))
        elif current_user.nivel_acesso == 'gerente_almox':
            return query.filter_by(almoxarifado_id=current_user.almoxarifado_id)
        elif current_user.nivel_acesso == 'resp_sub_almox':
            return query.filter_by(id=current_user.sub_almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor' and current_user.setor:
            return query.filter_by(id=current_user.setor.sub_almoxarifado_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_setores(query):
        """Filtra setores baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todos os setores
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import SubAlmoxarifado, Almoxarifado, Setor
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            return query.filter(Setor.sub_almoxarifado_id.in_(sub_almoxarifados_ids))
        elif current_user.nivel_acesso == 'gerente_almox':
            from models.hierarchy import SubAlmoxarifado, Setor
            sub_almoxarifados_ids = [sa.id for sa in SubAlmoxarifado.query.filter_by(almoxarifado_id=current_user.almoxarifado_id).all()]
            return query.filter(Setor.sub_almoxarifado_id.in_(sub_almoxarifados_ids))
        elif current_user.nivel_acesso == 'resp_sub_almox':
            return query.filter_by(sub_almoxarifado_id=current_user.sub_almoxarifado_id)
        elif current_user.nivel_acesso == 'operador_setor':
            return query.filter_by(id=current_user.setor_id)
        
        return query.filter(False)
    
    @staticmethod
    def filter_estoque(query):
        """Filtra estoque baseado no escopo do usuÃ¡rio"""
        if not current_user.is_authenticated:
            return query.filter(False)
        
        if current_user.nivel_acesso == 'super_admin':
            return query  # Acesso a todo o estoque
        elif current_user.nivel_acesso == 'admin_central':
            from models.hierarchy import Setor, SubAlmoxarifado, Almoxarifado
            from models.produto import EstoqueProduto
            # Filtrar por almoxarifados, sub-almoxarifados e setores da central
            almoxarifados_ids = db.session.query(Almoxarifado.id).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            setores_ids = db.session.query(Setor.id).join(SubAlmoxarifado).join(Almoxarifado).filter(Almoxarifado.central_id == current_user.central_id).subquery()
            return query.filter(
                db.or_(
                    EstoqueProduto.almoxarifado_id.in_(almoxarifados_ids),
                    EstoqueProduto.sub_almoxarifado_id.in_(sub_almoxarifados_ids),
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'gerente_almox':
            from models.hierarchy import Setor, SubAlmoxarifado
            from models.produto import EstoqueProduto
            # Filtrar por almoxarifado, sub-almoxarifados e setores do almoxarifado
            sub_almoxarifados_ids = db.session.query(SubAlmoxarifado.id).filter(SubAlmoxarifado.almoxarifado_id == current_user.almoxarifado_id).subquery()
            setores_ids = db.session.query(Setor.id).join(SubAlmoxarifado).filter(SubAlmoxarifado.almoxarifado_id == current_user.almoxarifado_id).subquery()
            return query.filter(
                db.or_(
                    EstoqueProduto.almoxarifado_id == current_user.almoxarifado_id,
                    EstoqueProduto.sub_almoxarifado_id.in_(sub_almoxarifados_ids),
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'resp_sub_almox':
            from models.hierarchy import Setor
            from models.produto import EstoqueProduto
            # Filtrar por sub-almoxarifado e setores do sub-almoxarifado
            setores_ids = [s.id for s in Setor.query.filter_by(sub_almoxarifado_id=current_user.sub_almoxarifado_id).all()]
            return query.filter(
                db.or_(
                    EstoqueProduto.sub_almoxarifado_id == current_user.sub_almoxarifado_id,
                    EstoqueProduto.setor_id.in_(setores_ids)
                )
            )
        elif current_user.nivel_acesso == 'operador_setor':
            return query.filter_by(setor_id=current_user.setor_id)
        
        return query.filter(False)

def get_user_context():
    """ObtÃ©m o contexto do usuÃ¡rio para injeÃ§Ã£o em templates (MongoDB)"""
    if current_user.is_authenticated:
        ui_config = get_ui_blocks_config()
        menu_blocks = ui_config.get_menu_blocks_for_user(current_user.nivel_acesso)
        dashboard_widgets = ui_config.get_dashboard_widgets_for_user(current_user.nivel_acesso)
        try:
            current_app.logger.debug(
                f"CTX: nivel={current_user.nivel_acesso} menus={len(menu_blocks)} widgets={len(dashboard_widgets)}"
            )
        except Exception:
            pass
        level = current_user.nivel_acesso or ''
        flags = {
            'is_super_admin': level == 'super_admin',
            'is_admin_central': level == 'admin_central',
            'is_gerente_almox': level == 'gerente_almox',
            'is_resp_sub_almox': level == 'resp_sub_almox',
            'is_operador_setor': level == 'operador_setor',
            'is_secretario': level == 'secretario',
        }
        scope_labels = {
            'super_admin': 'Super Admin (Todos os escopos)',
            'admin_central': 'Admin Central',
            'gerente_almox': 'Gerente de Almoxarifado',
            'resp_sub_almox': 'ResponsÃ¡vel de Sub-Almoxarifado',
            'operador_setor': 'Operador de Setor',
            'secretario': 'Secretário',
        }
        return {
            'current_user': current_user,
            'user': current_user,
            'menu_blocks': menu_blocks,
            'dashboard_widgets': dashboard_widgets,
            'scope_name': scope_labels.get(level, 'UsuÃ¡rio'),
            'user_level': level,
            'user_name': getattr(current_user, 'nome_completo', None),
            **flags
        }
    else:
        return {
            'current_user': None,
            'user': None,
            'menu_blocks': [],
            'dashboard_widgets': [],
            'scope_name': '',
            'user_level': None,
            'user_name': None,
            'is_super_admin': False,
            'is_admin_central': False,
            'is_gerente_almox': False,
            'is_resp_sub_almox': False,
            'is_operador_setor': False,
        }
