from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
# Removido: from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
# Removido: from models.produto import Produto, EstoqueProduto, LoteProduto, MovimentacaoProduto
# Removido: from models.usuario import Usuario
# Removido: from models.categoria import CategoriaProduto
# Removido: from extensions import db
from auth import (require_any_level, require_manager_or_above, require_admin_or_above, 
                  ScopeFilter)
from config.ui_blocks import get_ui_blocks_config
import extensions
from pymongo import ReturnDocument
from datetime import datetime
from bson import ObjectId

main_bp = Blueprint('main', __name__)

# Helper compartilhado para resolver documento por id sequencial ou ObjectId string
def _find_by_id(coll_name: str, value):
    coll = extensions.mongo_db[coll_name]
    doc = None
    try:
        # tentar id sequencial
        if str(value).isdigit():
            doc = coll.find_one({'id': int(value)})
    except Exception:
        doc = None
    if not doc:
        # tentar ObjectId
        try:
            doc = coll.find_one({'_id': ObjectId(str(value))})
        except Exception:
            doc = None
    if not doc and isinstance(value, str):
        # tentar id/string direta
        doc = coll.find_one({'id': value}) or coll.find_one({'_id': value})
    return doc


@main_bp.route('/')
@require_any_level
def index():
    """Página inicial"""
    return render_template('index.html')

@main_bp.route('/configuracoes')
@require_admin_or_above
def configuracoes():
    """Página de configurações"""
    print(f"DEBUG: current_user.nivel_acesso = {current_user.nivel_acesso}")
    ui_config = get_ui_blocks_config()
    settings_sections = ui_config.get_settings_sections_for_user(current_user.nivel_acesso)
    print(f"DEBUG: settings_sections count = {len(settings_sections)}")
    for section in settings_sections:
        print(f"DEBUG: section = {section.id} - {section.title}")
    return render_template('configuracoes.html', settings_sections=settings_sections)

