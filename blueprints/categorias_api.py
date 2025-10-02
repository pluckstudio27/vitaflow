from flask import Blueprint, request, jsonify
from flask_login import current_user
from extensions import db
from auth_mongo import require_admin_or_above, require_manager_or_above, require_any_level

# Importar modelos MongoDB como primários
try:
    from models_mongo.categoria import CategoriaProdutoMongo
    from models_mongo.produto import ProdutoMongo
    from models_mongo.usuario import UsuarioMongo
    USE_MONGO = True
except ImportError:
    # Fallback para modelos SQLAlchemy
    from models.categoria import CategoriaProduto
    from models.produto import Produto
    from models.usuario import Usuario
    from sqlalchemy.exc import IntegrityError
    USE_MONGO = False

categorias_api_bp = Blueprint('categorias_api', __name__)

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Função auxiliar para paginação"""
    per_page = min(per_page, max_per_page)
    
    try:
        if USE_MONGO:
            # Para MongoDB, query é uma lista de documentos
            total = len(query)
            start = (page - 1) * per_page
            end = start + per_page
            items = query[start:end]
            
            pages = (total + per_page - 1) // per_page
            has_next = page < pages
            has_prev = page > 1
            
            return {
                'items': [item.to_dict() if hasattr(item, 'to_dict') else item for item in items],
                'total': total,
                'pages': pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': has_next,
                'has_prev': has_prev,
                'next_num': page + 1 if has_next else None,
                'prev_num': page - 1 if has_prev else None
            }
        else:
            # Para SQLAlchemy
            paginated = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            return {
                'items': [item.to_dict() for item in paginated.items],
                'total': paginated.total,
                'pages': paginated.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev,
                'next_num': paginated.next_num,
                'prev_num': paginated.prev_num
            }
    except Exception:
        return {
            'items': [],
            'total': 0,
            'pages': 0,
            'current_page': page,
            'per_page': per_page,
            'has_next': False,
            'has_prev': False,
            'next_num': None,
            'prev_num': None
        }

@categorias_api_bp.route('/categorias', methods=['GET'])
@require_any_level
def get_categorias():
    """Listar categorias de produtos com paginação e filtros"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        
        if USE_MONGO:
            # Usar modelos MongoDB
            filter_dict = {}
            
            if search:
                filter_dict['$or'] = [
                    {'nome': {'$regex': search, '$options': 'i'}},
                    {'codigo': {'$regex': search, '$options': 'i'}},
                    {'descricao': {'$regex': search, '$options': 'i'}}
                ]
            
            if ativo is not None:
                filter_dict['ativo'] = ativo
                
            categorias = CategoriaProdutoMongo.find_many(filter_dict)
        else:
            # Usar modelos SQLAlchemy
            query = CategoriaProduto.query
            
            if search:
                query = query.filter(
                    db.or_(
                        CategoriaProduto.nome.ilike(f'%{search}%'),
                        CategoriaProduto.codigo.ilike(f'%{search}%'),
                        CategoriaProduto.descricao.ilike(f'%{search}%')
                    )
                )
            
            if ativo is not None:
                query = query.filter(CategoriaProduto.ativo == ativo)
            
            query = query.order_by(CategoriaProduto.nome)
            categorias = query
        
        return jsonify(paginate_query(categorias, page, per_page))
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>', methods=['GET'])
@require_any_level
def get_categoria(id):
    """Obter categoria específica"""
    try:
        if USE_MONGO:
            categoria = CategoriaProdutoMongo.find_by_id(str(id))
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
        else:
            categoria = CategoriaProduto.query.get_or_404(id)
        
        return jsonify(categoria.to_dict())
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias', methods=['POST'])
@require_admin_or_above
def create_categoria():
    """Criar nova categoria de produto"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validações obrigatórias
        if not data.get('nome', '').strip():
            return jsonify({'error': 'Nome é obrigatório'}), 400
        
        if not data.get('codigo', '').strip():
            return jsonify({'error': 'Código é obrigatório'}), 400
        
        if USE_MONGO:
            # Verificar duplicatas no MongoDB
            existing_nome = CategoriaProdutoMongo.find_one({'nome': {'$regex': f'^{data["nome"].strip()}$', '$options': 'i'}})
            if existing_nome:
                return jsonify({'error': 'Já existe uma categoria com este nome'}), 400
            
            existing_codigo = CategoriaProdutoMongo.find_one({'codigo': {'$regex': f'^{data["codigo"].strip()}$', '$options': 'i'}})
            if existing_codigo:
                return jsonify({'error': 'Já existe uma categoria com este código'}), 400
            
            categoria = CategoriaProdutoMongo(
                nome=data['nome'].strip(),
                codigo=data['codigo'].strip(),
                descricao=data.get('descricao', '').strip(),
                cor=data.get('cor', '#007bff').strip(),
                ativo=data.get('ativo', True)
            )
            
            categoria.save()
            return jsonify(categoria.to_dict()), 201
        else:
            # Verificar duplicatas no SQLAlchemy
            existing_nome = CategoriaProduto.query.filter(
                CategoriaProduto.nome.ilike(data['nome'].strip())
            ).first()
            if existing_nome:
                return jsonify({'error': 'Já existe uma categoria com este nome'}), 400
            
            existing_codigo = CategoriaProduto.query.filter(
                CategoriaProduto.codigo.ilike(data['codigo'].strip())
            ).first()
            if existing_codigo:
                return jsonify({'error': 'Já existe uma categoria com este código'}), 400
            
            categoria = CategoriaProduto(
                nome=data['nome'].strip(),
                codigo=data['codigo'].strip(),
                descricao=data.get('descricao', '').strip(),
                cor=data.get('cor', '#007bff').strip(),
                ativo=data.get('ativo', True)
            )
            
            db.session.add(categoria)
            db.session.commit()
            return jsonify(categoria.to_dict()), 201
        
    except Exception as e:
        if not USE_MONGO:
            db.session.rollback()
        print(f"Erro ao criar categoria: {e}")
        return jsonify({'error': 'Erro de integridade dos dados' if 'duplicate' in str(e).lower() else 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_categoria(id):
    """Atualizar categoria"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        if USE_MONGO:
            # MongoDB
            categoria = CategoriaProdutoMongo.find_by_id(id)
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            
            # Validações
            if 'nome' in data:
                if not data['nome'].strip():
                    return jsonify({'error': 'Nome não pode estar vazio'}), 400
                
                existing = CategoriaProdutoMongo.find_one({
                    'nome': {'$regex': f'^{data["nome"].strip()}$', '$options': 'i'},
                    '_id': {'$ne': categoria._id}
                })
                if existing:
                    return jsonify({'error': 'Já existe uma categoria com este nome'}), 400
                
                categoria.nome = data['nome'].strip()
            
            if 'codigo' in data:
                if not data['codigo'].strip():
                    return jsonify({'error': 'Código não pode estar vazio'}), 400
                
                existing = CategoriaProdutoMongo.find_one({
                    'codigo': {'$regex': f'^{data["codigo"].strip()}$', '$options': 'i'},
                    '_id': {'$ne': categoria._id}
                })
                if existing:
                    return jsonify({'error': 'Já existe uma categoria com este código'}), 400
                
                categoria.codigo = data['codigo'].strip()
            
            if 'descricao' in data:
                categoria.descricao = data['descricao'].strip()
            
            if 'cor' in data:
                categoria.cor = data['cor'].strip()
            
            if 'ativo' in data:
                categoria.ativo = bool(data['ativo'])
            
            categoria.save()
            return jsonify(categoria.to_dict())
        
        else:
            # SQLAlchemy
            categoria = CategoriaProduto.query.get_or_404(id)
            
            # Validações
            if 'nome' in data:
                if not data['nome'].strip():
                    return jsonify({'error': 'Nome não pode estar vazio'}), 400
                
                existing = CategoriaProduto.query.filter(
                    CategoriaProduto.nome.ilike(data['nome'].strip()),
                    CategoriaProduto.id != id
                ).first()
                if existing:
                    return jsonify({'error': 'Já existe uma categoria com este nome'}), 400
                
                categoria.nome = data['nome'].strip()
            
            if 'codigo' in data:
                if not data['codigo'].strip():
                    return jsonify({'error': 'Código não pode estar vazio'}), 400
                
                existing = CategoriaProduto.query.filter(
                    CategoriaProduto.codigo.ilike(data['codigo'].strip()),
                    CategoriaProduto.id != id
                ).first()
                if existing:
                    return jsonify({'error': 'Já existe uma categoria com este código'}), 400
                
                categoria.codigo = data['codigo'].strip()
            
            if 'descricao' in data:
                categoria.descricao = data['descricao'].strip()
            
            if 'cor' in data:
                categoria.cor = data['cor'].strip()
            
            if 'ativo' in data:
                categoria.ativo = bool(data['ativo'])
            
            db.session.commit()
            return jsonify(categoria.to_dict())
        
    except Exception as e:
        if not USE_MONGO:
            db.session.rollback()
        return jsonify({'error': 'Erro de integridade dos dados' if 'duplicate' in str(e).lower() else 'Erro interno do servidor'}), 400

