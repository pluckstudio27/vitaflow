from flask import Blueprint, request, jsonify
from flask_login import current_user
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from models.produto import Produto, EstoqueProduto, LoteProduto, MovimentacaoProduto
from models.usuario import Usuario
from models.categoria import CategoriaProduto
from extensions import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from decimal import Decimal
import re
from auth import (require_any_level, require_manager_or_above, require_admin_or_above, 
                  ScopeFilter)

api_bp = Blueprint('api', __name__)

# Função auxiliar para paginação
def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Aplica paginação a uma query"""
    page = max(1, int(page))
    per_page = min(max_per_page, max(1, int(per_page)))
    
    paginated = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return {
        'items': [item.to_dict() for item in paginated.items],
        'page': paginated.page,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'pages': paginated.pages,
        'has_next': paginated.has_next,
        'has_prev': paginated.has_prev,
        'next_num': paginated.next_num,
        'prev_num': paginated.prev_num
    }

# Função auxiliar para validação
def validate_required_fields(data, required_fields):
    """Valida se os campos obrigatórios estão presentes"""
    if not data:
        return {'error': 'Dados não fornecidos'}, 400
    
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return {'error': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'}, 400
    
    return None, None

# Função auxiliar para validação de texto
def validate_text_field(text, field_name, min_length=1, max_length=255):
    """Valida campos de texto"""
    if not isinstance(text, str):
        return f'{field_name} deve ser uma string'
    
    text = text.strip()
    if len(text) < min_length:
        return f'{field_name} deve ter pelo menos {min_length} caracteres'
    
    if len(text) > max_length:
        return f'{field_name} deve ter no máximo {max_length} caracteres'
    
    # Validação básica contra caracteres especiais perigosos
    if re.search(r'[<>"\']', text):
        return f'{field_name} contém caracteres não permitidos'
    
    return None

# ============================================================================
# ROTAS PARA CENTRAL
# ============================================================================

@api_bp.route('/centrais', methods=['GET'])
@require_any_level
def get_centrais():
    """Listar todas as centrais com paginação e filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ativo = request.args.get('ativo', type=bool)
    search = request.args.get('search', '').strip()
    
    query = Central.query.options(joinedload(Central.almoxarifados))
    
    # Aplicar filtros de escopo baseados no usuário logado
    query = ScopeFilter.filter_centrais(query)
    
    if ativo is not None:
        query = query.filter(Central.ativo == ativo)
    
    if search:
        query = query.filter(Central.nome.ilike(f'%{search}%'))
    
    query = query.order_by(Central.nome)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/centrais/<int:id>', methods=['GET'])
@require_any_level
def get_central(id):
    """Buscar central por ID com eager loading"""
    central = Central.query.options(
        joinedload(Central.almoxarifados).joinedload(Almoxarifado.sub_almoxarifados)
    ).get_or_404(id)
    return jsonify(central.to_dict())

