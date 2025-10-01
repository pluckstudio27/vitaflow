from flask import Blueprint, request, jsonify
from flask_login import current_user
from models.categoria import CategoriaProduto
from models.produto import Produto
from models.usuario import Usuario
from extensions import db
from sqlalchemy.exc import IntegrityError
from auth import require_admin_or_above, require_manager_or_above, require_any_level

categorias_api_bp = Blueprint('categorias_api', __name__)

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Função auxiliar para paginação"""
    per_page = min(per_page, max_per_page)
    
    try:
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
        
        return jsonify(paginate_query(query, page, per_page))
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>', methods=['GET'])
@require_any_level
def get_categoria(id):
    """Obter categoria específica"""
    categoria = CategoriaProduto.query.get_or_404(id)
    return jsonify(categoria.to_dict())

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
        
        # Verificar duplicatas
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
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro de integridade dos dados'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_categoria(id):
    """Atualizar categoria"""
    try:
        categoria = CategoriaProduto.query.get_or_404(id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
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
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro de integridade dos dados'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_categoria(id):
    """Deletar categoria"""
    try:
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
        
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/toggle-status', methods=['POST'])
@require_admin_or_above
def toggle_categoria_status(id):
    """Alternar status ativo/inativo da categoria"""
    try:
        categoria = CategoriaProduto.query.get_or_404(id)
        categoria.ativo = not categoria.ativo
        
        db.session.commit()
        
        status = 'ativada' if categoria.ativo else 'desativada'
        return jsonify({
            'message': f'Categoria {status} com sucesso',
            'categoria': categoria.to_dict()
        })
        
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/produtos', methods=['GET'])
@require_any_level
def get_categoria_produtos(id):
    """Listar produtos de uma categoria específica"""
    try:
        categoria = CategoriaProduto.query.get_or_404(id)
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        
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
        
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@categorias_api_bp.route('/categorias/<int:id>/usuarios', methods=['GET'])
@require_admin_or_above
def get_categoria_usuarios(id):
    """Listar usuários de uma categoria específica"""
    try:
        categoria = CategoriaProduto.query.get_or_404(id)
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        
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
        
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500