@categorias_api_bp.route('/categorias/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_categoria(id):
    """Deletar categoria"""
    try:
        if USE_MONGO:
            # MongoDB
            categoria = CategoriaProdutoMongo.find_by_id(id)
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            
            # Verificar se há produtos associados
            produtos_count = ProdutoMongo.count({'categoria_id': id})
            if produtos_count > 0:
                return jsonify({
                    'error': f'Não é possível deletar a categoria. Existem {produtos_count} produto(s) associado(s).'
                }), 400
            
            # Verificar se há usuários associados
            usuarios_count = UsuarioMongo.count({'categoria_id': id})
            if usuarios_count > 0:
                return jsonify({
                    'error': f'Não é possível deletar a categoria. Existem {usuarios_count} usuário(s) associado(s).'
                }), 400
            
            categoria.delete()
            return jsonify({'message': 'Categoria deletada com sucesso'})
        
        else:
            # SQLAlchemy
            categoria = CategoriaProduto.query.get_or_404(id)
            
            # Verificar se há produtos associados
            produtos_count = Produto.query.filter_by(categoria_id=id).count()
            if produtos_count > 0:
                return jsonify({
                    'error': f'Não é possível deletar a categoria. Existem {produtos_count} produto(s) associado(s).'
                }), 400
            
            # Verificar se há usuários associados
            usuarios_count = Usuario.query.filter_by(categoria_id=id).count()
            if usuarios_count > 0:
                return jsonify({
                    'error': f'Não é possível deletar a categoria. Existem {usuarios_count} usuário(s) associado(s).'
                }), 400
            
            db.session.delete(categoria)
            db.session.commit()
            
            return jsonify({'message': 'Categoria deletada com sucesso'})
        
    except Exception as e:
        if not USE_MONGO:
            db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/toggle-status', methods=['POST'])
@require_admin_or_above
def toggle_categoria_status(id):
    """Alternar status ativo/inativo da categoria"""
    try:
        if USE_MONGO:
            # MongoDB
            categoria = CategoriaProdutoMongo.find_by_id(id)
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            
            categoria.ativo = not categoria.ativo
            categoria.save()
            
            status = 'ativada' if categoria.ativo else 'desativada'
            return jsonify({
                'message': f'Categoria {status} com sucesso',
                'categoria': categoria.to_dict()
            })
        
        else:
            # SQLAlchemy
            categoria = CategoriaProduto.query.get_or_404(id)
            categoria.ativo = not categoria.ativo
            
            db.session.commit()
            
            status = 'ativada' if categoria.ativo else 'desativada'
            return jsonify({
                'message': f'Categoria {status} com sucesso',
                'categoria': categoria.to_dict()
            })
        
    except Exception as e:
        if not USE_MONGO:
            db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/produtos', methods=['GET'])
@require_any_level
def get_categoria_produtos(id):
    """Listar produtos de uma categoria específica"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        
        if USE_MONGO:
            # MongoDB
            categoria = CategoriaProdutoMongo.find_by_id(id)
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            
            # Construir filtro
            filter_dict = {'categoria_id': id}
            
            if search:
                filter_dict['$or'] = [
                    {'nome': {'$regex': search, '$options': 'i'}},
                    {'codigo': {'$regex': search, '$options': 'i'}},
                    {'descricao': {'$regex': search, '$options': 'i'}}
                ]
            
            if ativo is not None:
                filter_dict['ativo'] = ativo
            
            # Buscar produtos
            produtos = ProdutoMongo.find_many(filter_dict, sort=[('nome', 1)])
            
            result = paginate_query(produtos, page, per_page)
            result['categoria'] = categoria.to_dict()
            
            return jsonify(result)
        
        else:
            # SQLAlchemy
            categoria = CategoriaProduto.query.get_or_404(id)
            
            query = Produto.query.filter_by(categoria_id=id)
            
            if search:
                query = query.filter(
                    db.or_(
                        Produto.nome.ilike(f'%{search}%'),
                        Produto.codigo.ilike(f'%{search}%'),
                        Produto.descricao.ilike(f'%{search}%')
                    )
                )
            
            if ativo is not None:
                query = query.filter(Produto.ativo == ativo)
            
            query = query.order_by(Produto.nome)
            
            result = paginate_query(query, page, per_page)
            result['categoria'] = categoria.to_dict()
            
            return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/usuarios', methods=['GET'])
@require_admin_or_above
def get_categoria_usuarios(id):
    """Listar usuários de uma categoria específica"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        
        if USE_MONGO:
            # MongoDB
            categoria = CategoriaProdutoMongo.find_by_id(id)
            if not categoria:
                return jsonify({'error': 'Categoria não encontrada'}), 404
            
            # Construir filtro
            filter_dict = {'categoria_id': id}
            
            if search:
                filter_dict['$or'] = [
                    {'nome_completo': {'$regex': search, '$options': 'i'}},
                    {'username': {'$regex': search, '$options': 'i'}},
                    {'email': {'$regex': search, '$options': 'i'}}
                ]
            
            if ativo is not None:
                filter_dict['ativo'] = ativo
            
            # Buscar usuários
            usuarios = UsuarioMongo.find_many(filter_dict, sort=[('nome_completo', 1)])
            
            result = paginate_query(usuarios, page, per_page)
            result['categoria'] = categoria.to_dict()
            
            return jsonify(result)
        
        else:
            # SQLAlchemy
            categoria = CategoriaProduto.query.get_or_404(id)
            
            query = Usuario.query.filter_by(categoria_id=id)
            
            if search:
                query = query.filter(
                    db.or_(
                        Usuario.nome_completo.ilike(f'%{search}%'),
                        Usuario.username.ilike(f'%{search}%'),
                        Usuario.email.ilike(f'%{search}%')
                    )
                )
            
            if ativo is not None:
                query = query.filter(Usuario.ativo == ativo)
            
            query = query.order_by(Usuario.nome_completo)
            
            result = paginate_query(query, page, per_page)
            result['categoria'] = categoria.to_dict()
            
            return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Erro interno do servidor'}), 500