@main_bp.route('/configuracoes/hierarquia')
@require_admin_or_above
def configuracoes_hierarquia():
    """Página de configuração da hierarquia (desativada até migração completa para Mongo)"""
    # Placeholder sem consultas SQLAlchemy
    centrais = []
    almoxarifados = []
    sub_almoxarifados = []
    setores = []
    
    return render_template('configuracoes/hierarquia.html',
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

# ==================== PRODUTOS ====================

@main_bp.route('/produtos')
@require_any_level
def produtos():
    """Página de produtos (lista de categorias desativada até migração Mongo)"""
    categorias = []
    return render_template('produtos/index.html', categorias=categorias)

@main_bp.route('/produtos/cadastro')
@require_manager_or_above
def produtos_cadastro():
    """Página de cadastro de produtos"""
    categorias = []
    try:
        db = extensions.mongo_db
        if db is not None:
            cursor = db['categorias'].find({'$or': [{'ativo': True}, {'ativo': {'$exists': False}}]}, {'_id': 1, 'id': 1, 'nome': 1}).sort('nome', 1)
            for d in cursor:
                categorias.append({
                    'id': d.get('id') if d.get('id') is not None else str(d.get('_id')),
                    'nome': d.get('nome')
                })
    except Exception as e:
        print(f"Erro ao carregar categorias: {e}")
    return render_template('produtos/cadastro.html', categorias=categorias)

@main_bp.route('/produtos/<string:id>')
@require_any_level
def produtos_detalhes(id):
    """Página de detalhes do produto (placeholder)"""
    produto = None
    return render_template('produtos/detalhes.html', produto=produto)

@main_bp.route('/produtos/<string:id>/recebimento')
@require_any_level
def produtos_recebimento(id):
    """Página de recebimento de produtos (placeholders)"""
    produto = None
    # Placeholders sem consultas
    centrais = []
    almoxarifados = []
    sub_almoxarifados = []
    setores = []
    
    return render_template('produtos/recebimento.html', 
                         produto=produto,
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

@main_bp.route('/estoque')
@require_any_level
def estoque():
    """Página de consulta de estoque (placeholders)"""
    centrais = []
    almoxarifados = []
    sub_almoxarifados = []
    setores = []
    
    return render_template('produtos/estoque.html',
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

@main_bp.route('/movimentacoes')
@require_any_level
def movimentacoes():
    """Página de movimentações e transferências (MongoDB)"""
    db = extensions.mongo_db

    def norm_id(doc):
        if doc.get('id') is not None:
            return doc.get('id')
        _id = doc.get('_id')
        return str(_id) if _id is not None else None

    def norm_ref(value):
        try:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
        except Exception:
            pass
        return str(value) if value is not None else None

    # Carregar listas de locais quando Mongo estiver disponível
    centrais = []
    almoxarifados = []
    sub_almoxarifados = []
    setores = []

    if db is not None:
        for c in db['centrais'].find({}, {'id': 1, '_id': 1, 'nome': 1}):
            centrais.append({'id': norm_id(c), 'nome': c.get('nome')})
        for a in db['almoxarifados'].find({}, {'id': 1, '_id': 1, 'nome': 1, 'central_id': 1}):
            almoxarifados.append({'id': norm_id(a), 'nome': a.get('nome'), 'central_id': norm_ref(a.get('central_id'))})
        for s in db['sub_almoxarifados'].find({}, {'id': 1, '_id': 1, 'nome': 1, 'almoxarifado_id': 1}):
            sub_almoxarifados.append({'id': norm_id(s), 'nome': s.get('nome'), 'almoxarifado_id': norm_ref(s.get('almoxarifado_id'))})
        for s in db['setores'].find({}, {'id': 1, '_id': 1, 'nome': 1, 'sub_almoxarifado_id': 1}):
            setores.append({'id': norm_id(s), 'nome': s.get('nome'), 'sub_almoxarifado_id': norm_ref(s.get('sub_almoxarifado_id'))})

    return render_template('movimentacoes/index.html',
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores,
                         use_mongo=True)

# ==================== USUÁRIOS ====================

@main_bp.route('/configuracoes/usuarios')
@require_admin_or_above
def configuracoes_usuarios():
    """Página de gerenciamento de usuários (MongoDB)"""
    try:
        db = extensions.mongo_db
        if db is None:
            # Se Mongo não estiver inicializado, manter placeholders
            usuarios = []
            centrais = []
            almoxarifados = []
            sub_almoxarifados = []
            setores = []
            categorias = []
            return render_template('users/index.html',
                                   usuarios=usuarios,
                                   centrais=centrais,
                                   almoxarifados=almoxarifados,
                                   sub_almoxarifados=sub_almoxarifados,
                                   setores=setores,
                                   categorias=categorias)

        # Coletar listas auxiliares
        centrais_docs = list(db['centrais'].find({}, {'_id': 1, 'nome': 1}))
        almox_docs = list(db['almoxarifados'].find({}, {'_id': 1, 'nome': 1, 'central_id': 1}))
        sub_docs = list(db['sub_almoxarifados'].find({}, {'_id': 1, 'nome': 1, 'almoxarifado_id': 1}))
        setores_docs = list(db['setores'].find({}, {'_id': 1, 'nome': 1}))
        categorias_docs = list(db['categorias'].find({}, {'_id': 1, 'nome': 1, 'codigo': 1, 'cor': 1}))

        # Mapas para resolução rápida
        centrais_map = {str(d['_id']): d.get('nome') for d in centrais_docs}
        almox_map = {str(d['_id']): d.get('nome') for d in almox_docs}
        sub_map = {str(d['_id']): d.get('nome') for d in sub_docs}
        setor_map = {str(d['_id']): d.get('nome') for d in setores_docs}
        categorias_map = {str(d['_id']): {
            'id': str(d['_id']),
            'nome': d.get('nome'),
            'codigo': d.get('codigo'),
            'cor': d.get('cor')
        } for d in categorias_docs}

        # Classe de visualização para o template, com métodos esperados
        class UsuarioView:
            def __init__(self, doc: dict):
                self._doc = doc or {}
                self.id = str(self._doc.get('_id'))
                self.username = self._doc.get('username') or ''
                self.email = self._doc.get('email') or ''
                # fallback para nome
                self.nome_completo = (self._doc.get('nome_completo')
                                       or self._doc.get('nome')
                                       or self.username or 'Usuário')
                self.nivel_acesso = self._doc.get('nivel_acesso') or 'operador_setor'
                self.ativo = bool(self._doc.get('ativo', True))
                self.ultimo_login = self._doc.get('ultimo_login')
                # ids hierárquicos (podem ser ObjectId ou string)
                self.central_id = self._doc.get('central_id')
                self.almoxarifado_id = self._doc.get('almoxarifado_id')
                self.sub_almoxarifado_id = self._doc.get('sub_almoxarifado_id')
                self.setor_id = self._doc.get('setor_id')

            def _to_key(self, val):
                try:
                    from bson import ObjectId as _OID
                    if isinstance(val, _OID):
                        return str(val)
                except Exception:
                    pass
                return str(val) if val is not None else None

            def get_hierarchy_path(self):
                parts = []
                c = centrais_map.get(self._to_key(self.central_id))
                a = almox_map.get(self._to_key(self.almoxarifado_id))
                s = sub_map.get(self._to_key(self.sub_almoxarifado_id))
                t = setor_map.get(self._to_key(self.setor_id))
                for nm in [c, a, s, t]:
                    if nm:
                        parts.append(nm)
                return ' / '.join(parts) if parts else '—'

            def get_categorias_display(self):
                # Suporta campo "categorias_especificas" (lista de IDs) e "categoria_id" (principal)
                cat_ids = []
                val_multi = self._doc.get('categorias_especificas') or []
                if isinstance(val_multi, list):
                    cat_ids.extend(val_multi)
                val_single = self._doc.get('categoria_id')
                if val_single:
                    cat_ids.append(val_single)
                # Mapear
                cats = []
                for cid in cat_ids:
                    cm = categorias_map.get(self._to_key(cid))
                    if cm:
                        cats.append(cm)
                if not cats:
                    return {'tipo': 'todas', 'categorias': [], 'texto': 'Todas'}
                if len(cats) == 1:
                    return {'tipo': 'especifica', 'categorias': cats}
                return {'tipo': 'multiplas', 'categorias': cats, 'texto': f"{len(cats)} categorias"}

        # Buscar usuários
        usuarios_docs = list(db['usuarios'].find({}, {'password_hash': 0}).sort('nome_completo', 1))
        usuarios = [UsuarioView(doc) for doc in usuarios_docs]

        # Listas para selects do modal
        centrais = [{'id': str(d['_id']), 'nome': d.get('nome')} for d in centrais_docs]
        almoxarifados = [{'id': str(d['_id']), 'nome': d.get('nome'), 'central_id': str(d.get('central_id')) if d.get('central_id') else None} for d in almox_docs]
        sub_almoxarifados = [{'id': str(d['_id']), 'nome': d.get('nome'), 'almoxarifado_id': str(d.get('almoxarifado_id')) if d.get('almoxarifado_id') else None} for d in sub_docs]
        setores = [{'id': str(d['_id']), 'nome': d.get('nome')} for d in setores_docs]
        categorias = [{'id': str(d['_id']), 'nome': d.get('nome'), 'codigo': d.get('codigo'), 'cor': d.get('cor')} for d in categorias_docs]

        return render_template('users/index.html',
                               usuarios=usuarios,
                               centrais=centrais,
                               almoxarifados=almoxarifados,
                               sub_almoxarifados=sub_almoxarifados,
                               setores=setores,
                               categorias=categorias)
    except Exception as e:
        print(f"Erro ao carregar usuários: {e}")
        # Em caso de erro, garantir que a página renderize
        return render_template('users/index.html',
                               usuarios=[],
                               centrais=[],
                               almoxarifados=[],
                               sub_almoxarifados=[],
                               setores=[],
                               categorias=[])

@main_bp.route('/configuracoes/categorias')
@require_admin_or_above
def configuracoes_categorias():
    """Página de configuração de categorias de produtos"""
    return render_template('categorias/index.html')

# ==================== CATEGORIAS (MongoDB) ====================

@main_bp.route('/api/categorias', methods=['GET'])
@require_admin_or_above
def api_categorias_list():
    """Lista categorias com paginação, busca e filtro de status."""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = (request.args.get('search') or '').strip()
        ativo_param = request.args.get('ativo')

        coll = extensions.mongo_db['categorias']

        # Montar filtro
        filter_query = {}
        if ativo_param is not None and ativo_param != '':
            val = str(ativo_param).lower()
            if val in ('true', '1'):
                filter_query['ativo'] = True
            elif val in ('false', '0'):
                filter_query['ativo'] = False
        if search:
            filter_query['$or'] = [
                {'nome': {'$regex': search, '$options': 'i'}},
                {'codigo': {'$regex': search, '$options': 'i'}},
                {'descricao': {'$regex': search, '$options': 'i'}}
            ]

        total = coll.count_documents(filter_query)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        skip = max(0, (page - 1) * per_page)

        cursor = coll.find(filter_query).sort('nome', 1).skip(skip).limit(per_page)

        # Pré-carregar coleções relacionadas para contagem
        produtos_coll = extensions.mongo_db['produtos']
        usuarios_coll = extensions.mongo_db['usuarios']

        items = []
        for c in cursor:
            cid_seq = c.get('id')
            cid_oid = c.get('_id')
            cid_oid_str = str(cid_oid) if cid_oid else None
            # candidatos de comparação para produtos/usuarios
            pid_candidates = []
            if cid_seq is not None:
                pid_candidates.append(cid_seq)
            if cid_oid is not None:
                pid_candidates.append(cid_oid)
            if cid_oid_str is not None:
                pid_candidates.append(cid_oid_str)

            produtos_count = produtos_coll.count_documents({'categoria_id': {'$in': pid_candidates}})
            usuarios_count = usuarios_coll.count_documents({
                '$or': [
                    {'categoria_id': {'$in': pid_candidates}},
                    {'categorias_especificas': {'$in': [cid_oid_str] if cid_oid_str else []}}
                ]
            })

            items.append({
                'id': cid_seq if cid_seq is not None else cid_oid_str,
                'nome': c.get('nome'),
                'codigo': c.get('codigo'),
                'descricao': c.get('descricao'),
                'cor': c.get('cor') or '#6c757d',
                'ativo': bool(c.get('ativo', True)),
                'produtos_count': int(produtos_count),
                'usuarios_count': int(usuarios_count)
            })

        return jsonify({
            'items': items,
            'total': total,
            'pages': pages,
            'per_page': per_page,
            'current_page': page,
            'has_prev': page > 1,
            'has_next': page < pages,
            'prev_num': page - 1 if page > 1 else 1,
            'next_num': page + 1 if page < pages else pages
        })
    except Exception as e:
        return jsonify({'error': f'Erro ao listar categorias: {e}'}), 500

@main_bp.route('/api/categorias', methods=['POST'])
@require_admin_or_above
def api_categorias_create():
    """Cria nova categoria com validação de código único."""
    try:
        data = request.get_json(silent=True) or {}
        nome = (data.get('nome') or '').strip()
        codigo = (data.get('codigo') or '').strip().upper()
        descricao = (data.get('descricao') or '').strip()
        cor = (data.get('cor') or '#007bff').strip()
        ativo = bool(data.get('ativo', True))

        if not nome or not codigo:
            return jsonify({'error': 'Nome e código são obrigatórios'}), 400

        coll = extensions.mongo_db['categorias']
        # Verificar código único (case-insensitive)
        exists = coll.find_one({'codigo': codigo})
        if exists:
            return jsonify({'error': 'Código de categoria já existe'}), 400

        # Gerar id sequencial
        last = list(coll.find({}, {'id': 1}).sort('id', -1).limit(1))
        next_id = (last[0]['id'] + 1) if (last and isinstance(last[0].get('id'), int)) else 1

        doc = {
            'id': next_id,
            'nome': nome,
            'codigo': codigo,
            'descricao': descricao or None,
            'cor': cor or '#007bff',
            'ativo': ativo,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        coll.insert_one(doc)
        return jsonify({'message': 'Categoria criada com sucesso', 'id': doc['id']}), 201
    except Exception as e:
        return jsonify({'error': f'Erro ao criar categoria: {e}'}), 500

@main_bp.route('/api/categorias/<string:cat_id>', methods=['GET'])
@require_admin_or_above
def api_categorias_get(cat_id):
    """Obtém detalhes da categoria, suportando id sequencial ou ObjectId."""
    try:
        coll = extensions.mongo_db['categorias']
        query = None
        if str(cat_id).isdigit():
            query = {'id': int(cat_id)}
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                query = {'_id': ObjectId(cat_id)}
            except Exception:
                query = {'_id': cat_id}
        else:
            query = {'id': cat_id}

        c = coll.find_one(query)
        if not c:
            return jsonify({'error': 'Categoria não encontrada'}), 404

        # Contagens
        produtos_coll = extensions.mongo_db['produtos']
        usuarios_coll = extensions.mongo_db['usuarios']
        cid_seq = c.get('id')
        cid_oid = c.get('_id')
        cid_oid_str = str(cid_oid) if cid_oid else None
        pid_candidates = []
        if cid_seq is not None:
            pid_candidates.append(cid_seq)
        if cid_oid is not None:
            pid_candidates.append(cid_oid)
        if cid_oid_str is not None:
            pid_candidates.append(cid_oid_str)
        produtos_count = produtos_coll.count_documents({'categoria_id': {'$in': pid_candidates}})
        usuarios_count = usuarios_coll.count_documents({
            '$or': [
                {'categoria_id': {'$in': pid_candidates}},
                {'categorias_especificas': {'$in': [cid_oid_str] if cid_oid_str else []}}
            ]
        })

        return jsonify({
            'id': cid_seq if cid_seq is not None else cid_oid_str,
            'nome': c.get('nome'),
            'codigo': c.get('codigo'),
            'descricao': c.get('descricao'),
            'cor': c.get('cor') or '#6c757d',
            'ativo': bool(c.get('ativo', True)),
            'produtos_count': int(produtos_count),
            'usuarios_count': int(usuarios_count)
        })
    except Exception as e:
        return jsonify({'error': f'Erro ao obter categoria: {e}'}), 500

@main_bp.route('/api/categorias/<string:cat_id>', methods=['PUT'])
@require_admin_or_above
def api_categorias_update(cat_id):
    """Atualiza dados da categoria com validação de código único."""
    try:
        data = request.get_json(silent=True) or {}
        nome = (data.get('nome') or '').strip()
        codigo = (data.get('codigo') or '').strip().upper()
        descricao = (data.get('descricao') or '').strip()
        cor = (data.get('cor') or '').strip()
        ativo = data.get('ativo')

        coll = extensions.mongo_db['categorias']

        # Verificar existência
        if str(cat_id).isdigit():
            current = coll.find_one({'id': int(cat_id)})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                current = coll.find_one({'_id': ObjectId(cat_id)})
            except Exception:
                current = coll.find_one({'_id': cat_id})
        else:
            current = coll.find_one({'id': cat_id})
        if not current:
            return jsonify({'error': 'Categoria não encontrada'}), 404

        # Validar código único caso alterado
        if codigo and codigo != (current.get('codigo') or '').upper():
            exists = coll.find_one({'codigo': codigo})
            if exists and str(exists.get('_id')) != str(current.get('_id')):
                return jsonify({'error': 'Código de categoria já existe'}), 400

        update_fields = {}
        if nome:
            update_fields['nome'] = nome
        if codigo:
            update_fields['codigo'] = codigo
        update_fields['descricao'] = descricao or None
        if cor:
            update_fields['cor'] = cor
        if ativo is not None:
            update_fields['ativo'] = bool(ativo)
        update_fields['updated_at'] = datetime.utcnow()

        # Executar update
        if str(cat_id).isdigit():
            res = coll.update_one({'id': int(cat_id)}, {'$set': update_fields})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                res = coll.update_one({'_id': ObjectId(cat_id)}, {'$set': update_fields})
            except Exception:
                res = coll.update_one({'_id': cat_id}, {'$set': update_fields})
        else:
            res = coll.update_one({'id': cat_id}, {'$set': update_fields})

        if not res or res.matched_count == 0:
            return jsonify({'error': 'Categoria não encontrada para atualização'}), 404
        return jsonify({'message': 'Categoria atualizada com sucesso'})
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar categoria: {e}'}), 500

@main_bp.route('/api/categorias/<string:cat_id>/toggle-status', methods=['POST'])
@require_admin_or_above
def api_categorias_toggle_status(cat_id):
    """Alterna o status (ativo/inativo) da categoria."""
    try:
        coll = extensions.mongo_db['categorias']
        # Obter categoria atual
        if str(cat_id).isdigit():
            c = coll.find_one({'id': int(cat_id)})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                c = coll.find_one({'_id': ObjectId(cat_id)})
            except Exception:
                c = coll.find_one({'_id': cat_id})
        else:
            c = coll.find_one({'id': cat_id})
        if not c:
            return jsonify({'error': 'Categoria não encontrada'}), 404

        new_status = not bool(c.get('ativo', True))
        if str(cat_id).isdigit():
            coll.update_one({'id': int(cat_id)}, {'$set': {'ativo': new_status, 'updated_at': datetime.utcnow()}})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                coll.update_one({'_id': ObjectId(cat_id)}, {'$set': {'ativo': new_status, 'updated_at': datetime.utcnow()}})
            except Exception:
                coll.update_one({'_id': cat_id}, {'$set': {'ativo': new_status, 'updated_at': datetime.utcnow()}})
        else:
            coll.update_one({'id': cat_id}, {'$set': {'ativo': new_status, 'updated_at': datetime.utcnow()}})

        return jsonify({'message': f"Categoria {'ativada' if new_status else 'desativada'} com sucesso"})
    except Exception as e:
        return jsonify({'error': f'Erro ao alterar status: {e}'}), 500

@main_bp.route('/api/categorias/<string:cat_id>', methods=['DELETE'])
@require_admin_or_above
def api_categorias_delete(cat_id):
    """Exclui categoria, bloqueando caso haja referências em produtos/usuários."""
    try:
        coll = extensions.mongo_db['categorias']
        # Encontrar categoria
        if str(cat_id).isdigit():
            c = coll.find_one({'id': int(cat_id)})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                c = coll.find_one({'_id': ObjectId(cat_id)})
            except Exception:
                c = coll.find_one({'_id': cat_id})
        else:
            c = coll.find_one({'id': cat_id})
        if not c:
            return jsonify({'error': 'Categoria não encontrada'}), 404

        cid_seq = c.get('id')
        cid_oid = c.get('_id')
        cid_oid_str = str(cid_oid) if cid_oid else None
        pid_candidates = []
        if cid_seq is not None:
            pid_candidates.append(cid_seq)
        if cid_oid is not None:
            pid_candidates.append(cid_oid)
        if cid_oid_str is not None:
            pid_candidates.append(cid_oid_str)

        produtos_coll = extensions.mongo_db['produtos']
        usuarios_coll = extensions.mongo_db['usuarios']
        produtos_count = produtos_coll.count_documents({'categoria_id': {'$in': pid_candidates}})
        usuarios_count = usuarios_coll.count_documents({
            '$or': [
                {'categoria_id': {'$in': pid_candidates}},
                {'categorias_especificas': {'$in': [cid_oid_str] if cid_oid_str else []}}
            ]
        })

        if produtos_count > 0 or usuarios_count > 0:
            return jsonify({'error': 'Não é possível excluir: há produtos ou usuários associados a esta categoria'}), 400

        # Excluir
        if str(cat_id).isdigit():
            coll.delete_one({'id': int(cat_id)})
        elif isinstance(cat_id, str) and len(cat_id) == 24:
            try:
                coll.delete_one({'_id': ObjectId(cat_id)})
            except Exception:
                coll.delete_one({'_id': cat_id})
        else:
            coll.delete_one({'id': cat_id})

        return jsonify({'message': 'Categoria excluída com sucesso'})
    except Exception as e:
        return jsonify({'error': f'Erro ao excluir categoria: {e}'}), 500

# ==================== ROTAS DIRETAS PARA COMPATIBILIDADE COM TESTES ====================

@main_bp.route('/usuarios')
@require_admin_or_above
def users():
    """Rota direta para usuários (compatibilidade com testes)"""
    return configuracoes_usuarios()

@main_bp.route('/categorias')
@require_admin_or_above
def categorias():
    """Rota direta para categorias (compatibilidade com testes)"""
    return configuracoes_categorias()

@main_bp.route('/relatorios')
@require_admin_or_above
def relatorios():
    """Página de relatórios"""
    return render_template('relatorios/index.html')

# ==================== API PLACEHOLDERS (JSON) ====================

# --- USUÁRIOS (MongoDB) ---
@main_bp.route('/api/usuarios', methods=['GET'])
@require_admin_or_above
def api_usuarios_list():
    """Lista usuários com paginação básica (para compatibilidade futura)."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = (request.args.get('search') or '').strip()
    coll = extensions.mongo_db['usuarios']
    query = {}
    if search:
        query['$or'] = [
            {'username': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'nome_completo': {'$regex': search, '$options': 'i'}}
        ]
    total = coll.count_documents(query)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    skip = max(0, (page - 1) * per_page)
    items = []
    for u in coll.find(query, {'password_hash': 0}).sort('nome_completo', 1).skip(skip).limit(per_page):
        items.append({
            'id': str(u.get('_id')),
            'username': u.get('username'),
            'email': u.get('email'),
            'nome_completo': u.get('nome_completo') or u.get('nome'),
            'nivel_acesso': u.get('nivel_acesso') or 'operador_setor',
            'ativo': bool(u.get('ativo', True))
        })
    return jsonify({'items': items, 'page': page, 'pages': pages, 'per_page': per_page, 'total': total})

@main_bp.route('/api/usuarios', methods=['POST'])
@require_admin_or_above
def api_usuarios_create():
    # Apenas super administradores podem criar usuários
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin':
        return jsonify({'error': 'Apenas super administradores podem criar usuários'}), 403
    data = request.get_json(silent=True) or {}
    username = (data.get('login') or data.get('username') or '').strip()
    nome = (data.get('nome') or data.get('nome_completo') or '').strip()
    email = (data.get('email') or '').strip()
    nivel = (data.get('nivel') or data.get('nivel_acesso') or 'operador_setor').strip()
    senha = (data.get('senha') or '').strip()
    ativo = bool(data.get('ativo', True))
    if not username or not nome or not senha:
        return jsonify({'error': 'Username, nome e senha são obrigatórios'}), 400
    coll = extensions.mongo_db['usuarios']
    if coll.find_one({'username': username}):
        return jsonify({'error': 'Username já existe'}), 400
    # Hash de senha
    try:
        from werkzeug.security import generate_password_hash
    except Exception:
        return jsonify({'error': 'Falha ao importar gerador de hash'}), 500
    doc = {
        'username': username,
        'nome_completo': nome,
        'email': email,
        'nivel_acesso': nivel,
        'ativo': ativo,
        'central_id': data.get('central_id'),
        'almoxarifado_id': data.get('almoxarifado_id'),
        'sub_almoxarifado_id': data.get('sub_almoxarifado_id'),
        'setor_id': data.get('setor_id'),
        'categoria_id': data.get('categoria_id'),
        'password_hash': generate_password_hash(senha),
        'created_at': datetime.utcnow()
    }
    res = coll.insert_one(doc)
    return jsonify({'id': str(res.inserted_id), 'message': 'Usuário criado com sucesso'})

@main_bp.route('/api/usuarios/<string:user_id>', methods=['GET'])
@require_admin_or_above
def api_usuarios_detail(user_id):
    coll = extensions.mongo_db['usuarios']
    doc = None
    try:
        doc = coll.find_one({'_id': ObjectId(user_id)}, {'password_hash': 0})
    except Exception:
        doc = coll.find_one({'id': user_id}, {'password_hash': 0})
    if not doc:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({
        'id': str(doc.get('_id')) if doc.get('_id') else doc.get('id'),
        'nome_completo': doc.get('nome_completo') or doc.get('nome'),
        'username': doc.get('username'),
        'email': doc.get('email'),
        'nivel_acesso': doc.get('nivel_acesso') or 'operador_setor',
        'ativo': bool(doc.get('ativo', True)),
        'central_id': doc.get('central_id'),
        'almoxarifado_id': doc.get('almoxarifado_id'),
        'sub_almoxarifado_id': doc.get('sub_almoxarifado_id'),
        'setor_id': doc.get('setor_id')
    })

@main_bp.route('/api/usuarios/<string:user_id>', methods=['PUT'])
@require_admin_or_above
def api_usuarios_update(user_id):
    data = request.get_json(silent=True) or {}
    coll = extensions.mongo_db['usuarios']
    # Buscar alvo para verificar permissões
    try:
        target = coll.find_one({'_id': ObjectId(user_id)})
    except Exception:
        target = coll.find_one({'id': user_id})
    if not target:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    # Bloquear edição de super admin por outros usuários
    target_id_str = str(target.get('id') or target.get('_id'))
    current_id_str = str(getattr(current_user, 'get_id', lambda: None)())
    if (target.get('nivel_acesso') == 'super_admin') and (current_id_str != target_id_str):
        return jsonify({'error': 'Não é permitido editar o perfil do super administrador'}), 403
    # Se não for super admin, só pode editar o próprio perfil
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin' and (current_id_str != target_id_str):
        return jsonify({'error': 'Você só pode editar seu próprio perfil'}), 403
    update = {}
    if 'login' in data or 'username' in data:
        update['username'] = (data.get('login') or data.get('username') or '').strip()
    if 'nome' in data or 'nome_completo' in data:
        update['nome_completo'] = (data.get('nome') or data.get('nome_completo') or '').strip()
    if 'email' in data:
        update['email'] = (data.get('email') or '').strip()
    if 'nivel' in data or 'nivel_acesso' in data:
        update['nivel_acesso'] = (data.get('nivel') or data.get('nivel_acesso') or 'operador_setor').strip()
    if 'ativo' in data:
        update['ativo'] = bool(data.get('ativo'))
    for f in ['central_id', 'almoxarifado_id', 'sub_almoxarifado_id', 'setor_id', 'categoria_id']:
        if f in data:
            update[f] = data.get(f)
    # Senha opcional
    if 'senha' in data and data.get('senha'):
        try:
            from werkzeug.security import generate_password_hash
            update['password_hash'] = generate_password_hash((data.get('senha') or '').strip())
        except Exception:
            return jsonify({'error': 'Falha ao atualizar senha'}), 500
    # Remover campos sensíveis se não for super admin
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin':
        update.pop('nivel_acesso', None)
        update.pop('ativo', None)
        for f in ['central_id', 'almoxarifado_id', 'sub_almoxarifado_id', 'setor_id', 'categoria_id']:
            update.pop(f, None)
    update['updated_at'] = datetime.utcnow()
    try:
        res = coll.find_one_and_update({'_id': ObjectId(user_id)}, {'$set': update}, return_document=ReturnDocument.AFTER)
    except Exception:
        res = coll.find_one_and_update({'id': user_id}, {'$set': update}, return_document=ReturnDocument.AFTER)
    if not res:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'id': str(res.get('_id')) if res.get('_id') else res.get('id'), 'message': 'Usuário atualizado'})

@main_bp.route('/api/usuarios/<string:user_id>', methods=['DELETE'])
@require_admin_or_above
def api_usuarios_delete(user_id):
    coll = extensions.mongo_db['usuarios']
    # Impedir exclusão de super administrador
    try:
        doc = coll.find_one({'_id': ObjectId(user_id)})
    except Exception:
        doc = coll.find_one({'id': user_id})
    if not doc:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    # Apenas super admin pode excluir usuários
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin':
        return jsonify({'error': 'Apenas super administradores podem excluir usuários'}), 403
    if doc.get('nivel_acesso') == 'super_admin':
        return jsonify({'error': 'Não é permitido excluir o super administrador'}), 403
    try:
        res = coll.delete_one({'_id': ObjectId(user_id)})
    except Exception:
        res = coll.delete_one({'id': user_id})
    if res.deleted_count == 0:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'message': 'Usuário excluído com sucesso'})

@main_bp.route('/api/usuarios/<string:user_id>/toggle-status', methods=['POST'])
@require_admin_or_above
def api_usuarios_toggle_status(user_id):
    coll = extensions.mongo_db['usuarios']
    try:
        doc = coll.find_one({'_id': ObjectId(user_id)})
    except Exception:
        doc = coll.find_one({'id': user_id})
    if not doc:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    # Apenas super admin pode alterar status de usuários
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin':
        return jsonify({'error': 'Apenas super administradores podem alterar status de usuários'}), 403
    # Impedir desativação do super administrador
    if doc.get('nivel_acesso') == 'super_admin':
        return jsonify({'error': 'Não é permitido desativar o super administrador'}), 403
    novo_status = not bool(doc.get('ativo', True))
    # Atualizar com chave correta
    filtro = {'_id': doc.get('_id')} if doc.get('_id') else {'id': doc.get('id')}
    coll.update_one(filtro, {'$set': {'ativo': novo_status, 'updated_at': datetime.utcnow()}})
    return jsonify({'message': 'Status alterado com sucesso', 'ativo': novo_status})

@main_bp.route('/api/usuarios/<string:user_id>/reset-password', methods=['POST'])
@require_admin_or_above
def api_usuarios_reset_password(user_id):
    data = request.get_json(silent=True) or {}
    nova_senha = (data.get('nova_senha') or '').strip()
    if not nova_senha:
        return jsonify({'error': 'Nova senha é obrigatória'}), 400
    coll = extensions.mongo_db['usuarios']
    # Buscar alvo
    try:
        doc = coll.find_one({'_id': ObjectId(user_id)})
    except Exception:
        doc = coll.find_one({'id': user_id})
    if not doc:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    # Impedir alteração de senha do super admin por outros usuários
    target_id_str = str(doc.get('id') or doc.get('_id'))
    current_id_str = str(getattr(current_user, 'get_id', lambda: None)())
    if (doc.get('nivel_acesso') == 'super_admin') and (current_id_str != target_id_str):
        return jsonify({'error': 'Não é permitido alterar a senha do super administrador'}), 403
    # Se não for super admin, só pode alterar a própria senha
    if getattr(current_user, 'nivel_acesso', None) != 'super_admin' and (current_id_str != target_id_str):
        return jsonify({'error': 'Você só pode alterar sua própria senha'}), 403
    try:
        from werkzeug.security import generate_password_hash
        hashpwd = generate_password_hash(nova_senha)
    except Exception:
        return jsonify({'error': 'Falha ao gerar hash de senha'}), 500
    filtro = {'_id': doc.get('_id')} if doc.get('_id') else {'id': doc.get('id')}
    res = coll.update_one(filtro, {'$set': {'password_hash': hashpwd, 'updated_at': datetime.utcnow()}})
    if res.matched_count == 0:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'message': 'Senha resetada com sucesso!'})

@main_bp.route('/api/usuarios/<string:user_id>/categorias-especificas', methods=['GET'])
@require_admin_or_above
def api_usuarios_categorias_list(user_id):
    db = extensions.mongo_db
    ucoll = db['usuarios']
    try:
        doc = ucoll.find_one({'_id': ObjectId(user_id)})
    except Exception:
        doc = ucoll.find_one({'id': user_id})
    if not doc:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    ids = doc.get('categorias_especificas') or []
    # Resolver nomes
    categorias = []
    ccoll = db['categorias']
    for cid in ids:
        found = None
        try:
            if isinstance(cid, int):
                found = ccoll.find_one({'id': cid})
            elif isinstance(cid, str) and len(cid) == 24:
                found = ccoll.find_one({'_id': ObjectId(cid)})
            else:
                found = ccoll.find_one({'_id': cid})
        except Exception:
            found = ccoll.find_one({'_id': cid})
        if found:
            categorias.append({'id': str(found.get('_id')) if found.get('_id') else found.get('id'), 'nome': found.get('nome')})
    return jsonify({'categorias_especificas': categorias})

@main_bp.route('/api/usuarios/<string:user_id>/categorias-especificas', methods=['POST'])
@require_admin_or_above
def api_usuarios_categorias_add(user_id):
    data = request.get_json(silent=True) or {}
    cid = data.get('categoria_id')
    if cid is None:
        return jsonify({'error': 'categoria_id é obrigatório'}), 400
    db = extensions.mongo_db
    ucoll = db['usuarios']
    ccoll = db['categorias']
    # Validar categoria
    cat_doc = None
    try:
        if isinstance(cid, int):
            cat_doc = ccoll.find_one({'id': cid})
        elif isinstance(cid, str) and len(cid) == 24:
            cat_doc = ccoll.find_one({'_id': ObjectId(cid)})
        else:
            cat_doc = ccoll.find_one({'_id': cid})
    except Exception:
        cat_doc = ccoll.find_one({'_id': cid})
    if not cat_doc:
        return jsonify({'error': 'Categoria não encontrada'}), 404
    # Adicionar ao usuário (evitar duplicado)
    try:
        res = ucoll.update_one({'_id': ObjectId(user_id)}, {'$addToSet': {'categorias_especificas': str(cat_doc.get('_id'))}})
    except Exception:
        res = ucoll.update_one({'id': user_id}, {'$addToSet': {'categorias_especificas': str(cat_doc.get('_id'))}})
    if res.matched_count == 0:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'categoria': {'id': str(cat_doc.get('_id')), 'nome': cat_doc.get('nome')}})

@main_bp.route('/api/usuarios/<string:user_id>/categorias-especificas/<string:categoria_id>', methods=['DELETE'])
@require_admin_or_above
def api_usuarios_categorias_remove(user_id, categoria_id):
    db = extensions.mongo_db
    ucoll = db['usuarios']
    try:
        res = ucoll.update_one({'_id': ObjectId(user_id)}, {'$pull': {'categorias_especificas': categoria_id}})
    except Exception:
        res = ucoll.update_one({'id': user_id}, {'$pull': {'categorias_especificas': categoria_id}})
    if res.matched_count == 0:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'message': 'Categoria removida'})

# --- PRODUTOS (MongoDB) - criação e geração de código ---
@main_bp.route('/api/produtos', methods=['POST'])
@require_manager_or_above
def api_produtos_create():
    data = request.get_json(silent=True) or {}
    codigo = (data.get('codigo') or '').strip()
    nome = (data.get('nome') or '').strip()
    if not codigo or not nome or not data.get('central_id'):
        return jsonify({'error': 'Central, Código e Nome são obrigatórios'}), 400
    coll = extensions.mongo_db['produtos']
    if coll.find_one({'codigo': codigo}):
        return jsonify({'error': 'Código já existe'}), 400
    doc = {
        'central_id': data.get('central_id'),
        'codigo': codigo,
        'nome': nome,
        'descricao': (data.get('descricao') or '').strip() or None,
        'unidade_medida': (data.get('unidade_medida') or '').strip() or None,
        'ativo': bool(data.get('ativo', True)),
        'created_at': datetime.utcnow()
    }
    # Resolver categoria via categoria_id ou tratar 'categoria' como id se aplicável; caso contrário, manter texto
    categoria_id = data.get('categoria_id')
    if categoria_id is None:
        raw_categoria = data.get('categoria')
        if raw_categoria is not None and str(raw_categoria).strip() != '':
            categoria_id = raw_categoria
    if categoria_id is not None:
        try:
            categorias = extensions.mongo_db['categorias']
            categoria_resolvida = None
            if isinstance(categoria_id, int) or (isinstance(categoria_id, str) and categoria_id.isdigit()):
                categoria_resolvida = categorias.find_one({'id': int(categoria_id)})
                categoria_id = int(categoria_id)
            elif isinstance(categoria_id, str) and len(categoria_id) == 24:
                try:
                    categoria_resolvida = categorias.find_one({'_id': ObjectId(categoria_id)})
                except Exception:
                    categoria_resolvida = categorias.find_one({'_id': categoria_id})
            else:
                # fallback: tentar por _id string
                categoria_resolvida = categorias.find_one({'_id': categoria_id})
            if not categoria_resolvida:
                return jsonify({'error': 'Categoria informada não existe'}), 400
            # Persistir id resolvido normalizado (sequencial se existir, senão _id string)
            doc['categoria_id'] = categoria_resolvida.get('id') if categoria_resolvida.get('id') is not None else str(categoria_resolvida.get('_id'))
        except Exception:
            return jsonify({'error': 'Falha ao validar categoria_id'}), 400
    else:
        # Caso não haja categoria_id válido, aceitar categoria como texto livre opcional
        cat_text = (data.get('categoria') or '').strip()
        if cat_text:
            doc['categoria'] = cat_text
    res = coll.insert_one(doc)
    return jsonify({'id': str(res.inserted_id)})

@main_bp.route('/api/produtos/gerar-codigo', methods=['POST'])
@require_manager_or_above
def api_produtos_gerar_codigo():
    """Gera código curto e intuitivo: <central>-<categoria>-#### (sequencial por combinação)."""
    data = request.get_json(silent=True) or {}
    central_id = data.get('central_id')
    categoria_id = data.get('categoria') or data.get('categoria_id')
    if not central_id or not categoria_id:
        return jsonify({'success': False, 'message': 'central_id e categoria são obrigatórios'}), 400

    db = extensions.mongo_db

    # Resolver Central (usar id sequencial; se ausente, usar sufixo curto do ObjectId)
    central_doc = _find_central_by_param(central_id)
    if not central_doc:
        return jsonify({'success': False, 'message': 'Central não encontrada'}), 404
    if central_doc.get('id') is not None:
        central_part = str(central_doc.get('id'))
    else:
        c_oid = central_doc.get('_id')
        c_str = str(c_oid) if c_oid else str(central_id)
        central_part = c_str[-4:] if len(c_str) >= 4 else c_str

    # Resolver Categoria (priorizar campo "codigo"; senão, usar id sequencial ou sufixo curto do ObjectId)
    categorias_coll = db['categorias']
    cat_doc = None
    if isinstance(categoria_id, int) or (isinstance(categoria_id, str) and categoria_id.isdigit()):
        cat_doc = categorias_coll.find_one({'id': int(categoria_id)})
    elif isinstance(categoria_id, str) and len(categoria_id) == 24:
        try:
            cat_doc = categorias_coll.find_one({'_id': ObjectId(categoria_id)})
        except Exception:
            cat_doc = categorias_coll.find_one({'_id': categoria_id})
    else:
        cat_doc = categorias_coll.find_one({'_id': categoria_id}) or categorias_coll.find_one({'id': categoria_id})
    if not cat_doc:
        return jsonify({'success': False, 'message': 'Categoria não encontrada'}), 404
    cat_part = (cat_doc.get('codigo') or '').strip()
    if not cat_part:
        if cat_doc.get('id') is not None:
            cat_part = str(cat_doc.get('id'))
        else:
            c_str = str(cat_doc.get('_id'))
            cat_part = c_str[-4:] if len(c_str) >= 4 else c_str

    prefix = f"{central_part}-{cat_part}-"

    coll = db['produtos']
    seq = coll.count_documents({'codigo': {'$regex': f'^{prefix}'}}) + 1
    while True:
        codigo = f"{prefix}{seq:04d}"
        if not coll.find_one({'codigo': codigo}):
            break
        seq += 1

    return jsonify({'success': True, 'codigo': codigo})

# --- ALMOXARIFADOS (detalhe) ---
@main_bp.route('/api/almoxarifados/<string:almox_id>')
@require_any_level
def api_almoxarifado_detail(almox_id):
    db = extensions.mongo_db
    coll = db['almoxarifados']
    doc = None
    try:
        doc = coll.find_one({'_id': ObjectId(almox_id)})
    except Exception:
        # fallback id sequencial/alternativo
        if str(almox_id).isdigit():
            doc = coll.find_one({'id': int(almox_id)})
        else:
            doc = coll.find_one({'id': almox_id})
    if not doc:
        return jsonify({'error': 'Almoxarifado não encontrado'}), 404
    # Total de sub-almoxarifados
    subs = db['sub_almoxarifados']
    aid_key = doc.get('_id') if doc.get('_id') else doc.get('id')
    count = 0
    try:
        count = subs.count_documents({'almoxarifado_id': aid_key})
        if isinstance(aid_key, ObjectId):
            count = max(count, subs.count_documents({'almoxarifado_id': str(aid_key)}))
    except Exception:
        count = subs.count_documents({'almoxarifado_id': str(aid_key)})
    return jsonify({
        'id': str(doc.get('_id')) if doc.get('_id') else doc.get('id'),
        'nome': doc.get('nome'),
        'central_id': str(doc.get('central_id')) if doc.get('central_id') else None,
        'total_sub_almoxarifados': count
    })

# --- CENTRAIS ---
@main_bp.route('/api/centrais')
@require_any_level
def api_centrais_list():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    ativo_param = request.args.get('ativo')
    search = (request.args.get('search') or '').strip()

    filter_query = {}
    if ativo_param is not None and ativo_param != '':
        val = str(ativo_param).lower()
        if val in ('true', '1'):
            filter_query['ativo'] = True
        elif val in ('false', '0'):
            filter_query['ativo'] = False
    if search:
        filter_query['$or'] = [
            {'nome': {'$regex': search, '$options': 'i'}},
            {'descricao': {'$regex': search, '$options': 'i'}}
        ]

    coll = extensions.mongo_db['centrais']
    total = coll.count_documents(filter_query)
    skip = max(0, (page - 1) * per_page)
    cursor = coll.find(filter_query).sort('id', 1).skip(skip).limit(per_page)

    items = []
    for doc in cursor:
        items.append({
            'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
            'nome': doc.get('nome'),
            'descricao': doc.get('descricao'),
            'ativo': doc.get('ativo', True)
        })

    return jsonify({'items': items, 'pagination': {'page': page, 'per_page': per_page, 'total': total}})


def _find_central_by_param(id_param: str):
    coll = extensions.mongo_db['centrais']
    doc = None
    if str(id_param).isdigit():
        doc = coll.find_one({'id': int(id_param)})
    if doc is None:
        # tentar como ObjectId
        try:
            oid = ObjectId(str(id_param))
            doc = coll.find_one({'_id': oid})
        except Exception:
            doc = coll.find_one({'id': id_param})
    return doc


def _count_almoxarifados_vinculados(doc: dict, only_active=True) -> int:
    almox_coll = extensions.mongo_db['almoxarifados']
    conditions = []
    if isinstance(doc.get('id'), int):
        conditions.append({'central_id': doc.get('id')})
    # considerar ObjectId e string
    _oid = doc.get('_id')
    if _oid:
        conditions.append({'central_id': _oid})
        conditions.append({'central_id': str(_oid)})
    query = {'$or': conditions} if conditions else {}
    if only_active:
        query['ativo'] = True
    return almox_coll.count_documents(query)


@main_bp.route('/api/centrais/<string:id>')
@require_any_level
def api_centrais_get(id):
    doc = _find_central_by_param(id)
    if not doc:
        return jsonify({'error': 'Central não encontrada'}), 404
    total_almoxarifados = _count_almoxarifados_vinculados(doc, only_active=False)
    return jsonify({
        'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
        'nome': doc.get('nome'),
        'descricao': doc.get('descricao'),
        'ativo': doc.get('ativo', True),
        'total_almoxarifados': total_almoxarifados
    })


@main_bp.route('/api/centrais', methods=['POST'])
@require_admin_or_above
def api_centrais_create():
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    ativo = bool(data.get('ativo', True))
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400

    coll = extensions.mongo_db['centrais']
    # gerar id sequencial simples
    last = coll.find({'id': {'$exists': True, '$type': 'int'}}).sort('id', -1).limit(1)
    next_id = None
    try:
        last_doc = next(last)
        next_id = int(last_doc.get('id', 0)) + 1
    except StopIteration:
        next_id = 1
    except Exception:
        next_id = int(coll.count_documents({})) + 1

    doc = {
        'id': next_id,
        'nome': nome,
        'descricao': descricao,
        'ativo': ativo,
        'created_at': datetime.utcnow()
    }
    res = coll.insert_one(doc)
    created = coll.find_one({'_id': res.inserted_id})
    return jsonify({
        'id': created.get('id') if created.get('id') is not None else str(created.get('_id')),
        'nome': created.get('nome'),
        'descricao': created.get('descricao'),
        'ativo': created.get('ativo', True)
    }), 201


@main_bp.route('/api/centrais/<string:id>', methods=['PUT'])
@require_admin_or_above
def api_centrais_update(id):
    data = request.get_json(silent=True) or {}
    update = {}
    if 'nome' in data: update['nome'] = (data.get('nome') or '').strip()
    if 'descricao' in data: update['descricao'] = (data.get('descricao') or '').strip()
    if 'ativo' in data: update['ativo'] = bool(data.get('ativo'))

    coll = extensions.mongo_db['centrais']
    # Selecionar filtro por id sequencial ou _id
    filter_query = None
    if str(id).isdigit():
        filter_query = {'id': int(id)}
    else:
        try:
            filter_query = {'_id': ObjectId(str(id))}
        except Exception:
            filter_query = {'id': id}

    updated = coll.find_one_and_update(
        filter_query,
        {'$set': update},
        return_document=ReturnDocument.AFTER
    )
    if not updated:
        return jsonify({'error': 'Central não encontrada'}), 404
    return jsonify({
        'id': updated.get('id') if updated.get('id') is not None else str(updated.get('_id')),
        'nome': updated.get('nome'),
        'descricao': updated.get('descricao'),
        'ativo': updated.get('ativo', True)
    })


@main_bp.route('/api/centrais/<string:id>', methods=['DELETE'])
@require_admin_or_above
def api_centrais_delete(id):
    coll = extensions.mongo_db['centrais']
    doc = _find_central_by_param(id)
    if not doc:
        return jsonify({'error': 'Central não encontrada'}), 404

    # bloquear exclusão se houver almoxarifados ativos vinculados
    total_almox_ativos = _count_almoxarifados_vinculados(doc, only_active=True)
    if total_almox_ativos > 0:
        return jsonify({'error': 'Não é possível excluir: há almoxarifados ativos vinculados'}), 400

    # executar exclusão
    if str(id).isdigit():
        coll.delete_one({'id': int(id)})
    else:
        try:
            coll.delete_one({'_id': ObjectId(str(id))})
        except Exception:
            coll.delete_one({'id': id})
    return jsonify({'status': 'deleted'})


@main_bp.route('/api/almoxarifados')
@require_any_level
def api_almoxarifados():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    ativo = request.args.get('ativo')
    central_param = request.args.get('central_id')

    filter_query = {}
    if ativo is not None:
        val = str(ativo).lower()
        if val in ('true', '1'):
            filter_query['ativo'] = True
        elif val in ('false', '0'):
            filter_query['ativo'] = False

    # Optional filter by central_id supporting both numeric sequence and ObjectId hex
    if central_param:
        if str(central_param).isdigit():
            filter_query['central_id'] = int(central_param)
        elif isinstance(central_param, str) and len(central_param) == 24:
            # Legacy documents may store central_id as ObjectId hex string
            filter_query['central_id'] = central_param

    coll = extensions.mongo_db['almoxarifados']
    total = coll.count_documents(filter_query)
    skip = max(0, (page - 1) * per_page)
    cursor = coll.find(filter_query).sort('id', 1).skip(skip).limit(per_page)

    # Preload centrais for name lookup (both by sequence id and by _id)
    centrais_coll = extensions.mongo_db['centrais']
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    items = []
    for doc in cursor:
        # Determine central name and normalized central_id
        raw_cid = doc.get('central_id')
        central_doc = None
        normalized_central_id = None
        if isinstance(raw_cid, int):
            central_doc = centrais_by_seq.get(raw_cid)
            normalized_central_id = raw_cid
        elif isinstance(raw_cid, ObjectId):
            central_doc = centrais_by_oid.get(str(raw_cid))
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
        elif isinstance(raw_cid, str) and len(raw_cid) == 24:
            # Likely an ObjectId hex string
            central_doc = centrais_by_oid.get(raw_cid)
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

        items.append({
            # Prefer sequence id; fallback to Mongo _id as string
            'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
            'nome': doc.get('nome'),
            'descricao': doc.get('descricao'),
            'ativo': doc.get('ativo', True),
            'central_id': normalized_central_id if normalized_central_id is not None else (raw_cid if isinstance(raw_cid, int) else None),
            'central_nome': central_doc.get('nome') if central_doc else None
        })

    return jsonify({
        'items': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': total}
    })

@main_bp.route('/api/almoxarifados', methods=['POST'])
@require_admin_or_above
def api_almoxarifados_create():
    data = request.get_json(silent=True) or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    ativo = bool(data.get('ativo', True))
    central_id = data.get('central_id')
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400
    if central_id is None:
        return jsonify({'error': 'Central é obrigatória'}), 400

    centrais_coll = extensions.mongo_db['centrais']
    central_doc = None
    if isinstance(central_id, int) or (isinstance(central_id, str) and str(central_id).isdigit()):
        try:
            central_doc = centrais_coll.find_one({'id': int(central_id)})
        except Exception:
            central_doc = None
    elif isinstance(central_id, str) and len(central_id) == 24:
        try:
            central_doc = centrais_coll.find_one({'_id': ObjectId(str(central_id))})
        except Exception:
            central_doc = None
    if not central_doc:
        return jsonify({'error': 'Central não encontrada'}), 404

    coll = extensions.mongo_db['almoxarifados']
    # gerar id sequencial simples
    last = coll.find({'id': {'$exists': True, '$type': 'int'}}).sort('id', -1).limit(1)
    next_id = None
    try:
        last_doc = next(last)
        next_id = int(last_doc.get('id', 0)) + 1
    except StopIteration:
        next_id = 1
    except Exception:
        next_id = int(coll.count_documents({})) + 1

    normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else (int(central_id) if isinstance(central_id, str) and central_id.isdigit() else central_id)
    doc = {
        'id': next_id,
        'nome': nome,
        'descricao': descricao,
        'ativo': ativo,
        'central_id': normalized_central_id,
        'created_at': datetime.utcnow()
    }
    res = coll.insert_one(doc)
    created = coll.find_one({'_id': res.inserted_id})
    # Prepara dados de retorno com nome da central
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    raw_cid = created.get('central_id')
    central_doc_resp = None
    normalized_cid_resp = None
    if isinstance(raw_cid, int):
        central_doc_resp = centrais_by_seq.get(raw_cid)
        normalized_cid_resp = raw_cid
    elif isinstance(raw_cid, ObjectId):
        central_doc_resp = centrais_by_oid.get(str(raw_cid))
        normalized_cid_resp = central_doc_resp.get('id') if central_doc_resp and 'id' in central_doc_resp else None
    elif isinstance(raw_cid, str) and len(raw_cid) == 24:
        central_doc_resp = centrais_by_oid.get(raw_cid)
        normalized_cid_resp = central_doc_resp.get('id') if central_doc_resp and 'id' in central_doc_resp else None

    return jsonify({
        'id': created.get('id') if created.get('id') is not None else str(created.get('_id')),
        'nome': created.get('nome'),
        'descricao': created.get('descricao'),
        'ativo': created.get('ativo', True),
        'central_id': normalized_cid_resp if normalized_cid_resp is not None else (raw_cid if isinstance(raw_cid, int) else None),
        'central_nome': central_doc_resp.get('nome') if central_doc_resp else None
    }), 201

@main_bp.route('/api/almoxarifados/<string:id>', methods=['PUT'])
@require_admin_or_above
def api_almoxarifados_update(id):
    data = request.get_json(silent=True) or {}
    update = {}
    if 'nome' in data: update['nome'] = (data.get('nome') or '').strip()
    if 'descricao' in data: update['descricao'] = (data.get('descricao') or '').strip()
    if 'ativo' in data: update['ativo'] = bool(data.get('ativo'))
    if 'central_id' in data:
        cid = data.get('central_id')
        if isinstance(cid, int) or (isinstance(cid, str) and cid.isdigit()):
            update['central_id'] = int(cid)
        elif isinstance(cid, str) and len(cid) == 24:
            update['central_id'] = cid

    coll = extensions.mongo_db['almoxarifados']
    # Selecionar filtro por id sequencial ou _id
    filter_query = None
    if str(id).isdigit():
        filter_query = {'id': int(id)}
    else:
        try:
            filter_query = {'_id': ObjectId(str(id))}
        except Exception:
            filter_query = {'id': id}

    updated = coll.find_one_and_update(
        filter_query,
        {'$set': update},
        return_document=ReturnDocument.AFTER
    )
    if not updated:
        return jsonify({'error': 'Almoxarifado não encontrado'}), 404

    # Montar central info
    centrais_coll = extensions.mongo_db['centrais']
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    raw_cid = updated.get('central_id')
    central_doc = None
    normalized_central_id = None
    if isinstance(raw_cid, int):
        central_doc = centrais_by_seq.get(raw_cid)
        normalized_central_id = raw_cid
    elif isinstance(raw_cid, ObjectId):
        central_doc = centrais_by_oid.get(str(raw_cid))
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
    elif isinstance(raw_cid, str) and len(raw_cid) == 24:
        central_doc = centrais_by_oid.get(raw_cid)
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

    return jsonify({
        'id': updated.get('id') if updated.get('id') is not None else str(updated.get('_id')),
        'nome': updated.get('nome'),
        'descricao': updated.get('descricao'),
        'ativo': updated.get('ativo', True),
        'central_id': normalized_central_id if normalized_central_id is not None else (raw_cid if isinstance(raw_cid, int) else None),
        'central_nome': central_doc.get('nome') if central_doc else None
    })

@main_bp.route('/api/almoxarifados/<string:id>', methods=['DELETE'])
@require_admin_or_above
def api_almoxarifados_delete(id):
    # Bloquear exclusão se houver sub-almoxarifados vinculados
    subs_coll = extensions.mongo_db['sub_almoxarifados']
    conditions = []
    if str(id).isdigit():
        conditions.append({'almoxarifado_id': int(id)})
    else:
        try:
            oid = ObjectId(str(id))
            conditions.append({'almoxarifado_id': oid})
            conditions.append({'almoxarifado_id': str(oid)})
        except Exception:
            conditions.append({'almoxarifado_id': id})
    total_subs = subs_coll.count_documents({'$or': conditions}) if conditions else 0
    if total_subs > 0:
        return jsonify({'error': 'Não é possível excluir: há sub-almoxarifados vinculados'}), 400

    # Executar exclusão
    coll = extensions.mongo_db['almoxarifados']
    if str(id).isdigit():
        coll.delete_one({'id': int(id)})
    else:
        try:
            coll.delete_one({'_id': ObjectId(str(id))})
        except Exception:
            coll.delete_one({'id': id})
    return jsonify({'status': 'deleted'})

@main_bp.route('/api/sub-almoxarifados')
@require_any_level
def api_sub_almoxarifados():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    coll = extensions.mongo_db['sub_almoxarifados']
    total = coll.count_documents({})
    skip = max(0, (page - 1) * per_page)
    cursor = coll.find({}).sort('id', 1).skip(skip).limit(per_page)

    # Preload almoxarifados and centrais for name lookup
    almox_coll = extensions.mongo_db['almoxarifados']
    centrais_coll = extensions.mongo_db['centrais']
    almox_by_seq = {a.get('id'): a for a in almox_coll.find({}, {'id': 1, 'nome': 1, 'central_id': 1}) if 'id' in a}
    almox_by_oid = {str(a.get('_id')): a for a in almox_coll.find({}, {'_id': 1, 'nome': 1, 'central_id': 1})}
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    items = []
    for doc in cursor:
        raw_aid = doc.get('almoxarifado_id')
        almox_doc = None
        normalized_almox_id = None
        if isinstance(raw_aid, int):
            almox_doc = almox_by_seq.get(raw_aid)
            normalized_almox_id = raw_aid
        elif isinstance(raw_aid, ObjectId):
            almox_doc = almox_by_oid.get(str(raw_aid))
            normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None
        elif isinstance(raw_aid, str) and len(raw_aid) == 24:
            almox_doc = almox_by_oid.get(raw_aid)
            normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None

        # Determine central info via almoxarifado
        central_doc = None
        normalized_central_id = None
        raw_cid = almox_doc.get('central_id') if almox_doc else None
        if isinstance(raw_cid, int):
            central_doc = centrais_by_seq.get(raw_cid)
            normalized_central_id = raw_cid
        elif isinstance(raw_cid, ObjectId):
            central_doc = centrais_by_oid.get(str(raw_cid))
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
        elif isinstance(raw_cid, str) and len(raw_cid) == 24:
            central_doc = centrais_by_oid.get(raw_cid)
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

        # Normalizar IDs de saída preferindo id sequencial; fallback para _id como string ou valor bruto
        sid_out = doc.get('id') if doc.get('id') is not None else str(doc.get('_id'))
        if almox_doc:
            aid_out = almox_doc.get('id') if almox_doc.get('id') is not None else str(almox_doc.get('_id'))
        else:
            if isinstance(raw_aid, int):
                aid_out = raw_aid
            else:
                try:
                    aid_out = str(raw_aid) if raw_aid is not None else None
                except Exception:
                    aid_out = None
        if central_doc:
            cid_out = central_doc.get('id') if central_doc.get('id') is not None else str(central_doc.get('_id'))
        else:
            if isinstance(raw_cid, int):
                cid_out = raw_cid
            else:
                try:
                    cid_out = str(raw_cid) if raw_cid is not None else None
                except Exception:
                    cid_out = None

        items.append({
            'id': sid_out,
            'nome': doc.get('nome'),
            'descricao': doc.get('descricao'),
            'ativo': doc.get('ativo', True),
            'almoxarifado_id': aid_out,
            'almoxarifado_nome': almox_doc.get('nome') if almox_doc else None,
            'central_id': cid_out,
            'central_nome': central_doc.get('nome') if central_doc else None,
        })

    return jsonify({
        'items': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': total}
    })

@main_bp.route('/api/sub-almoxarifados/<id>')
@require_any_level
def api_sub_almoxarifado_get(id):
    coll = extensions.mongo_db['sub_almoxarifados']
    doc = None
    if str(id).isdigit():
        doc = coll.find_one({'id': int(id)})
    elif isinstance(id, str) and len(id) == 24:
        try:
            doc = coll.find_one({'_id': ObjectId(id)})
        except Exception:
            doc = None
    if not doc:
        return jsonify({'error': 'Sub-almoxarifado não encontrado'}), 404

    # Lookup almoxarifado and central info
    almox_coll = extensions.mongo_db['almoxarifados']
    centrais_coll = extensions.mongo_db['centrais']
    almox_by_seq = {a.get('id'): a for a in almox_coll.find({}, {'id': 1, 'nome': 1, 'central_id': 1}) if 'id' in a}
    almox_by_oid = {str(a.get('_id')): a for a in almox_coll.find({}, {'_id': 1, 'nome': 1, 'central_id': 1})}
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    raw_aid = doc.get('almoxarifado_id')
    almox_doc = None
    normalized_almox_id = None
    if isinstance(raw_aid, int):
        almox_doc = almox_by_seq.get(raw_aid)
        normalized_almox_id = raw_aid
    elif isinstance(raw_aid, ObjectId):
        almox_doc = almox_by_oid.get(str(raw_aid))
        normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None
    elif isinstance(raw_aid, str) and len(raw_aid) == 24:
        almox_doc = almox_by_oid.get(raw_aid)
        normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None

    central_doc = None
    normalized_central_id = None
    raw_cid = almox_doc.get('central_id') if almox_doc else None
    if isinstance(raw_cid, int):
        central_doc = centrais_by_seq.get(raw_cid)
        normalized_central_id = raw_cid
    elif isinstance(raw_cid, ObjectId):
        central_doc = centrais_by_oid.get(str(raw_cid))
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
    elif isinstance(raw_cid, str) and len(raw_cid) == 24:
        central_doc = centrais_by_oid.get(raw_cid)
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

    return jsonify({
        'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
        'nome': doc.get('nome'),
        'descricao': doc.get('descricao'),
        'ativo': doc.get('ativo', True),
        'almoxarifado_id': normalized_almox_id if normalized_almox_id is not None else (raw_aid if isinstance(raw_aid, int) else None),
        'almoxarifado_nome': almox_doc.get('nome') if almox_doc else None,
        'central_id': normalized_central_id if normalized_central_id is not None else (raw_cid if isinstance(raw_cid, int) else None),
        'central_nome': central_doc.get('nome') if central_doc else None,
    })

@main_bp.route('/api/sub-almoxarifados', methods=['POST'])
@require_any_level
def api_sub_almoxarifados_create():
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    almoxarifado_id = data.get('almoxarifado_id')
    descricao = (data.get('descricao') or '').strip()
    ativo = bool(data.get('ativo', True))
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400
    if almoxarifado_id is None:
        return jsonify({'error': 'Almoxarifado é obrigatório'}), 400

    coll = extensions.mongo_db['sub_almoxarifados']
    # calcular next_id sem usar cursor.count() ou índice direto
    last_cursor = coll.find({'id': {'$exists': True}}).sort('id', -1).limit(1)
    last_doc = next(last_cursor, None)
    next_id = (last_doc['id'] + 1) if (last_doc and isinstance(last_doc.get('id'), int)) else 1

    doc = {
        'id': next_id,
        'nome': nome,
        'descricao': descricao,
        'ativo': ativo,
        'almoxarifado_id': almoxarifado_id,
        'created_at': datetime.utcnow()
    }
    coll.insert_one(doc)
    return jsonify({'id': next_id})

@main_bp.route('/api/sub-almoxarifados/<id>', methods=['PUT'])
@require_any_level
def api_sub_almoxarifados_update(id):
    data = request.get_json() or {}
    update = {}
    for field in ('nome', 'descricao', 'ativo', 'almoxarifado_id'):
        if field in data:
            update[field] = data[field]
    coll = extensions.mongo_db['sub_almoxarifados']
    if str(id).isdigit():
        res = coll.update_one({'id': int(id)}, {'$set': update})
    else:
        try:
            res = coll.update_one({'_id': ObjectId(id)}, {'$set': update})
        except Exception:
            res = None
    if not res or res.matched_count == 0:
        return jsonify({'error': 'Sub-almoxarifado não encontrado'}), 404
    return jsonify({'status': 'updated'})

@main_bp.route('/api/sub-almoxarifados/<id>', methods=['DELETE'])
@require_any_level
def api_sub_almoxarifados_delete(id):
    coll = extensions.mongo_db['sub_almoxarifados']
    if str(id).isdigit():
        coll.delete_one({'id': int(id)})
    else:
        try:
            coll.delete_one({'_id': ObjectId(id)})
        except Exception:
            coll.delete_one({'id': id})
    return jsonify({'status': 'deleted'})


@main_bp.route('/api/setores')
@require_any_level
def api_setores():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    coll = extensions.mongo_db['setores']
    total = coll.count_documents({})
    skip = max(0, (page - 1) * per_page)
    cursor = coll.find({}).sort('id', 1).skip(skip).limit(per_page)

    # Preload sub-almoxarifados, almoxarifados e centrais
    sub_coll = extensions.mongo_db['sub_almoxarifados']
    almox_coll = extensions.mongo_db['almoxarifados']
    centrais_coll = extensions.mongo_db['centrais']
    sub_by_seq = {s.get('id'): s for s in sub_coll.find({}, {'id': 1, 'nome': 1, 'almoxarifado_id': 1}) if 'id' in s}
    sub_by_oid = {str(s.get('_id')): s for s in sub_coll.find({}, {'_id': 1, 'nome': 1, 'almoxarifado_id': 1})}
    almox_by_seq = {a.get('id'): a for a in almox_coll.find({}, {'id': 1, 'nome': 1, 'central_id': 1}) if 'id' in a}
    almox_by_oid = {str(a.get('_id')): a for a in almox_coll.find({}, {'_id': 1, 'nome': 1, 'central_id': 1})}
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    items = []
    for doc in cursor:
        raw_sid = doc.get('sub_almoxarifado_id')
        sub_doc = None
        normalized_sub_id = None
        if isinstance(raw_sid, int):
            sub_doc = sub_by_seq.get(raw_sid)
            normalized_sub_id = raw_sid
        elif isinstance(raw_sid, ObjectId):
            sub_doc = sub_by_oid.get(str(raw_sid))
            normalized_sub_id = sub_doc.get('id') if sub_doc and 'id' in sub_doc else None
        elif isinstance(raw_sid, str) and len(raw_sid) == 24:
            sub_doc = sub_by_oid.get(raw_sid)
            normalized_sub_id = sub_doc.get('id') if sub_doc and 'id' in sub_doc else None

        almox_doc = None
        normalized_almox_id = None
        raw_aid = sub_doc.get('almoxarifado_id') if sub_doc else None
        if isinstance(raw_aid, int):
            almox_doc = almox_by_seq.get(raw_aid)
            normalized_almox_id = raw_aid
        elif isinstance(raw_aid, ObjectId):
            almox_doc = almox_by_oid.get(str(raw_aid))
            normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None
        elif isinstance(raw_aid, str) and len(raw_aid) == 24:
            almox_doc = almox_by_oid.get(raw_aid)
            normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None

        central_doc = None
        normalized_central_id = None
        raw_cid = almox_doc.get('central_id') if almox_doc else None
        if isinstance(raw_cid, int):
            central_doc = centrais_by_seq.get(raw_cid)
            normalized_central_id = raw_cid
        elif isinstance(raw_cid, ObjectId):
            central_doc = centrais_by_oid.get(str(raw_cid))
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
        elif isinstance(raw_cid, str) and len(raw_cid) == 24:
            central_doc = centrais_by_oid.get(raw_cid)
            normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

        items.append({
            'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
            'nome': doc.get('nome'),
            'descricao': doc.get('descricao'),
            'ativo': doc.get('ativo', True),
            'sub_almoxarifado_id': normalized_sub_id if normalized_sub_id is not None else (raw_sid if isinstance(raw_sid, int) else None),
            'sub_almoxarifado_nome': sub_doc.get('nome') if sub_doc else None,
            'almoxarifado_id': normalized_almox_id if normalized_almox_id is not None else (raw_aid if isinstance(raw_aid, int) else None),
            'almoxarifado_nome': almox_doc.get('nome') if almox_doc else None,
            'central_id': normalized_central_id if normalized_central_id is not None else (raw_cid if isinstance(raw_cid, int) else None),
            'central_nome': central_doc.get('nome') if central_doc else None,
        })

    return jsonify({
        'items': items,
        'pagination': {'page': page, 'per_page': per_page, 'total': total}
    })

@main_bp.route('/api/setores/<id>')
@require_any_level
def api_setor_get(id):
    coll = extensions.mongo_db['setores']
    doc = None
    if str(id).isdigit():
        doc = coll.find_one({'id': int(id)})
    elif isinstance(id, str) and len(id) == 24:
        try:
            doc = coll.find_one({'_id': ObjectId(id)})
        except Exception:
            doc = None
    if not doc:
        return jsonify({'error': 'Setor não encontrado'}), 404

    sub_coll = extensions.mongo_db['sub_almoxarifados']
    almox_coll = extensions.mongo_db['almoxarifados']
    centrais_coll = extensions.mongo_db['centrais']
    sub_by_seq = {s.get('id'): s for s in sub_coll.find({}, {'id': 1, 'nome': 1, 'almoxarifado_id': 1}) if 'id' in s}
    sub_by_oid = {str(s.get('_id')): s for s in sub_coll.find({}, {'_id': 1, 'nome': 1, 'almoxarifado_id': 1})}
    almox_by_seq = {a.get('id'): a for a in almox_coll.find({}, {'id': 1, 'nome': 1, 'central_id': 1}) if 'id' in a}
    almox_by_oid = {str(a.get('_id')): a for a in almox_coll.find({}, {'_id': 1, 'nome': 1, 'central_id': 1})}
    centrais_by_seq = {c.get('id'): c for c in centrais_coll.find({}, {'id': 1, 'nome': 1}) if 'id' in c}
    centrais_by_oid = {str(c.get('_id')): c for c in centrais_coll.find({}, {'_id': 1, 'nome': 1})}

    raw_sid = doc.get('sub_almoxarifado_id')
    sub_doc = None
    normalized_sub_id = None
    if isinstance(raw_sid, int):
        sub_doc = sub_by_seq.get(raw_sid)
        normalized_sub_id = raw_sid
    elif isinstance(raw_sid, ObjectId):
        sub_doc = sub_by_oid.get(str(raw_sid))
        normalized_sub_id = sub_doc.get('id') if sub_doc and 'id' in sub_doc else None
    elif isinstance(raw_sid, str) and len(raw_sid) == 24:
        sub_doc = sub_by_oid.get(raw_sid)
        normalized_sub_id = sub_doc.get('id') if sub_doc and 'id' in sub_doc else None

    almox_doc = None
    normalized_almox_id = None
    raw_aid = sub_doc.get('almoxarifado_id') if sub_doc else None
    if isinstance(raw_aid, int):
        almox_doc = almox_by_seq.get(raw_aid)
        normalized_almox_id = raw_aid
    elif isinstance(raw_aid, ObjectId):
        almox_doc = almox_by_oid.get(str(raw_aid))
        normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None
    elif isinstance(raw_aid, str) and len(raw_aid) == 24:
        almox_doc = almox_by_oid.get(raw_aid)
        normalized_almox_id = almox_doc.get('id') if almox_doc and 'id' in almox_doc else None

    central_doc = None
    normalized_central_id = None
    raw_cid = almox_doc.get('central_id') if almox_doc else None
    if isinstance(raw_cid, int):
        central_doc = centrais_by_seq.get(raw_cid)
        normalized_central_id = raw_cid
    elif isinstance(raw_cid, ObjectId):
        central_doc = centrais_by_oid.get(str(raw_cid))
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None
    elif isinstance(raw_cid, str) and len(raw_cid) == 24:
        central_doc = centrais_by_oid.get(raw_cid)
        normalized_central_id = central_doc.get('id') if central_doc and 'id' in central_doc else None

    return jsonify({
        'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
        'nome': doc.get('nome'),
        'descricao': doc.get('descricao'),
        'ativo': doc.get('ativo', True),
        'sub_almoxarifado_id': normalized_sub_id if normalized_sub_id is not None else (raw_sid if isinstance(raw_sid, int) else None),
        'sub_almoxarifado_nome': sub_doc.get('nome') if sub_doc else None,
        'almoxarifado_id': normalized_almox_id if normalized_almox_id is not None else (raw_aid if isinstance(raw_aid, int) else None),
        'almoxarifado_nome': almox_doc.get('nome') if almox_doc else None,
        'central_id': normalized_central_id if normalized_central_id is not None else (raw_cid if isinstance(raw_cid, int) else None),
        'central_nome': central_doc.get('nome') if central_doc else None,
    })

@main_bp.route('/api/setores', methods=['POST'])
@require_any_level
def api_setores_create():
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    sub_almoxarifado_id = data.get('sub_almoxarifado_id')
    descricao = (data.get('descricao') or '').strip()
    ativo = bool(data.get('ativo', True))
    if not nome:
        return jsonify({'error': 'Nome é obrigatório'}), 400
    if sub_almoxarifado_id is None:
        return jsonify({'error': 'Sub-almoxarifado é obrigatório'}), 400

    coll = extensions.mongo_db['setores']
    # calcular next_id sem usar cursor.count() ou índice direto
    last_cursor = coll.find({'id': {'$exists': True}}).sort('id', -1).limit(1)
    last_doc = next(last_cursor, None)
    next_id = (last_doc['id'] + 1) if (last_doc and isinstance(last_doc.get('id'), int)) else 1

    doc = {
        'id': next_id,
        'nome': nome,
        'descricao': descricao,
        'ativo': ativo,
        'sub_almoxarifado_id': sub_almoxarifado_id,
        'created_at': datetime.utcnow()
    }
    coll.insert_one(doc)
    return jsonify({'id': next_id})

@main_bp.route('/api/setores/<id>', methods=['PUT'])
@require_any_level
def api_setores_update(id):
    data = request.get_json() or {}
    update = {}
    for field in ('nome', 'descricao', 'ativo', 'sub_almoxarifado_id'):
        if field in data:
            update[field] = data[field]
    coll = extensions.mongo_db['setores']
    if str(id).isdigit():
        res = coll.update_one({'id': int(id)}, {'$set': update})
    else:
        try:
            res = coll.update_one({'_id': ObjectId(id)}, {'$set': update})
        except Exception:
            res = None
    if not res or res.matched_count == 0:
        return jsonify({'error': 'Setor não encontrado'}), 404
    return jsonify({'status': 'updated'})

@main_bp.route('/api/setores/<id>', methods=['DELETE'])
@require_any_level
def api_setores_delete(id):
    coll = extensions.mongo_db['setores']
    if str(id).isdigit():
        coll.delete_one({'id': int(id)})
    else:
        try:
            coll.delete_one({'_id': ObjectId(id)})
        except Exception:
            coll.delete_one({'id': id})
    return jsonify({'status': 'deleted'})

@main_bp.route('/api/produtos')
@require_any_level
def api_produtos():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = (request.args.get('search') or '').strip()
    categoria_id = request.args.get('categoria_id')
    ativo_param = request.args.get('ativo')

    # Montar filtro
    filter_query = {}
    if ativo_param is not None and ativo_param != '':
        val = str(ativo_param).lower()
        if val in ('true', '1'): filter_query['ativo'] = True
        elif val in ('false', '0'): filter_query['ativo'] = False
    if categoria_id:
        # aceitar id numérico legado ou ObjectId string
        if str(categoria_id).isdigit():
            filter_query['categoria_id'] = int(categoria_id)
        elif isinstance(categoria_id, str) and len(categoria_id) == 24:
            filter_query['categoria_id'] = categoria_id
        else:
            filter_query['categoria_id'] = categoria_id
    if search:
        # buscar por nome/codigo/descricao
        filter_query['$or'] = [
            {'nome': {'$regex': search, '$options': 'i'}},
            {'codigo': {'$regex': search, '$options': 'i'}},
            {'descricao': {'$regex': search, '$options': 'i'}}
        ]

    coll = extensions.mongo_db['produtos']
    total = coll.count_documents(filter_query)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    skip = max(0, (page - 1) * per_page)

    cursor = coll.find(filter_query).sort('created_at', -1).skip(skip).limit(per_page)

    # Opcional: carregar categorias para mostrar nome/cor
    categorias_coll = extensions.mongo_db['categorias']
    categorias_by_seq = {c.get('id'): c for c in categorias_coll.find({}, {'id': 1, 'nome': 1, 'codigo': 1, 'cor': 1}) if 'id' in c}
    categorias_by_oid = {str(c.get('_id')): c for c in categorias_coll.find({}, {'_id': 1, 'nome': 1, 'codigo': 1, 'cor': 1})}

    items = []
    for doc in cursor:
        # Normalizar id para string quando não existir id sequencial
        pid = doc.get('id') if doc.get('id') is not None else str(doc.get('_id'))
        cat_raw = doc.get('categoria_id')
        cat_doc = None
        if isinstance(cat_raw, int):
            cat_doc = categorias_by_seq.get(cat_raw)
        elif isinstance(cat_raw, str):
            cat_doc = categorias_by_oid.get(cat_raw)
        # Montar objeto categoria esperado pelo template
        categoria_produto = None
        if cat_doc:
            categoria_produto = {
                'id': cat_doc.get('id') if cat_doc.get('id') is not None else str(cat_doc.get('_id')),
                'nome': cat_doc.get('nome'),
                'codigo': cat_doc.get('codigo'),
                'cor': cat_doc.get('cor') or '#6c757d'
            }
        items.append({
            'id': pid,
            'codigo': doc.get('codigo'),
            'nome': doc.get('nome'),
            'descricao': doc.get('descricao'),
            'unidade_medida': doc.get('unidade_medida'),
            'ativo': bool(doc.get('ativo', True)),
            'categoria_produto': categoria_produto
        })

    return jsonify({
        'items': items,
        'page': page,
        'pages': pages,
        'per_page': per_page,
        'total': total
    })

@main_bp.route('/api/produtos/<string:produto_id>')
@require_any_level
def api_produto_detalhe(produto_id):
    """Detalhes reais do produto a partir do MongoDB (compatível com templates)."""
    # Montar consulta por id sequencial ou ObjectId
    query = None
    if str(produto_id).isdigit():
        query = {'id': int(produto_id)}
    elif isinstance(produto_id, str) and len(produto_id) == 24:
        try:
            query = {'_id': ObjectId(produto_id)}
        except Exception:
            query = {'_id': produto_id}
    else:
        query = {'id': produto_id}

    doc = extensions.mongo_db['produtos'].find_one(query)
    if not doc:
        return jsonify({'error': 'Produto não encontrado'}), 404

    # Resolver categoria por nome (se existir coleção categorias)
    categoria_nome = None
    raw_cat = doc.get('categoria_id')
    try:
        categorias = extensions.mongo_db['categorias']
        if isinstance(raw_cat, int):
            cat = categorias.find_one({'id': raw_cat})
        elif isinstance(raw_cat, ObjectId):
            cat = categorias.find_one({'_id': raw_cat})
        elif isinstance(raw_cat, str) and len(raw_cat) == 24:
            cat = categorias.find_one({'_id': ObjectId(raw_cat)})
        else:
            cat = None
        if cat:
            categoria_nome = cat.get('nome')
    except Exception:
        categoria_nome = None

    return jsonify({
        'id': doc.get('id') if doc.get('id') is not None else str(doc.get('_id')),
        'nome': doc.get('nome'),
        'codigo': doc.get('codigo'),
        'descricao': doc.get('descricao'),
        'unidade_medida': doc.get('unidade_medida'),
        'ativo': bool(doc.get('ativo', True)),
        # Normaliza central_id para uso no frontend (int ou string de ObjectId)
        'central_id': (
            (lambda v: (
                int(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
                else (str(v) if v is not None else None)
            ))(doc.get('central_id'))
        ),
        # Campo simples esperado pelo modal de edição (texto)
        'categoria': categoria_nome
    })

@main_bp.route('/api/produtos/<string:produto_id>', methods=['PUT'])
@require_any_level
def api_produto_update(produto_id):
    """Atualiza campos básicos do produto. Mantém compatibilidade com modal de edição."""
    data = request.get_json(silent=True) or {}
    update_fields = {}

    if 'nome' in data:
        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'error': 'Nome é obrigatório'}), 400
        update_fields['nome'] = nome
    if 'codigo' in data:
        codigo = (data.get('codigo') or '').strip()
        if not codigo:
            return jsonify({'error': 'Código é obrigatório'}), 400
        update_fields['codigo'] = codigo
    if 'descricao' in data:
        update_fields['descricao'] = (data.get('descricao') or '').strip() or None
    if 'unidade_medida' in data:
        update_fields['unidade_medida'] = (data.get('unidade_medida') or '').strip() or None
    if 'ativo' in data:
        update_fields['ativo'] = bool(data.get('ativo'))
    # Campo "categoria" é texto livre no modal; opcionalmente armazenar
    if 'categoria' in data:
        update_fields['categoria'] = (data.get('categoria') or '').strip() or None
    # Novo: aceitar mudança de categoria_id com validação
    if 'categoria_id' in data:
        categoria_id = data.get('categoria_id')
        try:
            categorias = extensions.mongo_db['categorias']
            categoria_resolvida = None
            if isinstance(categoria_id, int) or (isinstance(categoria_id, str) and categoria_id.isdigit()):
                categoria_resolvida = categorias.find_one({'id': int(categoria_id)})
                categoria_id = int(categoria_id)
            elif isinstance(categoria_id, str) and len(categoria_id) == 24:
                try:
                    categoria_resolvida = categorias.find_one({'_id': ObjectId(categoria_id)})
                except Exception:
                    categoria_resolvida = categorias.find_one({'_id': categoria_id})
            else:
                categoria_resolvida = categorias.find_one({'_id': categoria_id})
            if not categoria_resolvida:
                return jsonify({'error': 'Categoria informada não existe'}), 400
            # Persistir id resolvido
            update_fields['categoria_id'] = categoria_resolvida.get('id') if categoria_resolvida.get('id') is not None else str(categoria_resolvida.get('_id'))
        except Exception:
            return jsonify({'error': 'Falha ao validar categoria_id'}), 400

    update_fields['updated_at'] = datetime.utcnow()

    # Query normalizada
    if str(produto_id).isdigit():
        query = {'id': int(produto_id)}
    elif isinstance(produto_id, str) and len(produto_id) == 24:
        try:
            query = {'_id': ObjectId(produto_id)}
        except Exception:
            query = {'_id': produto_id}
    else:
        query = {'id': produto_id}

    res = extensions.mongo_db['produtos'].find_one_and_update(
        query,
        {'$set': update_fields},
        return_document=ReturnDocument.AFTER
    )
    if not res:
        return jsonify({'error': 'Produto não encontrado'}), 404

    # Resolver categoria por nome novamente
    categoria_nome = None
    raw_cat = res.get('categoria_id')
    try:
        categorias = extensions.mongo_db['categorias']
        if isinstance(raw_cat, int):
            cat = categorias.find_one({'id': raw_cat})
        elif isinstance(raw_cat, ObjectId):
            cat = categorias.find_one({'_id': raw_cat})
        elif isinstance(raw_cat, str) and len(raw_cat) == 24:
            cat = categorias.find_one({'_id': ObjectId(raw_cat)})
        else:
            cat = None
        if cat:
            categoria_nome = cat.get('nome')
    except Exception:
        categoria_nome = None

    return jsonify({
        'id': res.get('id') if res.get('id') is not None else str(res.get('_id')),
        'nome': res.get('nome'),
        'codigo': res.get('codigo'),
        'descricao': res.get('descricao'),
        'unidade_medida': res.get('unidade_medida'),
        'ativo': bool(res.get('ativo', True)),
        'categoria': categoria_nome
    })

@main_bp.route('/api/produtos/<string:produto_id>', methods=['DELETE'])
@require_any_level
def api_produto_delete(produto_id):
    """Inativa (soft delete) o produto para compatibilidade com o frontend."""
    # Query normalizada
    if str(produto_id).isdigit():
        query = {'id': int(produto_id)}
    elif isinstance(produto_id, str) and len(produto_id) == 24:
        try:
            query = {'_id': ObjectId(produto_id)}
        except Exception:
            query = {'_id': produto_id}
    else:
        query = {'id': produto_id}

    res = extensions.mongo_db['produtos'].find_one_and_update(
        query,
        {'$set': {'ativo': False, 'updated_at': datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )
    if not res:
        return jsonify({'error': 'Produto não encontrado'}), 404
    return jsonify({'success': True})

@main_bp.route('/api/produtos/<string:produto_id>/estoque')
@require_any_level
def api_produto_estoque(produto_id):
    """Retorna estrutura mínima de estoque compatível com templates.
    Tenta computar a partir da coleção 'estoques' quando possível."""
    estoques = []
    total_qtd = 0.0
    total_disp = 0.0
    try:
        coll = extensions.mongo_db['estoques']
        # Montar filtros possíveis para produto_id
        pid_candidates = []
        if str(produto_id).isdigit():
            pid_candidates.append(int(produto_id))
        pid_candidates.append(produto_id)
        try:
            pid_candidates.append(ObjectId(produto_id))
        except Exception:
            pass
        cursor = coll.find({'produto_id': {'$in': pid_candidates}})
        for s in cursor:
            quantidade = float(s.get('quantidade', s.get('quantidade_atual', 0)) or 0)
            disponivel = float(s.get('quantidade_disponivel', quantidade) or 0)
            total_qtd += quantidade
            total_disp += disponivel
            tipo = s.get('tipo') or s.get('local_tipo') or 'almoxarifado'
            nome_local = s.get('nome_local') or s.get('local_nome') or 'Local'
            local_id = s.get('local_id') or s.get('almoxarifado_id') or s.get('sub_almoxarifado_id') or s.get('setor_id')
            estoques.append({
                'tipo': tipo,
                'nome_local': nome_local,
                'quantidade': quantidade,
                'quantidade_disponivel': disponivel,
                'data_atualizacao': s.get('updated_at') or s.get('data_atualizacao'),
                'local_id': local_id
            })
    except Exception:
        # Se não houver coleção ou ocorrer erro, devolve estrutura vazia
        pass

    return jsonify({
        'estoques': estoques,
        'resumo': {
            'total_quantidade': total_qtd,
            'total_disponivel': total_disp
        }
    })

@main_bp.route('/api/produtos/<string:produto_id>/lotes')
@require_any_level
def api_produto_lotes(produto_id):
    """Placeholder compatível com templates: retorna lista de lotes."""
    items = []
    try:
        coll = extensions.mongo_db['lotes']
        pid_candidates = []
        if str(produto_id).isdigit():
            pid_candidates.append(int(produto_id))
        pid_candidates.append(produto_id)
        try:
            pid_candidates.append(ObjectId(produto_id))
        except Exception:
            pass
        for l in coll.find({'produto_id': {'$in': pid_candidates}}).limit(50):
            items.append({
                'numero_lote': l.get('lote') or l.get('numero_lote'),
                'quantidade_atual': l.get('quantidade_atual', 0),
                'data_fabricacao': l.get('data_fabricacao'),
                'data_vencimento': l.get('data_vencimento'),
                'observacoes': l.get('observacoes')
            })
    except Exception:
        pass
    return jsonify({'items': items})

@main_bp.route('/api/produtos/<string:produto_id>/movimentacoes')
@require_any_level
def api_produto_movimentacoes(produto_id):
    """Placeholder compatível com templates: retorna movimentações paginadas."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', request.args.get('per_page', 20)))
    items = []
    total = 0
    try:
        coll = extensions.mongo_db['movimentacoes']
        pid_candidates = []
        if str(produto_id).isdigit():
            pid_candidates.append(int(produto_id))
        pid_candidates.append(produto_id)
        try:
            pid_candidates.append(ObjectId(produto_id))
        except Exception:
            pass
        total = coll.count_documents({'produto_id': {'$in': pid_candidates}})
        skip = max(0, (page - 1) * per_page)
        for m in coll.find({'produto_id': {'$in': pid_candidates}}).sort('data_movimentacao', -1).skip(skip).limit(per_page):
            items.append({
                'data_movimentacao': m.get('data_movimentacao'),
                'tipo_movimentacao': m.get('tipo') or m.get('tipo_movimentacao'),
                'quantidade': m.get('quantidade'),
                'observacoes': m.get('observacoes')
            })
    except Exception:
        pass
    return jsonify({'items': items, 'pagination': {'page': page, 'per_page': per_page, 'total': total}})

@main_bp.route('/api/estoque/hierarquia')
@require_any_level
def api_estoque_hierarquia():
    """Agrega o estoque por hierarquia a partir da coleção 'estoques'.
    Retorna uma lista de itens com os campos esperados pelo template estoque.html.
    """
    items = []

    def _find_by_id(coll_name: str, value):
        """Resolve documento por id sequencial ou ObjectId string."""
        coll = extensions.mongo_db[coll_name]
        doc = None
        try:
            # tentar id sequencial
            if str(value).isdigit():
                doc = coll.find_one({'id': int(value)})
        except Exception:
            doc = None
        if not doc:
            # tentar ObjectId
            try:
                doc = coll.find_one({'_id': ObjectId(str(value))})
            except Exception:
                doc = None
        if not doc and isinstance(value, str):
            # tentar id/string direta
            doc = coll.find_one({'id': value}) or coll.find_one({'_id': value})
        return doc

    prod_cache = {}
    local_cache = {
        'centrais': {},
        'almoxarifados': {},
        'sub_almoxarifados': {},
        'setores': {}
    }

    try:
        coll = extensions.mongo_db['estoques']
        cursor = coll.find({})
        for s in cursor:
            # Produto
            raw_pid = s.get('produto_id')
            pdoc = prod_cache.get(str(raw_pid))
            if pdoc is None:
                try:
                    pdoc = _find_by_id('produtos', raw_pid)
                except Exception:
                    pdoc = None
                prod_cache[str(raw_pid)] = pdoc
            produto_nome = (pdoc or {}).get('nome') or '-'
            produto_codigo = (pdoc or {}).get('codigo') or '-'
            produto_unidade = (pdoc or {}).get('unidade_medida')
            produto_id_out = (pdoc or {}).get('id')
            if produto_id_out is None and pdoc is not None:
                produto_id_out = str(pdoc.get('_id'))
            if produto_id_out is None:
                produto_id_out = raw_pid

            # Local e tipo
            tipo = None
            local_id = None
            coll_name = None
            if s.get('setor_id') is not None:
                tipo = 'setor'
                local_id = s.get('setor_id')
                coll_name = 'setores'
            elif s.get('sub_almoxarifado_id') is not None:
                tipo = 'subalmoxarifado'
                local_id = s.get('sub_almoxarifado_id')
                coll_name = 'sub_almoxarifados'
            elif s.get('almoxarifado_id') is not None:
                tipo = 'almoxarifado'
                local_id = s.get('almoxarifado_id')
                coll_name = 'almoxarifados'
            elif s.get('central_id') is not None:
                tipo = 'central'
                local_id = s.get('central_id')
                coll_name = 'centrais'
            else:
                tipo = s.get('local_tipo') or 'almoxarifado'
                local_id = s.get('local_id')

            local_nome = s.get('local_nome') or s.get('nome_local') or 'Local'
            if coll_name and local_id is not None:
                cache = local_cache[coll_name]
                ldoc = cache.get(str(local_id))
                if ldoc is None:
                    try:
                        ldoc = _find_by_id(coll_name, local_id)
                    except Exception:
                        ldoc = None
                    cache[str(local_id)] = ldoc
                if ldoc is not None:
                    local_nome = ldoc.get('nome') or ldoc.get('descricao') or local_nome
                    # normalizar id
                    lid_out = ldoc.get('id')
                    if lid_out is None:
                        lid_out = str(ldoc.get('_id'))
                    local_id = lid_out

            quantidade = float(s.get('quantidade', s.get('quantidade_atual', 0)) or 0)
            reservada = float(s.get('quantidade_reservada', 0) or 0)
            disponivel = float(s.get('quantidade_disponivel', quantidade - reservada) or 0)
            inicial = float(s.get('quantidade_inicial', quantidade) or 0)

            items.append({
                'produto_id': produto_id_out,
                'produto_nome': produto_nome,
                'produto_codigo': produto_codigo,
                'unidade_medida': produto_unidade,
                'local_tipo': tipo,
                'local_id': local_id,
                'local_nome': local_nome,
                'quantidade': quantidade,
                'quantidade_disponivel': disponivel,
                'quantidade_inicial': inicial,
                'data_atualizacao': s.get('updated_at') or s.get('data_atualizacao')
            })
    except Exception:
        # Em caso de erro, devolve lista vazia para não quebrar a página
        pass

    return jsonify(items)

@main_bp.route('/api/hierarquia/locais')
@require_any_level
def api_hierarquia_locais():
    """Lista todos os locais (centrais, almoxarifados, sub-almoxarifados e setores)
    com os campos {id, nome, tipo} usados pelo filtro da UI.
    """
    locais = []

    def _collect(coll_name: str, tipo: str):
        try:
            coll = extensions.mongo_db[coll_name]
            for doc in coll.find({}):
                if doc.get('ativo', True) is False:
                    continue
                lid = doc.get('id')
                if lid is None:
                    lid = str(doc.get('_id'))
                nome = doc.get('nome') or doc.get('descricao') or doc.get('name') or 'Sem nome'
                locais.append({'id': lid, 'nome': nome, 'tipo': tipo})
        except Exception:
            pass

    _collect('centrais', 'central')
    _collect('almoxarifados', 'almoxarifado')
    _collect('sub_almoxarifados', 'subalmoxarifado')
    _collect('setores', 'setor')

    return jsonify(locais)

@main_bp.route('/api/dashboard/stats-general')
@require_any_level
def api_dashboard_stats_general():
    return jsonify({
        'almoxarifados': 0,
        'sub_almoxarifados': 0,
        'setores': 0,
        'produtos': 0
    })

@main_bp.route('/api/dashboard/estoque-baixo')
@require_any_level
def api_dashboard_estoque_baixo():
    return jsonify({'items': []})

@main_bp.route('/api/dashboard/movimentacoes-recentes')
@require_any_level
def api_dashboard_movimentacoes_recentes():
    return jsonify({'items': []})

@main_bp.route('/api/movimentacoes')
@require_any_level
def api_movimentacoes():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    filtros = {
        'tipo': (request.args.get('tipo') or '').strip().lower(),
        'produto': (request.args.get('produto') or '').strip(),
        'data_inicio': (request.args.get('data_inicio') or '').strip(),
        'data_fim': (request.args.get('data_fim') or '').strip()
    }

    coll = extensions.mongo_db['movimentacoes']

    # Montar filtro de consulta
    query = {}

    # Filtro por tipo
    if filtros['tipo']:
        # aceitar tanto campo 'tipo' quanto 'tipo_movimentacao'
        query['$or'] = [
            {'tipo': filtros['tipo']},
            {'tipo_movimentacao': filtros['tipo']}
        ]

    # Filtro por produto: pode ser nome/código (texto) ou id
    if filtros['produto']:
        produto_text = filtros['produto']
        pid_candidates = []
        if produto_text.isdigit():
            pid_candidates.append(int(produto_text))
        # ObjectId
        try:
            pid_candidates.append(ObjectId(produto_text))
        except Exception:
            pass
        # String direta
        pid_candidates.append(produto_text)

        # Montar $or considerando produto_id e texto em nome/código
        prod_match = [{
            'produto_id': {'$in': pid_candidates}
        }]
        # Se produto_text não for id claro, buscar por nome/código em produtos
        try:
            produtos_coll = extensions.mongo_db['produtos']
            prods = list(produtos_coll.find({
                '$or': [
                    {'nome': {'$regex': produto_text, '$options': 'i'}},
                    {'codigo': {'$regex': produto_text, '$options': 'i'}}
                ]
            }, {'id': 1, '_id': 1}))
            if prods:
                ids = []
                for p in prods:
                    if p.get('id') is not None:
                        ids.append(p['id'])
                    if p.get('_id') is not None:
                        ids.append(str(p['_id']))
                        ids.append(p['_id'])
                if ids:
                    prod_match.append({'produto_id': {'$in': ids}})
        except Exception:
            pass

        if '$or' in query:
            query['$and'] = [{'$or': query['$or']}, {'$or': prod_match}]
            del query['$or']
        else:
            query['$or'] = prod_match

    # Filtro por data
    date_range = {}
    def parse_date_str(s):
        try:
            # aceitar formatos ISO e dd/mm/yyyy
            if '-' in s:
                return datetime.fromisoformat(s)
            else:
                # dd/mm/yyyy
                d, m, y = s.split('/')
                return datetime(int(y), int(m), int(d))
        except Exception:
            return None
    if filtros['data_inicio']:
        di = parse_date_str(filtros['data_inicio'])
        if di:
            date_range['$gte'] = di
    if filtros['data_fim']:
        df = parse_date_str(filtros['data_fim'])
        if df:
            # incluir final do dia
            date_range['$lte'] = df
    if date_range:
        # aceitar campos data_movimentacao e created_at
        if '$and' in query:
            query['$and'].append({'$or': [
                {'data_movimentacao': date_range},
                {'created_at': date_range}
            ]})
        elif '$or' in query:
            query = {'$and': [
                {'$or': query['$or']},
                {'$or': [
                    {'data_movimentacao': date_range},
                    {'created_at': date_range}
                ]}
            ]}
        else:
            query['$or'] = [
                {'data_movimentacao': date_range},
                {'created_at': date_range}
            ]

    total = coll.count_documents(query or {})
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    skip = max(0, (page - 1) * per_page)

    cursor = coll.find(query or {}).sort('data_movimentacao', -1).skip(skip).limit(per_page)

    # caches para resolução
    prod_cache = {}

    def resolve_produto(pid):
        key = str(pid)
        if key in prod_cache:
            return prod_cache[key]
        doc = None
        try:
            coll_prod = extensions.mongo_db['produtos']
            if str(pid).isdigit():
                doc = coll_prod.find_one({'id': int(pid)})
            if not doc:
                try:
                    doc = coll_prod.find_one({'_id': ObjectId(str(pid))})
                except Exception:
                    pass
            if not doc and isinstance(pid, str):
                doc = coll_prod.find_one({'id': pid}) or coll_prod.find_one({'_id': pid})
        except Exception:
            doc = None
        prod_cache[key] = doc
        return doc

    def resolve_local(tipo, lid):
        if not tipo:
            return None
        coll_name = None
        if str(tipo).lower() in ('setor', 'setores'):
            coll_name = 'setores'
        elif str(tipo).lower() in ('subalmoxarifado', 'sub_almoxarifado', 'sub_almoxarifados'):
            coll_name = 'sub_almoxarifados'
        elif str(tipo).lower() in ('almoxarifado', 'almoxarifados'):
            coll_name = 'almoxarifados'
        elif str(tipo).lower() in ('central', 'centrais'):
            coll_name = 'centrais'
        if not coll_name:
            return None
        try:
            return _find_by_id(coll_name, lid)
        except Exception:
            return None

    items = []
    for m in cursor:
        # Normalizar tipo
        tipo_mov = m.get('tipo') or m.get('tipo_movimentacao')
        # Produto
        pdoc = resolve_produto(m.get('produto_id'))
        produto_nome = (pdoc or {}).get('nome') or m.get('produto_nome') or '-'
        produto_codigo = (pdoc or {}).get('codigo') or m.get('produto_codigo') or '-'
        produto_unidade = (pdoc or {}).get('unidade_medida') or m.get('produto_unidade') or ''

        # Origem/destino
        origem_tipo = m.get('origem_tipo') or m.get('local_tipo')
        origem_id = m.get('origem_id') or m.get('local_id')
        destino_tipo = m.get('destino_tipo')
        destino_id = m.get('destino_id')

        origem_doc = resolve_local(origem_tipo, origem_id)
        destino_doc = resolve_local(destino_tipo, destino_id)
        origem_nome = (origem_doc or {}).get('nome') or m.get('origem_nome') or m.get('local_nome')
        destino_nome = (destino_doc or {}).get('nome') or m.get('destino_nome')

        # Usuário
        usuario_resp = m.get('usuario_responsavel') or m.get('usuario') or m.get('usuario_nome') or '-'

        # Data
        data_mov = m.get('data_movimentacao') or m.get('created_at') or m.get('updated_at')
        if isinstance(data_mov, str):
            try:
                data_mov = datetime.fromisoformat(data_mov)
            except Exception:
                data_mov = datetime.utcnow()

        items.append({
            'data_movimentacao': data_mov,
            'tipo_movimentacao': tipo_mov,
            'produto_codigo': produto_codigo,
            'produto_nome': produto_nome,
            'produto_unidade': produto_unidade,
            'quantidade': m.get('quantidade') or m.get('quantidade_movimentada') or 0,
            'origem_nome': origem_nome,
            'destino_nome': destino_nome,
            'usuario_responsavel': usuario_resp,
            'motivo': m.get('motivo') or m.get('observacoes')
        })

    # Construir paginação compatível com template
    total_pages = max(1, (total + per_page - 1) // per_page)
    pagination = {
        'current_page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total': total
    }

    return jsonify({'items': items, 'pagination': pagination})

@main_bp.route('/api/produtos/<string:produto_id>/almoxarifados')
@require_any_level
def api_produto_almoxarifados(produto_id):
    """Lista almoxarifados relevantes para o produto, incluindo indicação de estoque atual.
    Consolida informações da coleção 'estoques' e da coleção 'almoxarifados'.
    """
    try:
        db = extensions.mongo_db
        almox_coll = db['almoxarifados']
        estoque_coll = db['estoques']

        # Normalizar candidatos de produto_id para consulta
        pid_candidates = []
        if str(produto_id).isdigit():
            pid_candidates.append(int(produto_id))
        pid_candidates.append(produto_id)
        try:
            pid_candidates.append(ObjectId(produto_id))
        except Exception:
            pass

        # Mapear estoques por almoxarifado_id
        estoque_por_almox = {}
        for s in estoque_coll.find({'produto_id': {'$in': pid_candidates}}):
            # detectar almoxarifado_id do documento de estoque
            aid = s.get('almoxarifado_id') or s.get('local_id')
            if aid is None:
                continue
            # normalizar chave para string
            key = str(aid)
            quantidade = float(s.get('quantidade', s.get('quantidade_atual', 0)) or 0)
            disponivel = float(s.get('quantidade_disponivel', quantidade) or 0)
            atual = estoque_por_almox.get(key)
            if atual is None:
                estoque_por_almox[key] = {'quantidade': quantidade, 'disponivel': disponivel}
            else:
                atual['quantidade'] += quantidade
                atual['disponivel'] += disponivel

        # Carregar almoxarifados ativos
        items = []
        for a in almox_coll.find({'$or': [{'ativo': True}, {'ativo': {'$exists': False}}]}).sort('nome', 1):
            # id de saída preferindo sequencial e caindo para _id
            aid_out = a.get('id') if a.get('id') is not None else str(a.get('_id'))
            nome = a.get('nome') or a.get('descricao') or 'Sem nome'
            key = str(a.get('id') if a.get('id') is not None else a.get('_id'))
            est = estoque_por_almox.get(key)
            items.append({
                'id': aid_out,
                'nome': nome,
                'tem_estoque': est is not None and (est.get('quantidade', 0) > 0 or est.get('disponivel', 0) > 0),
                'quantidade_atual': est.get('quantidade', 0) if est else 0
            })

        return jsonify({'success': True, 'almoxarifados': items})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro ao listar almoxarifados: {e}'})

@main_bp.route('/api/produtos/<string:produto_id>/recebimento', methods=['POST'])
@require_any_level
def api_produto_recebimento(produto_id):
    """Registra recebimento de produto em um almoxarifado.
    - Atualiza/incrementa estoque em 'estoques'
    - Cria movimentação em 'movimentacoes'
    - Cria/atualiza lote em 'lotes' quando informado
    Aceita produto_id e almoxarifado_id como id sequencial (int) ou ObjectId string.
    """
    try:
        db = extensions.mongo_db
        produtos = db['produtos']
        almoxarifados = db['almoxarifados']
        estoques = db['estoques']
        movimentacoes = db['movimentacoes']
        lotes = db['lotes']

        data = request.get_json(silent=True) or {}
        quantidade = float(data.get('quantidade') or 0)
        if quantidade <= 0:
            return jsonify({'error': 'Quantidade deve ser maior que zero'}), 400

        # Resolver produto
        if str(produto_id).isdigit():
            prod_query = {'id': int(produto_id)}
        elif isinstance(produto_id, str) and len(produto_id) == 24:
            try:
                prod_query = {'_id': ObjectId(produto_id)}
            except Exception:
                prod_query = {'_id': produto_id}
        else:
            prod_query = {'id': produto_id}
        produto = produtos.find_one(prod_query)
        if not produto:
            return jsonify({'error': 'Produto não encontrado'}), 404

        # Resolver almoxarifado
        raw_aid = data.get('almoxarifado_id')
        if raw_aid is None or (isinstance(raw_aid, str) and raw_aid.strip() == ''):
            return jsonify({'error': 'almoxarifado_id é obrigatório'}), 400
        if isinstance(raw_aid, int) or (isinstance(raw_aid, str) and raw_aid.isdigit()):
            alm_query = {'id': int(raw_aid)}
            aid_out = int(raw_aid)
        elif isinstance(raw_aid, str) and len(raw_aid) == 24:
            try:
                obj_id = ObjectId(raw_aid)
                alm_query = {'_id': obj_id}
                aid_out = str(obj_id)
            except Exception:
                alm_query = {'_id': raw_aid}
                aid_out = raw_aid
        else:
            alm_query = {'_id': raw_aid}
            aid_out = raw_aid
        almox = almoxarifados.find_one(alm_query)
        if not almox:
            return jsonify({'error': 'Almoxarifado informado não existe'}), 400
        almox_nome = almox.get('nome') or almox.get('descricao') or 'Almoxarifado'

        # Normalizar ids de persistência (preferir id sequencial se existir)
        pid_out = produto.get('id') if produto.get('id') is not None else str(produto.get('_id'))
        aid_out = almox.get('id') if almox.get('id') is not None else str(almox.get('_id'))

        # Datas
        now = datetime.utcnow()
        def _parse_date(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(str(value))
            except Exception:
                return None
        data_recebimento = _parse_date(data.get('data_recebimento')) or now
        data_fabricacao = _parse_date(data.get('data_fabricacao'))
        data_vencimento = _parse_date(data.get('data_vencimento'))

        # Atualizar/incrementar estoque
        estoque_filter = {'produto_id': pid_out, 'local_tipo': 'almoxarifado', 'local_id': aid_out}
        estoque_update = {
            '$inc': {
                'quantidade': quantidade,
                'quantidade_disponivel': quantidade
            },
            '$set': {
                'produto_id': pid_out,
                'local_tipo': 'almoxarifado',
                'local_id': aid_out,
                'almoxarifado_id': aid_out,
                'nome_local': almox_nome,
                'updated_at': now
            },
            '$setOnInsert': {
                'created_at': now
            }
        }
        estoque_res = estoques.find_one_and_update(
            estoque_filter,
            estoque_update,
            return_document=ReturnDocument.AFTER,
            upsert=True
        )

        # Registrar movimentação
        mov_doc = {
            'produto_id': pid_out,
            'tipo': 'entrada',
            'quantidade': quantidade,
            'data_movimentacao': data_recebimento,
            'origem_nome': data.get('fornecedor') or 'Fornecedor',
            'destino_nome': almox_nome,
            'usuario_responsavel': getattr(current_user, 'username', None),
            'observacoes': data.get('observacoes'),
            'nota_fiscal': data.get('nota_fiscal'),
            'preco_unitario': data.get('preco_unitario'),
            'lote': data.get('lote') or None,
            'local_tipo': 'almoxarifado',
            'local_id': aid_out,
            'created_at': now
        }
        mov_ins = movimentacoes.insert_one(mov_doc)

        # Atualizar/registrar lote se informado
        lote_num = (data.get('lote') or '').strip()
        if lote_num:
            lote_filter = {'produto_id': pid_out, 'lote': lote_num, 'almoxarifado_id': aid_out}
            lote_update = {
                '$inc': {
                    'quantidade_atual': quantidade
                },
                '$set': {
                    'produto_id': pid_out,
                    'lote': lote_num,
                    'almoxarifado_id': aid_out,
                    'data_fabricacao': data_fabricacao,
                    'data_vencimento': data_vencimento,
                    'fornecedor': data.get('fornecedor'),
                    'updated_at': now
                },
                '$setOnInsert': {
                    'created_at': now
                }
            }
            lotes.find_one_and_update(lote_filter, lote_update, upsert=True)

        return jsonify({
            'success': True,
            'movimentacao_id': str(mov_ins.inserted_id),
            'estoque': {
                'produto_id': pid_out,
                'almoxarifado_id': aid_out,
                'quantidade': float(estoque_res.get('quantidade', 0)),
                'quantidade_disponivel': float(estoque_res.get('quantidade_disponivel', estoque_res.get('quantidade', 0)))
            }
        })
    except Exception as e:
        return jsonify({'error': f'Falha ao registrar recebimento: {e}'}), 500

@main_bp.route('/api/movimentacoes/transferencia', methods=['POST'])
@require_any_level
def api_movimentacoes_transferencia():
    """Executa transferência de estoque entre dois locais.
    Payload esperado:
    {
        produto_id: <id>,
        quantidade: <float>,
        motivo: <str|null>,
        observacoes: <str|null>,
        origem: { tipo: 'almoxarifado'|'sub_almoxarifado'|'setor'|'central', id: <id> },
        destino: { tipo: 'almoxarifado'|'sub_almoxarifado'|'setor'|'central', id: <id> }
    }
    """
    try:
        db = extensions.mongo_db
        produtos = db['produtos']
        estoques = db['estoques']
        movimentacoes = db['movimentacoes']

        data = request.get_json(silent=True) or {}
        # validação básica
        quantidade = float(data.get('quantidade') or 0)
        if quantidade <= 0:
            return jsonify({'error': 'Quantidade deve ser maior que zero'}), 400

        # produto
        raw_pid = data.get('produto_id')
        if raw_pid is None:
            return jsonify({'error': 'produto_id é obrigatório'}), 400
        prod_doc = None
        try:
            if str(raw_pid).isdigit():
                prod_doc = produtos.find_one({'id': int(raw_pid)})
            if not prod_doc:
                try:
                    prod_doc = produtos.find_one({'_id': ObjectId(str(raw_pid))})
                except Exception:
                    prod_doc = None
            if not prod_doc and isinstance(raw_pid, str):
                prod_doc = produtos.find_one({'id': raw_pid}) or produtos.find_one({'_id': raw_pid})
        except Exception:
            prod_doc = None
        if not prod_doc:
            return jsonify({'error': 'Produto não encontrado'}), 404
        pid_out = prod_doc.get('id') if prod_doc.get('id') is not None else str(prod_doc.get('_id'))

        # helpers de tipo
        def _coll_name_for_tipo(tipo: str):
            t = str(tipo).lower()
            if t in ('setor', 'setores'):
                return 'setores'
            if t in ('subalmoxarifado', 'sub_almoxarifado', 'sub_almoxarifados'):
                return 'sub_almoxarifados'
            if t in ('almoxarifado', 'almoxarifados'):
                return 'almoxarifados'
            if t in ('central', 'centrais'):
                return 'centrais'
            return None
        def _nome_por_doc(doc, default='Local'):
            return (doc or {}).get('nome') or (doc or {}).get('descricao') or default
        def _id_out(doc, raw):
            if doc is None:
                return str(raw)
            val = doc.get('id')
            if val is None:
                val = str(doc.get('_id'))
            return val
        def _field_by_tipo(tipo: str):
            t = str(tipo).lower()
            if t in ('setor', 'setores'):
                return 'setor_id'
            if t in ('subalmoxarifado', 'sub_almoxarifado', 'sub_almoxarifados'):
                return 'sub_almoxarifado_id'
            if t in ('almoxarifado', 'almoxarifados'):
                return 'almoxarifado_id'
            if t in ('central', 'centrais'):
                return 'central_id'
            return None

        # origem
        origem = data.get('origem') or {}
        destino = data.get('destino') or {}
        origem_tipo = origem.get('tipo')
        destino_tipo = destino.get('tipo')
        origem_id_raw = origem.get('id')
        destino_id_raw = destino.get('id')
        if not origem_tipo or origem_id_raw is None:
            return jsonify({'error': 'origem.tipo e origem.id são obrigatórios'}), 400
        if not destino_tipo or destino_id_raw is None:
            return jsonify({'error': 'destino.tipo e destino.id são obrigatórios'}), 400
        # impedir mesma origem/destino
        if str(origem_tipo).lower() == str(destino_tipo).lower() and str(origem_id_raw) == str(destino_id_raw):
            return jsonify({'error': 'Origem e destino não podem ser o mesmo local'}), 400

        # resolver docs
        ocoll = _coll_name_for_tipo(origem_tipo)
        dcoll = _coll_name_for_tipo(destino_tipo)
        if not ocoll or not dcoll:
            return jsonify({'error': 'Tipo de origem/destino inválido'}), 400
        origem_doc = _find_by_id(ocoll, origem_id_raw)
        destino_doc = _find_by_id(dcoll, destino_id_raw)
        if origem_doc is None:
            return jsonify({'error': 'Local de origem não encontrado'}), 400
        if destino_doc is None:
            return jsonify({'error': 'Local de destino não encontrado'}), 400
        origem_nome = _nome_por_doc(origem_doc, 'Origem')
        destino_nome = _nome_por_doc(destino_doc, 'Destino')
        origem_id_out = _id_out(origem_doc, origem_id_raw)
        destino_id_out = _id_out(destino_doc, destino_id_raw)

        now = datetime.utcnow()

        # localizar estoque de origem e validar disponibilidade
        origem_filter1 = {'produto_id': pid_out, 'local_tipo': str(origem_tipo).lower(), 'local_id': origem_id_out}
        origem_doc_estoque = estoques.find_one(origem_filter1)
        if not origem_doc_estoque:
            # fallback por campo específico
            ofield = _field_by_tipo(origem_tipo)
            if ofield:
                origem_doc_estoque = estoques.find_one({'produto_id': pid_out, ofield: origem_id_out})
        if not origem_doc_estoque:
            return jsonify({'error': 'Não há estoque no local de origem para este produto'}), 400
        disponivel = float(origem_doc_estoque.get('quantidade_disponivel', origem_doc_estoque.get('quantidade', 0)) or 0)
        if disponivel < quantidade:
            return jsonify({'error': 'Quantidade insuficiente na origem'}), 400

        # decrementar origem
        estoques.find_one_and_update(
            origem_filter1,
            {
                '$inc': {
                    'quantidade': -quantidade,
                    'quantidade_disponivel': -quantidade
                },
                '$set': {
                    'updated_at': now
                }
            }
        )

        # incrementar destino (upsert)
        dfield = _field_by_tipo(destino_tipo)
        set_fields = {
            'produto_id': pid_out,
            'local_tipo': str(destino_tipo).lower(),
            'local_id': destino_id_out,
            'nome_local': destino_nome,
            'updated_at': now
        }
        if dfield:
            set_fields[dfield] = destino_id_out
        dest_filter = {'produto_id': pid_out, 'local_tipo': str(destino_tipo).lower(), 'local_id': destino_id_out}
        dest_res = estoques.find_one_and_update(
            dest_filter,
            {
                '$inc': {
                    'quantidade': quantidade,
                    'quantidade_disponivel': quantidade
                },
                '$set': set_fields,
                '$setOnInsert': {
                    'created_at': now
                }
            },
            return_document=ReturnDocument.AFTER,
            upsert=True
        )

        # registrar movimentação
        mov_doc = {
            'produto_id': pid_out,
            'tipo': 'transferencia',
            'quantidade': quantidade,
            'data_movimentacao': now,
            'origem_tipo': str(origem_tipo).lower(),
            'origem_id': origem_id_out,
            'origem_nome': origem_nome,
            'destino_tipo': str(destino_tipo).lower(),
            'destino_id': destino_id_out,
            'destino_nome': destino_nome,
            'usuario_responsavel': getattr(current_user, 'username', None),
            'motivo': data.get('motivo'),
            'observacoes': data.get('observacoes'),
            'created_at': now
        }
        mov_ins = movimentacoes.insert_one(mov_doc)

        return jsonify({
            'success': True,
            'movimentacao_id': str(mov_ins.inserted_id),
            'estoque_origem': {
                'produto_id': pid_out,
                'local_tipo': str(origem_tipo).lower(),
                'local_id': origem_id_out
            },
            'estoque_destino': {
                'produto_id': pid_out,
                'local_tipo': str(destino_tipo).lower(),
                'local_id': destino_id_out,
                'quantidade': float(dest_res.get('quantidade', 0)),
                'quantidade_disponivel': float(dest_res.get('quantidade_disponivel', dest_res.get('quantidade', 0)))
            }
        })
    except Exception as e:
        return jsonify({'error': f'Falha ao executar transferência: {e}'}), 500

@main_bp.route('/api/movimentacoes/distribuicao', methods=['POST'])
@require_any_level
def api_movimentacoes_distribuicao():
    """Executa distribuição de estoque de uma origem para múltiplos setores.
    Payload esperado:
    {
        produto_id: <id>,
        quantidade_total: <float>,
        motivo: <str|null>,
        observacoes: <str|null>,
        origem: { tipo: 'almoxarifado'|'sub_almoxarifado'|'setor'|'central', id: <id> },
        setores_destino: [<id>, ...]
    }
    """
    try:
        db = extensions.mongo_db
        produtos = db['produtos']
        estoques = db['estoques']
        movimentacoes = db['movimentacoes']

        data = request.get_json(silent=True) or {}
        quantidade_total = float(data.get('quantidade_total') or 0)
        if quantidade_total <= 0:
            return jsonify({'error': 'quantidade_total deve ser maior que zero'}), 400

        # produto
        raw_pid = data.get('produto_id')
        if raw_pid is None:
            return jsonify({'error': 'produto_id é obrigatório'}), 400
        prod_doc = None
        try:
            if str(raw_pid).isdigit():
                prod_doc = produtos.find_one({'id': int(raw_pid)})
            if not prod_doc:
                try:
                    prod_doc = produtos.find_one({'_id': ObjectId(str(raw_pid))})
                except Exception:
                    prod_doc = None
            if not prod_doc and isinstance(raw_pid, str):
                prod_doc = produtos.find_one({'id': raw_pid}) or produtos.find_one({'_id': raw_pid})
        except Exception:
            prod_doc = None
        if not prod_doc:
            return jsonify({'error': 'Produto não encontrado'}), 404
        pid_out = prod_doc.get('id') if prod_doc.get('id') is not None else str(prod_doc.get('_id'))

        # helpers de tipo (locais)
        def _coll_name_for_tipo(tipo: str):
            t = str(tipo).lower()
            if t in ('setor', 'setores'):
                return 'setores'
            if t in ('subalmoxarifado', 'sub_almoxarifado', 'sub_almoxarifados'):
                return 'sub_almoxarifados'
            if t in ('almoxarifado', 'almoxarifados'):
                return 'almoxarifados'
            if t in ('central', 'centrais'):
                return 'centrais'
            return None
        def _nome_por_doc(doc, default='Local'):
            return (doc or {}).get('nome') or (doc or {}).get('descricao') or default
        def _id_out(doc, raw):
            if doc is None:
                return str(raw)
            val = doc.get('id')
            if val is None:
                val = str(doc.get('_id'))
            return val
        def _field_by_tipo(tipo: str):
            t = str(tipo).lower()
            if t in ('setor', 'setores'):
                return 'setor_id'
            if t in ('subalmoxarifado', 'sub_almoxarifado', 'sub_almoxarifados'):
                return 'sub_almoxarifado_id'
            if t in ('almoxarifado', 'almoxarifados'):
                return 'almoxarifado_id'
            if t in ('central', 'centrais'):
                return 'central_id'
            return None

        # origem e setores destino
        origem = data.get('origem') or {}
        setores_destino = data.get('setores_destino') or []
        origem_tipo = origem.get('tipo')
        origem_id_raw = origem.get('id')
        if not origem_tipo or origem_id_raw is None:
            return jsonify({'error': 'origem.tipo e origem.id são obrigatórios'}), 400
        if not setores_destino or not isinstance(setores_destino, list):
            return jsonify({'error': 'setores_destino deve ser uma lista com ao menos um setor'}), 400

        ocoll = _coll_name_for_tipo(origem_tipo)
        if not ocoll:
            return jsonify({'error': 'Tipo de origem inválido'}), 400
        origem_doc = _find_by_id(ocoll, origem_id_raw)
        if origem_doc is None:
            return jsonify({'error': 'Local de origem não encontrado'}), 400
        origem_nome = _nome_por_doc(origem_doc, 'Origem')
        origem_id_out = _id_out(origem_doc, origem_id_raw)

        # validar setores destino
        destino_setores_docs = []
        for sid in setores_destino:
            sdoc = _find_by_id('setores', sid)
            if sdoc is None:
                return jsonify({'error': 'Algum setor de destino não foi encontrado'}), 404
            destino_setores_docs.append(sdoc)
        if len(destino_setores_docs) == 0:
            return jsonify({'error': 'Nenhum setor válido informado'}), 400

        now = datetime.utcnow()

        # localizar estoque na origem e validar disponibilidade
        origem_filter1 = {'produto_id': pid_out, 'local_tipo': str(origem_tipo).lower(), 'local_id': origem_id_out}
        origem_doc_estoque = estoques.find_one(origem_filter1)
        if not origem_doc_estoque:
            ofield = _field_by_tipo(origem_tipo)
            if ofield:
                origem_doc_estoque = estoques.find_one({'produto_id': pid_out, ofield: origem_id_out})
        if not origem_doc_estoque:
            return jsonify({'error': 'Não há estoque no local de origem para este produto'}), 400
        disponivel = float(origem_doc_estoque.get('quantidade_disponivel', origem_doc_estoque.get('quantidade', 0)) or 0)
        if disponivel < quantidade_total:
            return jsonify({'error': 'Quantidade insuficiente na origem'}), 400

        # cálculo igualitário por setor
        qtd_setores = len(destino_setores_docs)
        quantidade_por_setor = quantidade_total / qtd_setores
        if quantidade_por_setor <= 0:
            return jsonify({'error': 'Quantidade por setor calculada inválida'}), 400

        # debitar origem
        estoques.find_one_and_update(
            origem_filter1,
            {
                '$inc': {
                    'quantidade': -quantidade_total,
                    'quantidade_disponivel': -quantidade_total
                },
                '$set': {
                    'updated_at': now
                }
            }
        )

        movimentos_criados = 0
        for sdoc in destino_setores_docs:
            setor_id_out = _id_out(sdoc, sdoc.get('_id'))
            setor_nome = _nome_por_doc(sdoc, 'Setor')

            # incrementar destino (upsert)
            dest_filter = {'produto_id': pid_out, 'local_tipo': 'setor', 'local_id': setor_id_out}
            dest_update = {
                '$inc': {
                    'quantidade': quantidade_por_setor,
                    'quantidade_disponivel': quantidade_por_setor
                },
                '$set': {
                    'produto_id': pid_out,
                    'local_tipo': 'setor',
                    'local_id': setor_id_out,
                    'nome_local': setor_nome,
                    'updated_at': now
                },
                '$setOnInsert': {
                    'created_at': now
                }
            }
            estoques.find_one_and_update(
                dest_filter,
                dest_update,
                return_document=ReturnDocument.AFTER,
                upsert=True
            )

            # registrar movimentação
            mov_doc = {
                'produto_id': pid_out,
                'tipo': 'distribuicao',
                'quantidade': quantidade_por_setor,
                'data_movimentacao': now,
                'origem_tipo': str(origem_tipo).lower(),
                'origem_id': origem_id_out,
                'origem_nome': origem_nome,
                'destino_tipo': 'setor',
                'destino_id': setor_id_out,
                'destino_nome': setor_nome,
                'usuario_responsavel': getattr(current_user, 'username', None),
                'motivo': data.get('motivo'),
                'observacoes': data.get('observacoes'),
                'created_at': now
            }
            movimentacoes.insert_one(mov_doc)
            movimentos_criados += 1

        return jsonify({
            'success': True,
            'movimentacoes_criadas': movimentos_criados,
            'quantidade_por_setor': quantidade_por_setor,
            'total_distribuida': quantidade_total
        })
    except Exception as e:
        return jsonify({'error': f'Falha ao executar distribuição: {e}'}), 500