@api_bp.route('/centrais', methods=['POST'])
@require_admin_or_above
def create_central():
    """Criar nova central com validações robustas"""
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['nome'])
    if error:
        return jsonify(error), status
    
    nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
    if nome_error:
        return jsonify({'error': nome_error}), 400
    
    descricao = data.get('descricao', '').strip()
    if descricao:
        desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
        if desc_error:
            return jsonify({'error': desc_error}), 400
    
    existing = Central.query.filter(Central.nome.ilike(data['nome'].strip())).first()
    if existing:
        return jsonify({'error': 'Já existe uma central com este nome'}), 400
    
    central = Central(
        nome=data['nome'].strip(),
        descricao=descricao,
        ativo=data.get('ativo', True)
    )
    
    try:
        db.session.add(central)
        db.session.commit()
        return jsonify(central.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar central: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ==================== RELATÓRIOS ====================

@api_bp.route('/estoque/relatorios/resumo', methods=['GET'])
@require_admin_or_above
def get_relatorio_estoque_resumo():
    """Relatório resumo do estoque"""
    try:
        # Buscar dados básicos do estoque
        total_produtos = Produto.query.count()
        total_estoque = db.session.query(db.func.sum(EstoqueProduto.quantidade)).scalar() or 0
        
        return jsonify({
            'total_produtos': total_produtos,
            'total_estoque': float(total_estoque),
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': 'Erro ao gerar relatório'}), 500

@api_bp.route('/relatorios/produtos/export', methods=['GET'])
@require_admin_or_above
def export_relatorio_produtos():
    """Exportar relatório de produtos"""
    try:
        produtos = Produto.query.all()
        dados = []
        for produto in produtos:
            dados.append({
                'id': produto.id,
                'nome': produto.nome,
                'codigo': produto.codigo,
                'categoria': produto.categoria_obj.nome if produto.categoria_obj else 'N/A'
            })
        
        return jsonify({
            'produtos': dados,
            'total': len(dados),
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': 'Erro ao exportar relatório'}), 500


# ============================================================================
# ROTAS PARA USUÁRIOS
# ============================================================================

@api_bp.route('/usuarios', methods=['GET'])
@require_admin_or_above
def get_usuarios():
    """Listar todos os usuários com paginação e filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ativo = request.args.get('ativo', type=bool)
    nivel = request.args.get('nivel', '').strip()
    search = request.args.get('search', '').strip()
    
    query = Usuario.query
    
    if ativo is not None:
        query = query.filter(Usuario.ativo == ativo)
    
    if nivel:
        query = query.filter(Usuario.nivel == nivel)
    
    if search:
        query = query.filter(
            db.or_(
                Usuario.nome_completo.ilike(f'%{search}%'),
                Usuario.email.ilike(f'%{search}%'),
                Usuario.username.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(Usuario.nome_completo)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/usuarios/<int:id>', methods=['GET'])
@require_admin_or_above
def get_usuario(id):
    """Buscar usuário por ID"""
    usuario = Usuario.query.get_or_404(id)
    return jsonify(usuario.to_dict())

@api_bp.route('/usuarios', methods=['POST'])
@require_admin_or_above
def create_usuario():
    """Criar novo usuário"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    # Validações obrigatórias
    required_fields = ['nome', 'email', 'login', 'senha', 'nivel']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} é obrigatório'}), 400
    
    # Validar se username e email são únicos
    if Usuario.query.filter_by(username=data['login']).first():
        return jsonify({'error': 'Login já existe'}), 400
    
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email já existe'}), 400
    
    try:
        usuario = Usuario(
            nome_completo=data['nome'],
            email=data['email'],
            username=data['login'],
            nivel_acesso=data['nivel'],
            ativo=data.get('ativo', True),
            central_id=data.get('central_id'),
            almoxarifado_id=data.get('almoxarifado_id'),
            sub_almoxarifado_id=data.get('sub_almoxarifado_id'),
            setor_id=data.get('setor_id'),
            categoria_id=data.get('categoria_id')
        )
        
        # Definir senha
        usuario.set_password(data['senha'])
        
        db.session.add(usuario)
        db.session.commit()
        
        return jsonify(usuario.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar usuário: violação de integridade'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/usuarios/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_usuario(id):
    """Atualizar usuário"""
    usuario = Usuario.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    try:
        # Validar se username e email são únicos (exceto para o próprio usuário)
        if 'login' in data and data['login'] != usuario.username:
            if Usuario.query.filter_by(username=data['login']).first():
                return jsonify({'error': 'Login já existe'}), 400
            usuario.username = data['login']
        
        if 'email' in data and data['email'] != usuario.email:
            if Usuario.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email já existe'}), 400
            usuario.email = data['email']
        
        # Atualizar outros campos
        if 'nome' in data:
            usuario.nome_completo = data['nome']
        if 'nome_completo' in data:
            usuario.nome_completo = data['nome_completo']
        if 'nivel' in data:
            usuario.nivel_acesso = data['nivel']
        if 'ativo' in data:
            usuario.ativo = data['ativo']
        if 'central_id' in data:
            usuario.central_id = data['central_id']
        if 'almoxarifado_id' in data:
            usuario.almoxarifado_id = data['almoxarifado_id']
        if 'sub_almoxarifado_id' in data:
            usuario.sub_almoxarifado_id = data['sub_almoxarifado_id']
        if 'setor_id' in data:
            usuario.setor_id = data['setor_id']
        if 'categoria_id' in data:
            usuario.categoria_id = data['categoria_id']
        
        # Atualizar senha se fornecida
        if 'senha' in data and data['senha']:
            usuario.set_password(data['senha'])
        
        db.session.commit()
        return jsonify(usuario.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar usuário: violação de integridade'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/usuarios/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_usuario(id):
    """Excluir usuário"""
    from models.usuario import LogAuditoria
    
    usuario = Usuario.query.get_or_404(id)
    
    # Não permitir excluir o próprio usuário
    if current_user.is_authenticated and current_user.id == id:
        return jsonify({'error': 'Não é possível excluir seu próprio usuário'}), 400
    
    # Verificar se há registros de auditoria
    logs_count = LogAuditoria.query.filter_by(usuario_id=id).count()
    if logs_count > 0:
        return jsonify({
            'error': f'Não é possível excluir este usuário pois existem {logs_count} registro(s) de auditoria associado(s). Para manter a integridade dos logs do sistema, considere desativar o usuário ao invés de excluí-lo.'
        }), 400
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'message': 'Usuário excluído com sucesso'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir usuário: violação de integridade'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/usuarios/<int:id>/toggle-status', methods=['POST'])
@require_admin_or_above
def toggle_usuario_status(id):
    """Ativar/desativar usuário"""
    usuario = Usuario.query.get_or_404(id)
    
    # Não permitir desativar o próprio usuário
    if current_user.is_authenticated and current_user.id == id:
        return jsonify({'error': 'Não é possível desativar seu próprio usuário'}), 400
    
    try:
        usuario.ativo = not usuario.ativo
        db.session.commit()
        
        status = 'ativado' if usuario.ativo else 'desativado'
        return jsonify({
            'message': f'Usuário {status} com sucesso',
            'ativo': usuario.ativo
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/usuarios/<int:id>/reset-password', methods=['POST'])
@require_admin_or_above
def reset_usuario_password(id):
    """Resetar senha do usuário"""
    usuario = Usuario.query.get_or_404(id)
    
    # Aceita tanto JSON quanto form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    nova_senha = data.get('nova_senha') if data else None
    
    if not nova_senha:
        # Se não foi fornecida nova senha, gera uma automaticamente
        import secrets
        import string
        nova_senha = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    try:
        usuario.set_password(nova_senha)
        db.session.commit()
        
        return jsonify({
            'message': 'Senha resetada com sucesso',
            'nova_senha': nova_senha
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/estoque/hierarquia', methods=['GET'])
@require_any_level
def get_estoque_hierarquia():
    """Obter estoque organizado por hierarquia"""
    try:
        # Buscar todos os estoques ativos com produtos
        query = db.session.query(EstoqueProduto).join(Produto).filter(
            EstoqueProduto.ativo == True,
            Produto.ativo == True
        )
        
        # Aplicar filtros de escopo baseados no usuário logado
        query = ScopeFilter.filter_estoque(query)
        
        estoques = query.all()
        
        estoque_data = []
        
        for estoque in estoques:
            item = {
                'id': estoque.id,
                'produto_id': estoque.produto_id,
                'produto_codigo': estoque.produto.codigo,
                'produto_nome': estoque.produto.nome,
                'quantidade': float(estoque.quantidade or 0),
                'quantidade_reservada': float(estoque.quantidade_reservada or 0),
                'quantidade_disponivel': float(estoque.quantidade_disponivel or 0),
                'local_nome': estoque.get_location_name(),
                'local_tipo': '',
                'local_id': None
            }
            
            # Determinar tipo e ID do local
            if estoque.almoxarifado_id:
                item['local_tipo'] = 'ALMOXARIFADO'
                item['local_id'] = estoque.almoxarifado_id
            elif estoque.sub_almoxarifado_id:
                item['local_tipo'] = 'SUBALMOXARIFADO'
                item['local_id'] = estoque.sub_almoxarifado_id
            elif estoque.setor_id:
                item['local_tipo'] = 'SETOR'
                item['local_id'] = estoque.setor_id
            
            estoque_data.append(item)
        
        return jsonify(estoque_data)
    except Exception as e:
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/hierarquia/locais', methods=['GET'])
@require_any_level
def get_hierarquia_locais():
    """Obter todos os locais da hierarquia como um array único"""
    try:
        locais = []
        
        # Buscar centrais ativas com filtro de escopo
        centrais = ScopeFilter.filter_centrais(Central.query.filter_by(ativo=True)).all()
        for central in centrais:
            locais.append({
                'id': central.id,
                'nome': central.nome,
                'tipo': 'central'
            })
        
        # Buscar almoxarifados ativos com filtro de escopo
        almoxarifados = ScopeFilter.filter_almoxarifados(Almoxarifado.query.filter_by(ativo=True)).all()
        for almox in almoxarifados:
            locais.append({
                'id': almox.id,
                'nome': almox.nome,
                'central_id': almox.central_id,
                'tipo': 'almoxarifado'
            })
        
        # Buscar sub-almoxarifados ativos com filtro de escopo
        sub_almoxarifados = ScopeFilter.filter_sub_almoxarifados(SubAlmoxarifado.query.filter_by(ativo=True)).all()
        for sub_almox in sub_almoxarifados:
            locais.append({
                'id': sub_almox.id,
                'nome': sub_almox.nome,
                'almoxarifado_id': sub_almox.almoxarifado_id,
                'tipo': 'subalmoxarifado'
            })
        
        # Buscar setores ativos com filtro de escopo
        setores = ScopeFilter.filter_setores(Setor.query.filter_by(ativo=True)).all()
        for setor in setores:
            locais.append({
                'id': setor.id,
                'nome': setor.nome,
                'sub_almoxarifado_id': setor.sub_almoxarifado_id,
                'tipo': 'setor'
            })
        
        return jsonify(locais)
    except Exception as e:
        return jsonify({'error': 'Erro interno do servidor'}), 500

# APIs de Movimentações

@api_bp.route('/movimentacoes', methods=['GET'])
@require_any_level
def get_movimentacoes():
    """Lista movimentações com filtros e paginação"""
    try:
        # Parâmetros de filtro
        tipo = request.args.get('tipo')
        produto = request.args.get('produto')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Query base
        query = db.session.query(MovimentacaoProduto).join(Produto)
        
        # Aplicar filtros
        if tipo:
            query = query.filter(MovimentacaoProduto.tipo_movimentacao == tipo.upper())
        
        if produto:
            query = query.filter(
                db.or_(
                    Produto.nome.ilike(f'%{produto}%'),
                    Produto.codigo.ilike(f'%{produto}%')
                )
            )
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(MovimentacaoProduto.data_movimentacao >= data_inicio_obj)
            except ValueError:
                return jsonify({'error': 'Formato de data inválido para data_inicio'}), 400
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(MovimentacaoProduto.data_movimentacao <= data_fim_obj)
            except ValueError:
                return jsonify({'error': 'Formato de data inválido para data_fim'}), 400
        
        # Ordenar por data mais recente
        query = query.order_by(MovimentacaoProduto.data_movimentacao.desc())
        
        # Aplicar paginação
        paginated = query.paginate(
            page=page,
            per_page=min(100, max(1, per_page)),
            error_out=False
        )
        
        # Preparar dados com informações adicionais
        items = []
        for mov in paginated.items:
            item_data = mov.to_dict()
            
            # Adicionar informações do produto
            item_data['produto_codigo'] = mov.produto.codigo
            item_data['produto_nome'] = mov.produto.nome
            item_data['produto_unidade'] = mov.produto.unidade_medida
            
            # Adicionar nomes dos locais
            if mov.origem_almoxarifado_id:
                almox = Almoxarifado.query.get(mov.origem_almoxarifado_id)
                item_data['origem_nome'] = almox.nome if almox else 'Almoxarifado não encontrado'
            elif mov.origem_sub_almoxarifado_id:
                sub_almox = SubAlmoxarifado.query.get(mov.origem_sub_almoxarifado_id)
                item_data['origem_nome'] = sub_almox.nome if sub_almox else 'Sub-almoxarifado não encontrado'
            elif mov.origem_setor_id:
                setor = Setor.query.get(mov.origem_setor_id)
                item_data['origem_nome'] = setor.nome if setor else 'Setor não encontrado'
            else:
                item_data['origem_nome'] = None
            
            if mov.destino_almoxarifado_id:
                almox = Almoxarifado.query.get(mov.destino_almoxarifado_id)
                item_data['destino_nome'] = almox.nome if almox else 'Almoxarifado não encontrado'
            elif mov.destino_sub_almoxarifado_id:
                sub_almox = SubAlmoxarifado.query.get(mov.destino_sub_almoxarifado_id)
                item_data['destino_nome'] = sub_almox.nome if sub_almox else 'Sub-almoxarifado não encontrado'
            elif mov.destino_setor_id:
                setor = Setor.query.get(mov.destino_setor_id)
                item_data['destino_nome'] = setor.nome if setor else 'Setor não encontrado'
            else:
                item_data['destino_nome'] = None
            
            items.append(item_data)
        
        return jsonify({
            'items': items,
            'pagination': {
                'current_page': paginated.page,
                'per_page': paginated.per_page,
                'total_items': paginated.total,
                'total_pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
        
    except Exception as e:
        print(f"Erro ao listar movimentações: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/movimentacoes/transferencia', methods=['POST'])
@require_any_level
def criar_transferencia():
    """Cria uma transferência entre locais"""
    try:
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['produto_id', 'quantidade', 'origem', 'destino']
        error, status = validate_required_fields(data, required_fields)
        if error:
            return jsonify(error), status
        
        # Validar estrutura de origem e destino
        if not isinstance(data['origem'], dict) or 'tipo' not in data['origem'] or 'id' not in data['origem']:
            return jsonify({'error': 'Estrutura de origem inválida'}), 400
        
        if not isinstance(data['destino'], dict) or 'tipo' not in data['destino'] or 'id' not in data['destino']:
            return jsonify({'error': 'Estrutura de destino inválida'}), 400
        
        # Validar produto
        produto = Produto.query.get(data['produto_id'])
        if not produto:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        # Validar quantidade
        try:
            quantidade = Decimal(str(data['quantidade']))
            if quantidade <= 0:
                return jsonify({'error': 'Quantidade deve ser maior que zero'}), 400
        except:
            return jsonify({'error': 'Quantidade inválida'}), 400
        
        # Validar locais de origem e destino
        origem = data['origem']
        destino = data['destino']
        
        # Verificar se origem e destino são diferentes
        if origem['tipo'] == destino['tipo'] and origem['id'] == destino['id']:
            return jsonify({'error': 'Origem e destino não podem ser iguais'}), 400
        
        # Validar existência dos locais
        def validar_local(local_data, nome_local):
            tipo = local_data['tipo']
            local_id = local_data['id']
            
            if tipo == 'almoxarifado':
                local_obj = Almoxarifado.query.get(local_id)
            elif tipo == 'sub_almoxarifado':
                local_obj = SubAlmoxarifado.query.get(local_id)
            elif tipo == 'setor':
                local_obj = Setor.query.get(local_id)
            else:
                return None, f'Tipo de {nome_local} inválido'
            
            if not local_obj:
                return None, f'{nome_local.capitalize()} não encontrado'
            
            return local_obj, None
        
        origem_obj, erro_origem = validar_local(origem, 'origem')
        if erro_origem:
            return jsonify({'error': erro_origem}), 400
        
        destino_obj, erro_destino = validar_local(destino, 'destino')
        if erro_destino:
            return jsonify({'error': erro_destino}), 400
        
        # Verificar estoque disponível na origem
        estoque_origem = EstoqueProduto.query.filter_by(produto_id=produto.id)
        
        if origem['tipo'] == 'almoxarifado':
            estoque_origem = estoque_origem.filter_by(almoxarifado_id=origem['id'])
        elif origem['tipo'] == 'sub_almoxarifado':
            estoque_origem = estoque_origem.filter_by(sub_almoxarifado_id=origem['id'])
        elif origem['tipo'] == 'setor':
            estoque_origem = estoque_origem.filter_by(setor_id=origem['id'])
        
        estoque_origem = estoque_origem.first()
        
        if not estoque_origem or estoque_origem.quantidade_disponivel < quantidade:
            return jsonify({'error': 'Estoque insuficiente na origem'}), 400
        
        # Criar movimentação de saída
        movimentacao_saida = MovimentacaoProduto(
            produto_id=produto.id,
            tipo_movimentacao='SAIDA',
            quantidade=quantidade,
            data_movimentacao=date.today(),
            motivo=data.get('motivo', 'Transferência'),
            observacoes=data.get('observacoes'),
            usuario_responsavel=current_user.nome_completo if current_user.is_authenticated else 'Sistema'
        )
        
        # Definir origem da movimentação de saída
        if origem['tipo'] == 'almoxarifado':
            movimentacao_saida.origem_almoxarifado_id = origem['id']
        elif origem['tipo'] == 'sub_almoxarifado':
            movimentacao_saida.origem_sub_almoxarifado_id = origem['id']
        elif origem['tipo'] == 'setor':
            movimentacao_saida.origem_setor_id = origem['id']
        
        # Criar movimentação de entrada
        movimentacao_entrada = MovimentacaoProduto(
            produto_id=produto.id,
            tipo_movimentacao='ENTRADA',
            quantidade=quantidade,
            data_movimentacao=date.today(),
            motivo=data.get('motivo', 'Transferência'),
            observacoes=data.get('observacoes'),
            usuario_responsavel=current_user.nome_completo if current_user.is_authenticated else 'Sistema'
        )
        
        # Definir destino da movimentação de entrada
        if destino['tipo'] == 'almoxarifado':
            movimentacao_entrada.destino_almoxarifado_id = destino['id']
        elif destino['tipo'] == 'sub_almoxarifado':
            movimentacao_entrada.destino_sub_almoxarifado_id = destino['id']
        elif destino['tipo'] == 'setor':
            movimentacao_entrada.destino_setor_id = destino['id']
        
        # Atualizar estoque de origem
        estoque_origem.quantidade_disponivel -= quantidade
        
        # Verificar se existe estoque no destino
        estoque_destino = EstoqueProduto.query.filter_by(produto_id=produto.id)
        
        if destino['tipo'] == 'almoxarifado':
            estoque_destino = estoque_destino.filter_by(almoxarifado_id=destino['id'])
        elif destino['tipo'] == 'sub_almoxarifado':
            estoque_destino = estoque_destino.filter_by(sub_almoxarifado_id=destino['id'])
        elif destino['tipo'] == 'setor':
            estoque_destino = estoque_destino.filter_by(setor_id=destino['id'])
        
        estoque_destino = estoque_destino.first()
        
        if estoque_destino:
            # Atualizar estoque existente
            estoque_destino.quantidade_disponivel += quantidade
        else:
            # Criar novo estoque
            estoque_destino = EstoqueProduto(
                produto_id=produto.id,
                quantidade_disponivel=quantidade
            )
            
            if destino['tipo'] == 'almoxarifado':
                estoque_destino.almoxarifado_id = destino['id']
            elif destino['tipo'] == 'sub_almoxarifado':
                estoque_destino.sub_almoxarifado_id = destino['id']
            elif destino['tipo'] == 'setor':
                estoque_destino.setor_id = destino['id']
            
            db.session.add(estoque_destino)
        
        # Salvar no banco
        db.session.add(movimentacao_saida)
        db.session.add(movimentacao_entrada)
        db.session.commit()
        
        return jsonify({
            'message': 'Transferência executada com sucesso',
            'movimentacao_saida_id': movimentacao_saida.id,
            'movimentacao_entrada_id': movimentacao_entrada.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar transferência: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/movimentacoes/distribuicao', methods=['POST'])
@require_manager_or_above
def criar_distribuicao():
    """Cria distribuição de produtos para múltiplos setores"""
    try:
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['produto_id', 'quantidade_total', 'origem', 'setores_destino']
        error, status = validate_required_fields(data, required_fields)
        if error:
            return jsonify(error), status
        
        # Validar estrutura de origem
        if not isinstance(data['origem'], dict) or 'tipo' not in data['origem'] or 'id' not in data['origem']:
            return jsonify({'error': 'Estrutura de origem inválida'}), 400
        
        # Validar setores de destino
        if not isinstance(data['setores_destino'], list) or len(data['setores_destino']) == 0:
            return jsonify({'error': 'Lista de setores de destino inválida'}), 400
        
        # Validar produto
        produto = Produto.query.get(data['produto_id'])
        if not produto:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        # Validar quantidade total
        try:
            quantidade_total = Decimal(str(data['quantidade_total']))
            if quantidade_total <= 0:
                return jsonify({'error': 'Quantidade total deve ser maior que zero'}), 400
        except:
            return jsonify({'error': 'Quantidade total inválida'}), 400
        
        # Validar origem
        origem = data['origem']
        origem_obj, erro_origem = validar_local(origem, 'origem')
        if erro_origem:
            return jsonify({'error': erro_origem}), 400
        
        # Validar setores de destino
        setores_destino = []
        for setor_id in data['setores_destino']:
            setor = Setor.query.get(setor_id)
            if not setor:
                return jsonify({'error': f'Setor {setor_id} não encontrado'}), 400
            setores_destino.append(setor)
        
        # Verificar estoque disponível na origem
        estoque_origem = EstoqueProduto.query.filter_by(produto_id=produto.id)
        
        if origem['tipo'] == 'almoxarifado':
            estoque_origem = estoque_origem.filter_by(almoxarifado_id=origem['id'])
        elif origem['tipo'] == 'sub_almoxarifado':
            estoque_origem = estoque_origem.filter_by(sub_almoxarifado_id=origem['id'])
        
        estoque_origem = estoque_origem.first()
        
        if not estoque_origem or estoque_origem.quantidade_disponivel < quantidade_total:
            return jsonify({'error': 'Estoque insuficiente na origem'}), 400
        
        # Calcular quantidade por setor (distribuição igual)
        quantidade_por_setor = quantidade_total / len(setores_destino)
        
        movimentacoes_criadas = []
        
        # Criar movimentação de saída da origem
        movimentacao_saida = MovimentacaoProduto(
            produto_id=produto.id,
            tipo_movimentacao='SAIDA',
            quantidade=quantidade_total,
            data_movimentacao=date.today(),
            motivo=data.get('motivo', 'Distribuição para setores'),
            observacoes=data.get('observacoes'),
            usuario_responsavel=current_user.nome_completo if current_user.is_authenticated else 'Sistema'
        )
        
        # Definir origem da movimentação de saída
        if origem['tipo'] == 'almoxarifado':
            movimentacao_saida.origem_almoxarifado_id = origem['id']
        elif origem['tipo'] == 'sub_almoxarifado':
            movimentacao_saida.origem_sub_almoxarifado_id = origem['id']
        
        db.session.add(movimentacao_saida)
        movimentacoes_criadas.append(movimentacao_saida)
        
        # Atualizar estoque de origem
        estoque_origem.quantidade_disponivel -= quantidade_total
        
        # Criar movimentações de entrada para cada setor
        for setor in setores_destino:
            movimentacao_entrada = MovimentacaoProduto(
                produto_id=produto.id,
                tipo_movimentacao='ENTRADA',
                quantidade=quantidade_por_setor,
                data_movimentacao=date.today(),
                motivo=data.get('motivo', 'Distribuição para setores'),
                observacoes=data.get('observacoes'),
                usuario_responsavel=current_user.nome_completo if current_user.is_authenticated else 'Sistema',
                destino_setor_id=setor.id
            )
            
            db.session.add(movimentacao_entrada)
            movimentacoes_criadas.append(movimentacao_entrada)
            
            # Verificar se existe estoque no setor
            estoque_setor = EstoqueProduto.query.filter_by(
                produto_id=produto.id,
                setor_id=setor.id
            ).first()
            
            if estoque_setor:
                # Atualizar estoque existente
                estoque_setor.quantidade_disponivel += quantidade_por_setor
            else:
                # Criar novo estoque
                estoque_setor = EstoqueProduto(
                    produto_id=produto.id,
                    quantidade_disponivel=quantidade_por_setor,
                    setor_id=setor.id
                )
                db.session.add(estoque_setor)
        
        # Salvar no banco
        db.session.commit()
        
        return jsonify({
            'message': 'Distribuição executada com sucesso',
            'movimentacoes_criadas': len(movimentacoes_criadas),
            'quantidade_por_setor': float(quantidade_por_setor),
            'setores_atendidos': [setor.nome for setor in setores_destino]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar distribuição: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

def validar_local(local_data, nome_local):
    """Função auxiliar para validar locais"""
    tipo = local_data['tipo']
    local_id = local_data['id']
    
    if tipo == 'central':
        local_obj = Central.query.get(local_id)
    elif tipo == 'almoxarifado':
        local_obj = Almoxarifado.query.get(local_id)
    elif tipo == 'sub_almoxarifado':
        local_obj = SubAlmoxarifado.query.get(local_id)
    elif tipo == 'setor':
        local_obj = Setor.query.get(local_id)
    else:
        return None, f'Tipo de {nome_local} inválido'
    
    if not local_obj:
        return None, f'{nome_local.capitalize()} não encontrado'
    
    return local_obj, None


# ==================== PRODUTOS ====================

@api_bp.route('/produtos', methods=['GET'])
@require_any_level
def get_produtos():
    """Listar produtos com paginação e filtros"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        ativo = request.args.get('ativo', type=bool)
        categoria = request.args.get('categoria', '').strip()
        categoria_id = request.args.get('categoria_id', type=int)
        
        query = Produto.query.options(joinedload(Produto.categoria_obj))
        
        # Aplicar filtro de categoria baseado no usuário logado
        # Apenas usuários não-administradores são limitados às suas categorias
        if (hasattr(current_user, 'nivel_acesso') and 
            current_user.nivel_acesso not in ['super_admin', 'admin_geral']):
            
            categorias_permitidas = current_user.get_categorias_permitidas()
            
            # Se categorias_permitidas é None, o usuário pode ver todas as categorias
            if categorias_permitidas is not None:
                query = query.filter(Produto.categoria_id.in_(categorias_permitidas))
        
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
            
        if categoria:
            query = query.filter(Produto.categoria.ilike(f'%{categoria}%'))
            
        if categoria_id:
            query = query.filter(Produto.categoria_id == categoria_id)
        
        query = query.order_by(Produto.nome)
        
        return jsonify(paginate_query(query, page, per_page))
    except IntegrityError:
        return jsonify({'error': 'Erro interno do servidor'}), 500


# Endpoints para gerenciar categorias específicas dos usuários
@api_bp.route('/usuarios/<int:id>/categorias-especificas', methods=['GET'])
@require_admin_or_above
def get_usuario_categorias_especificas(id):
    """Obter categorias específicas de um usuário"""
    usuario = Usuario.query.get_or_404(id)
    
    categorias = []
    for categoria in usuario.categorias_especificas:
        categorias.append({
            'id': categoria.id,
            'nome': categoria.nome,
            'descricao': categoria.descricao
        })
    
    return jsonify({
        'categorias_especificas': categorias,
        'categoria_id': usuario.categoria_id,
        'categorias_permitidas': usuario.get_categorias_permitidas()
    })


@api_bp.route('/usuarios/<int:id>/categorias-especificas', methods=['POST'])
@require_admin_or_above
def adicionar_categoria_especifica(id):
    """Adicionar categoria específica a um usuário"""
    usuario = Usuario.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'categoria_id' not in data:
        return jsonify({'error': 'categoria_id é obrigatório'}), 400
    
    categoria_id = data['categoria_id']
    categoria = CategoriaProduto.query.get(categoria_id)
    
    if not categoria:
        return jsonify({'error': 'Categoria não encontrada'}), 404
    
    # Verificar se a categoria já está associada
    if categoria in usuario.categorias_especificas:
        return jsonify({'error': 'Categoria já está associada ao usuário'}), 400
    
    try:
        usuario.adicionar_categoria_especifica(categoria_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoria específica adicionada com sucesso',
            'categoria': {
                'id': categoria.id,
                'nome': categoria.nome,
                'descricao': categoria.descricao
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao adicionar categoria específica'}), 500


@api_bp.route('/usuarios/<int:id>/categorias-especificas/<int:categoria_id>', methods=['DELETE'])
@require_admin_or_above
def remover_categoria_especifica(id, categoria_id):
    """Remover categoria específica de um usuário"""
    usuario = Usuario.query.get_or_404(id)
    categoria = CategoriaProduto.query.get_or_404(categoria_id)
    
    # Verificar se a categoria está associada
    if categoria not in usuario.categorias_especificas:
        return jsonify({'error': 'Categoria não está associada ao usuário'}), 400
    
    try:
        usuario.remover_categoria_especifica(categoria_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoria específica removida com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao remover categoria específica'}), 500

@api_bp.route('/produtos/<int:id>', methods=['GET'])
@require_any_level
def get_produto(id):
    """Obter produto específico com estoque"""
    produto = Produto.query.get_or_404(id)
    
    # Buscar estoque por nível hierárquico
    estoque_query = EstoqueProduto.query.filter_by(produto_id=id, ativo=True)
    estoque_data = []
    
    for estoque in estoque_query:
        item = estoque.to_dict()
        # Adicionar informações do local
        if estoque.almoxarifado_id:
            almox = Almoxarifado.query.get(estoque.almoxarifado_id)
            item['local'] = {'tipo': 'Almoxarifado', 'nome': almox.nome, 'id': almox.id}
        elif estoque.sub_almoxarifado_id:
            sub_almox = SubAlmoxarifado.query.get(estoque.sub_almoxarifado_id)
            item['local'] = {'tipo': 'SubAlmoxarifado', 'nome': sub_almox.nome, 'id': sub_almox.id}
        elif estoque.setor_id:
            setor = Setor.query.get(estoque.setor_id)
            item['local'] = {'tipo': 'Setor', 'nome': setor.nome, 'id': setor.id}
        
        estoque_data.append(item)
    
    result = produto.to_dict()
    result['estoque'] = estoque_data
    
    return jsonify(result)

@api_bp.route('/produtos/gerar-codigo', methods=['POST'])
@require_manager_or_above
def gerar_codigo_produto():
    """Gerar código automático para produto"""
    try:
        data = request.get_json()
        central_id = data.get('central_id')
        categoria = data.get('categoria', '')
        
        if not central_id:
            return jsonify({'success': False, 'message': 'Central é obrigatória'}), 400
        
        # Buscar central para obter prefixo
        central = Central.query.get(central_id)
        if not central:
            return jsonify({'success': False, 'message': 'Central não encontrada'}), 404
        
        # Gerar código baseado na central e categoria
        prefixo_central = central.nome[:3].upper()
        
        # Prefixo da categoria (primeiras 2 letras)
        prefixo_categoria = ''
        if categoria:
            # Mapear categorias para códigos
            categorias_map = {
                'Material Hospitalar': 'MH',
                'Odontológico': 'OD', 
                'Injetáveis': 'IN',
                'Medicamentos': 'MD',
                'Limpeza': 'LP',
                'Gênero Expediente': 'GE',
                'Gráfico': 'GR',
                'Equipamentos': 'EQ',
                'Laboratório': 'LB'
            }
            prefixo_categoria = categorias_map.get(categoria, categoria[:2].upper())
        
        # Buscar último número sequencial
        ultimo_produto = Produto.query.filter(
            Produto.codigo.like(f'{prefixo_central}%')
        ).order_by(Produto.codigo.desc()).first()
        
        proximo_numero = 1
        if ultimo_produto:
            try:
                # Extrair número do código (últimos 4 dígitos)
                numero_atual = int(ultimo_produto.codigo[-4:])
                proximo_numero = numero_atual + 1
            except:
                proximo_numero = 1
        
        # Gerar código: CENTRAL + CATEGORIA + NUMERO (4 dígitos)
        codigo = f"{prefixo_central}{prefixo_categoria}{proximo_numero:04d}"
        
        # Verificar se código já existe (segurança)
        while Produto.query.filter_by(codigo=codigo).first():
            proximo_numero += 1
            codigo = f"{prefixo_central}{prefixo_categoria}{proximo_numero:04d}"
        
        return jsonify({
            'success': True,
            'codigo': codigo
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/produtos', methods=['POST'])
@require_manager_or_above
def create_produto():
    """Criar novo produto"""
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['nome', 'codigo', 'central_id'])
    if error:
        return jsonify(error), status
    
    # Validações específicas
    nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=200)
    if nome_error:
        return jsonify({'error': nome_error}), 400
        
    codigo_error = validate_text_field(data['codigo'], 'Código', min_length=1, max_length=50)
    if codigo_error:
        return jsonify({'error': codigo_error}), 400
    
    # Validar central_id
    try:
        central_id = int(data['central_id'])
        central = Central.query.filter_by(id=central_id, ativo=True).first()
        if not central:
            return jsonify({'error': 'Central não encontrada ou inativa'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'ID da central deve ser um número válido'}), 400
    
    # Verificar duplicatas
    existing_codigo = Produto.query.filter_by(codigo=data['codigo'].strip()).first()
    if existing_codigo:
        return jsonify({'error': 'Já existe um produto com este código'}), 400
    
    existing_nome = Produto.query.filter(Produto.nome.ilike(data['nome'].strip())).first()
    if existing_nome:
        return jsonify({'error': 'Já existe um produto com este nome'}), 400
    
    produto = Produto(
        nome=data['nome'].strip(),
        codigo=data['codigo'].strip(),
        descricao=data.get('descricao', '').strip(),
        categoria=data.get('categoria', '').strip(),
        unidade_medida=data.get('unidade_medida', 'UN').strip(),
        central_id=central_id,
        categoria_id=data.get('categoria_id'),
        ativo=data.get('ativo', True)
    )
    
    try:
        db.session.add(produto)
        db.session.commit()
        return jsonify(produto.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar produto: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/produtos/<int:id>', methods=['PUT'])
@require_manager_or_above
def update_produto(id):
    """Atualizar produto"""
    produto = Produto.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    # Validações
    if 'nome' in data:
        nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=200)
        if nome_error:
            return jsonify({'error': nome_error}), 400
        
        existing = Produto.query.filter(
            Produto.nome.ilike(data['nome'].strip()),
            Produto.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe um produto com este nome'}), 400
        
        produto.nome = data['nome'].strip()
    
    if 'codigo' in data:
        codigo_error = validate_text_field(data['codigo'], 'Código', min_length=1, max_length=50)
        if codigo_error:
            return jsonify({'error': codigo_error}), 400
        
        existing = Produto.query.filter(
            Produto.codigo == data['codigo'].strip(),
            Produto.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe um produto com este código'}), 400
        
        produto.codigo = data['codigo'].strip()
    
    if 'descricao' in data:
        produto.descricao = data['descricao'].strip()
    
    if 'categoria' in data:
        produto.categoria = data['categoria'].strip()
        
    if 'categoria_id' in data:
        produto.categoria_id = data['categoria_id']
    
    if 'unidade_medida' in data:
        produto.unidade_medida = data['unidade_medida'].strip()
    
    if 'ativo' in data:
        produto.ativo = bool(data['ativo'])
    
    try:
        db.session.commit()
        return jsonify(produto.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar produto: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/produtos/<int:id>', methods=['DELETE'])
@require_manager_or_above
def delete_produto(id):
    """Excluir produto (soft delete)"""
    produto = Produto.query.get_or_404(id)
    
    # Verificar se há estoque
    estoque_existente = EstoqueProduto.query.filter_by(produto_id=id, ativo=True).filter(
        EstoqueProduto.quantidade > 0
    ).first()
    
    if estoque_existente:
        return jsonify({'error': 'Não é possível excluir produto com estoque'}), 400
    
    try:
        produto.ativo = False
        db.session.commit()
        return jsonify({'message': 'Produto excluído com sucesso'})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500


# ==================== RECEBIMENTO DE PRODUTOS ====================

@api_bp.route('/produtos/<int:id>/estoque', methods=['GET'])
@require_any_level
def get_produto_estoque(id):
    """Buscar estoque de um produto específico"""
    produto = Produto.query.get_or_404(id)
    
    # Buscar todos os estoques do produto
    estoques = EstoqueProduto.query.filter_by(produto_id=id, ativo=True).all()
    
    estoque_data = []
    total_quantidade = 0
    total_reservada = 0
    total_disponivel = 0
    
    for estoque in estoques:
        estoque_info = estoque.to_dict()
        
        # Adicionar informações do local e tipo (Central não é mais um local de estoque)
        if estoque.almoxarifado_id:
            almox = Almoxarifado.query.get(estoque.almoxarifado_id)
            estoque_info['nome_local'] = almox.nome if almox else 'Almoxarifado não encontrado'
            estoque_info['tipo'] = 'almoxarifado'
            estoque_info['local_id'] = estoque.almoxarifado_id
        elif estoque.sub_almoxarifado_id:
            sub_almox = SubAlmoxarifado.query.get(estoque.sub_almoxarifado_id)
            estoque_info['nome_local'] = sub_almox.nome if sub_almox else 'Sub-almoxarifado não encontrado'
            estoque_info['tipo'] = 'sub_almoxarifado'
            estoque_info['local_id'] = estoque.sub_almoxarifado_id
        elif estoque.setor_id:
            setor = Setor.query.get(estoque.setor_id)
            estoque_info['nome_local'] = setor.nome if setor else 'Setor não encontrado'
            estoque_info['tipo'] = 'setor'
            estoque_info['local_id'] = estoque.setor_id
        else:
            estoque_info['nome_local'] = 'Local não definido'
            estoque_info['tipo'] = 'indefinido'
            estoque_info['local_id'] = None
        
        estoque_data.append(estoque_info)
        total_quantidade += float(estoque.quantidade or 0)
        total_reservada += float(estoque.quantidade_reservada or 0)
        total_disponivel += float(estoque.quantidade_disponivel or 0)
    
    return jsonify({
        'produto_id': id,
        'produto_nome': produto.nome,
        'produto_codigo': produto.codigo,
        'estoques': estoque_data,
        'resumo': {
            'total_quantidade': total_quantidade,
            'total_reservada': total_reservada,
            'total_disponivel': total_disponivel,
            'locais_com_estoque': len(estoque_data)
        }
    })

@api_bp.route('/produtos/<int:id>/lotes', methods=['GET'])
@require_any_level
def get_produto_lotes(id):
    """Buscar lotes de um produto específico"""
    produto = Produto.query.get_or_404(id)
    
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Filtros
    ativo = request.args.get('ativo', type=bool)
    vencimento_proximo = request.args.get('vencimento_proximo', type=bool)
    
    query = LoteProduto.query.filter_by(produto_id=id)
    
    if ativo is not None:
        query = query.filter(LoteProduto.ativo == ativo)
    
    if vencimento_proximo:
        from datetime import datetime, timedelta
        data_limite = datetime.now().date() + timedelta(days=30)
        query = query.filter(LoteProduto.data_vencimento <= data_limite)
    
    query = query.order_by(LoteProduto.data_vencimento.asc(), LoteProduto.numero_lote)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/produtos/<int:id>/movimentacoes', methods=['GET'])
@require_any_level
def get_produto_movimentacoes(id):
    """Buscar movimentações de um produto específico"""
    produto = Produto.query.get_or_404(id)
    
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    limit = request.args.get('limit', type=int)
    
    # Filtros
    tipo = request.args.get('tipo')  # ENTRADA, SAIDA, TRANSFERENCIA
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = MovimentacaoProduto.query.filter_by(produto_id=id)
    
    if tipo:
        query = query.filter(MovimentacaoProduto.tipo_movimentacao == tipo.upper())
    
    if data_inicio:
        try:
            from datetime import datetime
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(MovimentacaoProduto.data_movimentacao >= data_inicio_dt)
        except ValueError:
            pass
    
    if data_fim:
        try:
            from datetime import datetime
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(MovimentacaoProduto.data_movimentacao <= data_fim_dt)
        except ValueError:
            pass
    
    query = query.order_by(MovimentacaoProduto.data_movimentacao.desc())
    
    # Se limit foi especificado, usar limit em vez de paginação
    if limit:
        movimentacoes = query.limit(limit).all()
        return jsonify({
            'items': [mov.to_dict() for mov in movimentacoes],
            'total': query.count(),
            'limit': limit
        })
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/produtos/<int:produto_id>/almoxarifados', methods=['GET'])
@require_any_level
def get_produto_almoxarifados(produto_id):
    """Buscar almoxarifados disponíveis para recebimento do produto"""
    try:
        produto = Produto.query.get_or_404(produto_id)
        
        # Buscar almoxarifados da central do produto
        almoxarifados = Almoxarifado.query.filter_by(
            central_id=produto.central_id,
            ativo=True
        ).order_by(Almoxarifado.nome).all()
        
        almoxarifados_data = []
        for almox in almoxarifados:
            almox_dict = almox.to_dict()
            # Adicionar informação se já tem estoque neste almoxarifado
            estoque_existente = EstoqueProduto.query.filter_by(
                produto_id=produto_id,
                almoxarifado_id=almox.id,
                ativo=True
            ).first()
            
            almox_dict['tem_estoque'] = estoque_existente is not None
            if estoque_existente:
                almox_dict['quantidade_atual'] = float(estoque_existente.quantidade_disponivel or 0)
            else:
                almox_dict['quantidade_atual'] = 0
                
            almoxarifados_data.append(almox_dict)
        
        # Buscar nome da central
        from models.hierarchy import Central
        central = Central.query.get(produto.central_id)
        
        return jsonify({
            'success': True,
            'produto_id': produto_id,
            'produto_nome': produto.nome,
            'central_id': produto.central_id,
            'central_nome': central.nome if central else None,
            'almoxarifados': almoxarifados_data,
            'total': len(almoxarifados_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/produtos/<int:produto_id>/recebimento', methods=['POST'])
@require_any_level
def receber_produto(produto_id):
    """Registrar recebimento de produto com lote"""
    produto = Produto.query.get_or_404(produto_id)
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['quantidade', 'almoxarifado_id'])
    if error:
        return jsonify(error), status
    
    # Validar quantidade
    try:
        quantidade = Decimal(str(data['quantidade']))
        if quantidade <= 0:
            return jsonify({'error': 'Quantidade deve ser maior que zero'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Quantidade inválida'}), 400
    
    # Validar almoxarifado
    almoxarifado_id = data['almoxarifado_id']
    almoxarifado = Almoxarifado.query.get_or_404(almoxarifado_id)
    
    # Verificar se o almoxarifado pertence à mesma central do produto
    if almoxarifado.central_id != produto.central_id:
        return jsonify({'error': 'Almoxarifado não pertence à central do produto'}), 400
    
    try:
        # Criar ou atualizar estoque
        estoque = EstoqueProduto.query.filter_by(
            produto_id=produto_id,
            almoxarifado_id=almoxarifado_id
        ).first()
        
        if not estoque:
            estoque = EstoqueProduto(
                produto_id=produto_id,
                almoxarifado_id=almoxarifado_id,
                quantidade=0,
                quantidade_disponivel=0
            )
            db.session.add(estoque)
        
        # Atualizar estoque
        estoque.quantidade += quantidade
        estoque.quantidade_disponivel += quantidade
        estoque.ativo = True
        
        # Fazer flush para obter o ID do estoque
        db.session.flush()
        
        # Criar lote (sempre criamos um lote para rastreabilidade)
        lote_numero = data.get('lote') if data.get('lote') else f'LOTE-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        lote_data = {
            'produto_id': produto_id,
            'estoque_id': estoque.id,  # Agora temos o ID do estoque
            'numero_lote': lote_numero,
            'quantidade_inicial': quantidade,
            'quantidade_atual': quantidade
        }
        
        # Adicionar campos opcionais do lote
        if 'data_vencimento' in data and data['data_vencimento']:
            try:
                lote_data['data_vencimento'] = datetime.strptime(data['data_vencimento'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Data de vencimento inválida (formato: YYYY-MM-DD)'}), 400
        
        if 'data_fabricacao' in data and data['data_fabricacao']:
            try:
                lote_data['data_fabricacao'] = datetime.strptime(data['data_fabricacao'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Data de fabricação inválida (formato: YYYY-MM-DD)'}), 400
        
        if 'preco_unitario' in data and data['preco_unitario'] is not None:
            try:
                lote_data['preco_unitario'] = float(data['preco_unitario'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Preço unitário inválido'}), 400
        
        if 'fornecedor' in data and data['fornecedor']:
            lote_data['fornecedor'] = data['fornecedor'].strip()
        
        if 'nota_fiscal' in data and data['nota_fiscal']:
            lote_data['nota_fiscal'] = data['nota_fiscal'].strip()
            
        lote = LoteProduto(**lote_data)
        db.session.add(lote)
        db.session.flush()  # Flush para obter o ID do lote
        
        # Registrar movimentação
        movimentacao_data = {
            'produto_id': produto_id,
            'tipo_movimentacao': 'ENTRADA',
            'quantidade': quantidade,
            'motivo': 'RECEBIMENTO',
            'observacoes': data.get('observacoes', ''),
            'usuario_responsavel': current_user.nome_completo if current_user.is_authenticated else 'Sistema',
            'lote_id': lote.id
        }
        
        # Associar movimentação ao almoxarifado
        movimentacao_data['destino_almoxarifado_id'] = almoxarifado_id
        
        movimentacao = MovimentacaoProduto(**movimentacao_data)
        db.session.add(movimentacao)
        
        db.session.commit()
        
        result = {
            'message': 'Recebimento registrado com sucesso',
            'estoque': estoque.to_dict(),
            'movimentacao': movimentacao.to_dict()
        }
        
        if lote:
            result['lote'] = lote.to_dict()
        
        return jsonify(result), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"ERRO NO RECEBIMENTO: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500


# ==================== ESTOQUE ====================

@api_bp.route('/estoque', methods=['GET'])
@require_any_level
def get_estoque():
    """Listar estoque com filtros"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        produto_id = request.args.get('produto_id', type=int)
        local_tipo = request.args.get('local_tipo', '').upper()
        local_id = request.args.get('local_id', type=int)
        apenas_com_estoque = request.args.get('apenas_com_estoque', False, type=bool)
        
        query = EstoqueProduto.query.filter_by(ativo=True).options(
            joinedload(EstoqueProduto.produto).joinedload(Produto.categoria_obj)
        )
        query = query.join(Produto).filter(Produto.ativo == True)
        
        # Aplicar filtros de escopo baseados no usuário logado
        query = ScopeFilter.filter_estoque(query)
        
        if produto_id:
            query = query.filter(EstoqueProduto.produto_id == produto_id)
        
        if local_tipo and local_id:
            if local_tipo == 'ALMOXARIFADO':
                query = query.filter(EstoqueProduto.almoxarifado_id == local_id)
            elif local_tipo == 'SUBALMOXARIFADO':
                query = query.filter(EstoqueProduto.sub_almoxarifado_id == local_id)
            elif local_tipo == 'SETOR':
                query = query.filter(EstoqueProduto.setor_id == local_id)
        
        if apenas_com_estoque:
            query = query.filter(EstoqueProduto.quantidade > 0)
        
        query = query.order_by(Produto.nome)
        
        return jsonify(paginate_query(query, page, per_page))
    except Exception as e:
        import traceback
        print(f"Erro na API de estoque: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/centrais/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_central(id):
    """Atualizar central com validações"""
    central = Central.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    if 'nome' in data:
        nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
        if nome_error:
            return jsonify({'error': nome_error}), 400
        
        existing = Central.query.filter(
            Central.nome.ilike(data['nome'].strip()),
            Central.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe outra central com este nome'}), 400
        
        central.nome = data['nome'].strip()
    
    if 'descricao' in data:
        descricao = data['descricao'].strip() if data['descricao'] else ''
        if descricao:
            desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
            if desc_error:
                return jsonify({'error': desc_error}), 400
        central.descricao = descricao
    
    if 'ativo' in data:
        if not isinstance(data['ativo'], bool):
            return jsonify({'error': 'Campo ativo deve ser verdadeiro ou falso'}), 400
        central.ativo = data['ativo']
    
    try:
        db.session.commit()
        return jsonify(central.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar central: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/centrais/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_central(id):
    """Excluir central com verificações de integridade"""
    central = Central.query.options(joinedload(Central.almoxarifados)).get_or_404(id)
    
    if central.almoxarifados:
        almox_count = len(central.almoxarifados)
        return jsonify({
            'error': f'Não é possível excluir central com {almox_count} almoxarifado(s) vinculado(s). '
                    'Remova ou transfira os almoxarifados primeiro.'
        }), 400
    
    try:
        db.session.delete(central)
        db.session.commit()
        return jsonify({'message': 'Central excluída com sucesso'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir central: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ============================================================================
# ROTAS PARA ALMOXARIFADO
# ============================================================================

@api_bp.route('/almoxarifados', methods=['GET'])
@require_any_level
def get_almoxarifados():
    """Listar todos os almoxarifados com paginação e filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    central_id = request.args.get('central_id', type=int)
    ativo = request.args.get('ativo', type=bool)
    search = request.args.get('search', '').strip()
    
    query = Almoxarifado.query.options(
        joinedload(Almoxarifado.central),
        joinedload(Almoxarifado.sub_almoxarifados)
    )
    
    # Aplicar filtros de escopo baseados no usuário logado
    query = ScopeFilter.filter_almoxarifados(query)
    
    if central_id:
        query = query.filter(Almoxarifado.central_id == central_id)
    
    if ativo is not None:
        query = query.filter(Almoxarifado.ativo == ativo)
    
    if search:
        query = query.filter(Almoxarifado.nome.ilike(f'%{search}%'))
    
    query = query.order_by(Almoxarifado.nome)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/almoxarifados/<int:id>', methods=['GET'])
@require_any_level
def get_almoxarifado(id):
    """Buscar almoxarifado por ID com eager loading"""
    almoxarifado = Almoxarifado.query.options(
        joinedload(Almoxarifado.central),
        joinedload(Almoxarifado.sub_almoxarifados).joinedload(SubAlmoxarifado.setores)
    ).get_or_404(id)
    return jsonify(almoxarifado.to_dict())

@api_bp.route('/almoxarifados', methods=['POST'])
@require_admin_or_above
def create_almoxarifado():
    """Criar novo almoxarifado com validações robustas"""
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['nome', 'central_id'])
    if error:
        return jsonify(error), status
    
    nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
    if nome_error:
        return jsonify({'error': nome_error}), 400
    
    descricao = data.get('descricao', '').strip()
    if descricao:
        desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
        if desc_error:
            return jsonify({'error': desc_error}), 400
    
    if not isinstance(data['central_id'], int) or data['central_id'] <= 0:
        return jsonify({'error': 'central_id deve ser um número inteiro positivo'}), 400
    
    central = Central.query.get(data['central_id'])
    if not central:
        return jsonify({'error': 'Central não encontrada'}), 404
    
    existing = Almoxarifado.query.filter(
        Almoxarifado.nome.ilike(data['nome'].strip()),
        Almoxarifado.central_id == data['central_id']
    ).first()
    if existing:
        return jsonify({'error': 'Já existe um almoxarifado com este nome nesta central'}), 400
    
    almoxarifado = Almoxarifado(
        nome=data['nome'].strip(),
        descricao=descricao,
        central_id=data['central_id'],
        ativo=data.get('ativo', True)
    )
    
    try:
        db.session.add(almoxarifado)
        db.session.commit()
        return jsonify(almoxarifado.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/almoxarifados/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_almoxarifado(id):
    """Atualizar almoxarifado com validações"""
    almoxarifado = Almoxarifado.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    if 'nome' in data:
        nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
        if nome_error:
            return jsonify({'error': nome_error}), 400
        
        existing = Almoxarifado.query.filter(
            Almoxarifado.nome.ilike(data['nome'].strip()),
            Almoxarifado.central_id == almoxarifado.central_id,
            Almoxarifado.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe outro almoxarifado com este nome nesta central'}), 400
        
        almoxarifado.nome = data['nome'].strip()
    
    if 'descricao' in data:
        descricao = data['descricao'].strip() if data['descricao'] else ''
        if descricao:
            desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
            if desc_error:
                return jsonify({'error': desc_error}), 400
        almoxarifado.descricao = descricao
    
    if 'central_id' in data:
        if not isinstance(data['central_id'], int) or data['central_id'] <= 0:
            return jsonify({'error': 'central_id deve ser um número inteiro positivo'}), 400
        
        central = Central.query.get(data['central_id'])
        if not central:
            return jsonify({'error': 'Central não encontrada'}), 404
        
        almoxarifado.central_id = data['central_id']
    
    if 'ativo' in data:
        if not isinstance(data['ativo'], bool):
            return jsonify({'error': 'Campo ativo deve ser verdadeiro ou falso'}), 400
        almoxarifado.ativo = data['ativo']
    
    try:
        db.session.commit()
        return jsonify(almoxarifado.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/almoxarifados/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_almoxarifado(id):
    """Excluir almoxarifado com verificações de integridade"""
    almoxarifado = Almoxarifado.query.options(
        joinedload(Almoxarifado.sub_almoxarifados)
    ).get_or_404(id)
    
    if almoxarifado.sub_almoxarifados:
        sub_count = len(almoxarifado.sub_almoxarifados)
        return jsonify({
            'error': f'Não é possível excluir almoxarifado com {sub_count} sub-almoxarifado(s) vinculado(s). '
                    'Remova ou transfira os sub-almoxarifados primeiro.'
        }), 400
    
    try:
        db.session.delete(almoxarifado)
        db.session.commit()
        return jsonify({'message': 'Almoxarifado excluído com sucesso'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ============================================================================
# ROTAS PARA SUB-ALMOXARIFADO
# ============================================================================

@api_bp.route('/sub-almoxarifados', methods=['GET'])
@require_any_level
def get_sub_almoxarifados():
    """Listar todos os sub-almoxarifados com paginação e filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    almoxarifado_id = request.args.get('almoxarifado_id', type=int)
    ativo = request.args.get('ativo', type=bool)
    search = request.args.get('search', '').strip()
    
    query = SubAlmoxarifado.query.options(
        joinedload(SubAlmoxarifado.almoxarifado).joinedload(Almoxarifado.central),
        joinedload(SubAlmoxarifado.setores)
    )
    
    # Aplicar filtros de escopo baseados no usuário logado
    query = ScopeFilter.filter_sub_almoxarifados(query)
    
    if almoxarifado_id:
        query = query.filter(SubAlmoxarifado.almoxarifado_id == almoxarifado_id)
    
    if ativo is not None:
        query = query.filter(SubAlmoxarifado.ativo == ativo)
    
    if search:
        query = query.filter(SubAlmoxarifado.nome.ilike(f'%{search}%'))
    
    query = query.order_by(SubAlmoxarifado.nome)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/sub-almoxarifados/<int:id>', methods=['GET'])
@require_any_level
def get_sub_almoxarifado(id):
    """Buscar sub-almoxarifado por ID com eager loading"""
    sub_almoxarifado = SubAlmoxarifado.query.options(
        joinedload(SubAlmoxarifado.almoxarifado).joinedload(Almoxarifado.central),
        joinedload(SubAlmoxarifado.setores)
    ).get_or_404(id)
    return jsonify(sub_almoxarifado.to_dict())

@api_bp.route('/sub-almoxarifados', methods=['POST'])
@require_admin_or_above
def create_sub_almoxarifado():
    """Criar novo sub-almoxarifado com validações robustas"""
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['nome', 'almoxarifado_id'])
    if error:
        return jsonify(error), status
    
    nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
    if nome_error:
        return jsonify({'error': nome_error}), 400
    
    descricao = data.get('descricao', '').strip()
    if descricao:
        desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
        if desc_error:
            return jsonify({'error': desc_error}), 400
    
    if not isinstance(data['almoxarifado_id'], int) or data['almoxarifado_id'] <= 0:
        return jsonify({'error': 'almoxarifado_id deve ser um número inteiro positivo'}), 400
    
    almoxarifado = Almoxarifado.query.get(data['almoxarifado_id'])
    if not almoxarifado:
        return jsonify({'error': 'Almoxarifado não encontrado'}), 404
    
    existing = SubAlmoxarifado.query.filter(
        SubAlmoxarifado.nome.ilike(data['nome'].strip()),
        SubAlmoxarifado.almoxarifado_id == data['almoxarifado_id']
    ).first()
    if existing:
        return jsonify({'error': 'Já existe um sub-almoxarifado com este nome neste almoxarifado'}), 400
    
    sub_almoxarifado = SubAlmoxarifado(
        nome=data['nome'].strip(),
        descricao=descricao,
        almoxarifado_id=data['almoxarifado_id'],
        ativo=data.get('ativo', True)
    )
    
    try:
        db.session.add(sub_almoxarifado)
        db.session.commit()
        return jsonify(sub_almoxarifado.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar sub-almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/sub-almoxarifados/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_sub_almoxarifado(id):
    """Atualizar sub-almoxarifado com validações"""
    sub_almoxarifado = SubAlmoxarifado.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    if 'nome' in data:
        nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
        if nome_error:
            return jsonify({'error': nome_error}), 400
        
        existing = SubAlmoxarifado.query.filter(
            SubAlmoxarifado.nome.ilike(data['nome'].strip()),
            SubAlmoxarifado.almoxarifado_id == sub_almoxarifado.almoxarifado_id,
            SubAlmoxarifado.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe outro sub-almoxarifado com este nome neste almoxarifado'}), 400
        
        sub_almoxarifado.nome = data['nome'].strip()
    
    if 'descricao' in data:
        descricao = data['descricao'].strip() if data['descricao'] else ''
        if descricao:
            desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
            if desc_error:
                return jsonify({'error': desc_error}), 400
        sub_almoxarifado.descricao = descricao
    
    if 'almoxarifado_id' in data:
        if not isinstance(data['almoxarifado_id'], int) or data['almoxarifado_id'] <= 0:
            return jsonify({'error': 'almoxarifado_id deve ser um número inteiro positivo'}), 400
        
        almoxarifado = Almoxarifado.query.get(data['almoxarifado_id'])
        if not almoxarifado:
            return jsonify({'error': 'Almoxarifado não encontrado'}), 404
        
        sub_almoxarifado.almoxarifado_id = data['almoxarifado_id']
    
    if 'ativo' in data:
        if not isinstance(data['ativo'], bool):
            return jsonify({'error': 'Campo ativo deve ser verdadeiro ou falso'}), 400
        sub_almoxarifado.ativo = data['ativo']
    
    try:
        db.session.commit()
        return jsonify(sub_almoxarifado.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar sub-almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/sub-almoxarifados/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_sub_almoxarifado(id):
    """Excluir sub-almoxarifado com verificações de integridade"""
    sub_almoxarifado = SubAlmoxarifado.query.options(
        joinedload(SubAlmoxarifado.setores)
    ).get_or_404(id)
    
    if sub_almoxarifado.setores:
        setor_count = len(sub_almoxarifado.setores)
        return jsonify({
            'error': f'Não é possível excluir sub-almoxarifado com {setor_count} setor(es) vinculado(s). '
                    'Remova ou transfira os setores primeiro.'
        }), 400
    
    try:
        db.session.delete(sub_almoxarifado)
        db.session.commit()
        return jsonify({'message': 'Sub-almoxarifado excluído com sucesso'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir sub-almoxarifado: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ============================================================================
# ROTAS PARA SETOR
# ============================================================================

@api_bp.route('/setores', methods=['GET'])
@require_any_level
def get_setores():
    """Listar todos os setores com paginação e filtros"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sub_almoxarifado_id = request.args.get('sub_almoxarifado_id', type=int)
    ativo = request.args.get('ativo', type=bool)
    search = request.args.get('search', '').strip()
    
    query = Setor.query.options(
        joinedload(Setor.sub_almoxarifado)
        .joinedload(SubAlmoxarifado.almoxarifado)
        .joinedload(Almoxarifado.central)
    )
    
    # Aplicar filtros de escopo baseados no usuário logado
    query = ScopeFilter.filter_setores(query)
    
    if sub_almoxarifado_id:
        query = query.filter(Setor.sub_almoxarifado_id == sub_almoxarifado_id)
    
    if ativo is not None:
        query = query.filter(Setor.ativo == ativo)
    
    if search:
        query = query.filter(Setor.nome.ilike(f'%{search}%'))
    
    query = query.order_by(Setor.nome)
    
    return jsonify(paginate_query(query, page, per_page))

@api_bp.route('/setores/<int:id>', methods=['GET'])
@require_any_level
def get_setor(id):
    """Buscar setor por ID com eager loading"""
    setor = Setor.query.options(
        joinedload(Setor.sub_almoxarifado)
        .joinedload(SubAlmoxarifado.almoxarifado)
        .joinedload(Almoxarifado.central)
    ).get_or_404(id)
    return jsonify(setor.to_dict())

@api_bp.route('/setores', methods=['POST'])
@require_admin_or_above
def create_setor():
    """Criar novo setor com validações robustas"""
    data = request.get_json()
    
    error, status = validate_required_fields(data, ['nome', 'sub_almoxarifado_id'])
    if error:
        return jsonify(error), status
    
    nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
    if nome_error:
        return jsonify({'error': nome_error}), 400
    
    descricao = data.get('descricao', '').strip()
    if descricao:
        desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
        if desc_error:
            return jsonify({'error': desc_error}), 400
    
    if not isinstance(data['sub_almoxarifado_id'], int) or data['sub_almoxarifado_id'] <= 0:
        return jsonify({'error': 'sub_almoxarifado_id deve ser um número inteiro positivo'}), 400
    
    sub_almoxarifado = SubAlmoxarifado.query.get(data['sub_almoxarifado_id'])
    if not sub_almoxarifado:
        return jsonify({'error': 'Sub-almoxarifado não encontrado'}), 404
    
    existing = Setor.query.filter(
        Setor.nome.ilike(data['nome'].strip()),
        Setor.sub_almoxarifado_id == data['sub_almoxarifado_id']
    ).first()
    if existing:
        return jsonify({'error': 'Já existe um setor com este nome neste sub-almoxarifado'}), 400
    
    setor = Setor(
        nome=data['nome'].strip(),
        descricao=descricao,
        sub_almoxarifado_id=data['sub_almoxarifado_id'],
        ativo=data.get('ativo', True)
    )
    
    try:
        db.session.add(setor)
        db.session.commit()
        return jsonify(setor.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar setor: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/setores/<int:id>', methods=['PUT'])
@require_admin_or_above
def update_setor(id):
    """Atualizar setor com validações"""
    setor = Setor.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    if 'nome' in data:
        nome_error = validate_text_field(data['nome'], 'Nome', min_length=2, max_length=100)
        if nome_error:
            return jsonify({'error': nome_error}), 400
        
        existing = Setor.query.filter(
            Setor.nome.ilike(data['nome'].strip()),
            Setor.sub_almoxarifado_id == setor.sub_almoxarifado_id,
            Setor.id != id
        ).first()
        if existing:
            return jsonify({'error': 'Já existe outro setor com este nome neste sub-almoxarifado'}), 400
        
        setor.nome = data['nome'].strip()
    
    if 'descricao' in data:
        descricao = data['descricao'].strip() if data['descricao'] else ''
        if descricao:
            desc_error = validate_text_field(descricao, 'Descrição', min_length=0, max_length=500)
            if desc_error:
                return jsonify({'error': desc_error}), 400
        setor.descricao = descricao
    
    if 'sub_almoxarifado_id' in data:
        if not isinstance(data['sub_almoxarifado_id'], int) or data['sub_almoxarifado_id'] <= 0:
            return jsonify({'error': 'sub_almoxarifado_id deve ser um número inteiro positivo'}), 400
        
        sub_almoxarifado = SubAlmoxarifado.query.get(data['sub_almoxarifado_id'])
        if not sub_almoxarifado:
            return jsonify({'error': 'Sub-almoxarifado não encontrado'}), 404
        
        setor.sub_almoxarifado_id = data['sub_almoxarifado_id']
    
    if 'ativo' in data:
        if not isinstance(data['ativo'], bool):
            return jsonify({'error': 'Campo ativo deve ser verdadeiro ou falso'}), 400
        setor.ativo = data['ativo']
    
    try:
        db.session.commit()
        return jsonify(setor.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar setor: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@api_bp.route('/setores/<int:id>', methods=['DELETE'])
@require_admin_or_above
def delete_setor(id):
    """Excluir setor"""
    setor = Setor.query.get_or_404(id)
    
    try:
        db.session.delete(setor)
        db.session.commit()
        return jsonify({'message': 'Setor excluído com sucesso'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir setor: violação de integridade'}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500