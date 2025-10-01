from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from models.produto import Produto, EstoqueProduto, LoteProduto, MovimentacaoProduto
from models.usuario import Usuario
from models.categoria import CategoriaProduto
from extensions import db
from auth import (require_any_level, require_manager_or_above, require_admin_or_above, 
                  ScopeFilter)
from config.ui_blocks import get_ui_blocks_config

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@require_any_level
def index():
    """Página inicial"""
    return render_template('index.html')

@main_bp.route('/health/mongo')
def health_mongo():
    """Healthcheck simples para verificar conectividade com MongoDB."""
    from extensions import mongo_client, mongo_db
    try:
        if mongo_client:
            mongo_client.admin.command('ping')
            return jsonify({'mongo_ok': True, 'db': mongo_db.name}), 200
        return jsonify({'mongo_ok': False, 'reason': 'no_config'}), 200
    except Exception as e:
        return jsonify({'mongo_ok': False, 'error': str(e)}), 500

@main_bp.route('/test/mongo')
def test_mongo():
    """Teste completo de escrita e leitura no MongoDB."""
    from extensions import mongo_client, mongo_db
    from datetime import datetime
    
    try:
        if not mongo_client:
            return jsonify({'error': 'MongoDB não configurado'}), 500
            
        # Teste de escrita
        test_doc = {
            'teste': 'deploy_render',
            'timestamp': datetime.utcnow(),
            'app': 'almox-sms'
        }
        
        result = mongo_db['test_collection'].insert_one(test_doc)
        
        # Teste de leitura
        doc_inserido = mongo_db['test_collection'].find_one({'_id': result.inserted_id})
        
        # Contar documentos na coleção
        count = mongo_db['test_collection'].count_documents({})
        
        return jsonify({
            'mongo_ok': True,
            'database': mongo_db.name,
            'documento_inserido': str(result.inserted_id),
            'documento_lido': {
                'teste': doc_inserido['teste'],
                'timestamp': doc_inserido['timestamp'].isoformat(),
                'app': doc_inserido['app']
            },
            'total_documentos': count
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/configuracoes')
@require_admin_or_above
def configuracoes():
    """Página de configurações"""
    ui_config = get_ui_blocks_config()
    settings_sections = ui_config.get_settings_sections_for_user(current_user.nivel_acesso)
    return render_template('configuracoes.html', settings_sections=settings_sections)

@main_bp.route('/configuracoes/hierarquia')
@require_admin_or_above
def configuracoes_hierarquia():
    """Página de configuração da hierarquia"""
    # Aplica filtros de escopo baseados no usuário logado
    centrais = ScopeFilter.filter_centrais(Central.query.filter_by(ativo=True)).all()
    almoxarifados = ScopeFilter.filter_almoxarifados(Almoxarifado.query.filter_by(ativo=True)).all()
    sub_almoxarifados = ScopeFilter.filter_sub_almoxarifados(SubAlmoxarifado.query.filter_by(ativo=True)).all()
    setores = ScopeFilter.filter_setores(Setor.query.filter_by(ativo=True)).all()
    
    return render_template('configuracoes/hierarquia.html',
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

# ==================== PRODUTOS ====================

@main_bp.route('/produtos')
@require_any_level
def produtos():
    """Página de produtos"""
    categorias = CategoriaProduto.get_active_categories()
    return render_template('produtos/index.html', categorias=categorias)

@main_bp.route('/produtos/cadastro')
@require_manager_or_above
def produtos_cadastro():
    """Página de cadastro de produtos"""
    categorias = CategoriaProduto.get_active_categories()
    return render_template('produtos/cadastro.html', categorias=categorias)

@main_bp.route('/produtos/<int:id>')
@require_any_level
def produtos_detalhes(id):
    """Página de detalhes do produto"""
    produto = Produto.query.get_or_404(id)
    return render_template('produtos/detalhes.html', produto=produto)

@main_bp.route('/produtos/<int:id>/recebimento')
@require_any_level
def produtos_recebimento(id):
    """Página de recebimento de produtos"""
    produto = Produto.query.get_or_404(id)
    # Aplica filtros de escopo baseados no usuário logado
    centrais = ScopeFilter.filter_centrais(Central.query.filter_by(ativo=True)).all()
    almoxarifados = ScopeFilter.filter_almoxarifados(Almoxarifado.query.filter_by(ativo=True)).all()
    sub_almoxarifados = ScopeFilter.filter_sub_almoxarifados(SubAlmoxarifado.query.filter_by(ativo=True)).all()
    setores = ScopeFilter.filter_setores(Setor.query.filter_by(ativo=True)).all()
    
    return render_template('produtos/recebimento.html', 
                         produto=produto,
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

@main_bp.route('/estoque')
@require_any_level
def estoque():
    """Página de consulta de estoque"""
    # Aplica filtros de escopo baseados no usuário logado
    centrais = ScopeFilter.filter_centrais(Central.query.filter_by(ativo=True)).all()
    almoxarifados = ScopeFilter.filter_almoxarifados(Almoxarifado.query.filter_by(ativo=True)).all()
    sub_almoxarifados = ScopeFilter.filter_sub_almoxarifados(SubAlmoxarifado.query.filter_by(ativo=True)).all()
    setores = ScopeFilter.filter_setores(Setor.query.filter_by(ativo=True)).all()
    
    return render_template('produtos/estoque.html',
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores)

@main_bp.route('/movimentacoes')
@require_any_level
def movimentacoes():
    """Página de movimentações e transferências"""
    # Aplica filtros de escopo baseados no usuário logado
    centrais = ScopeFilter.filter_centrais(Central.query.filter_by(ativo=True)).all()
    almoxarifados = ScopeFilter.filter_almoxarifados(Almoxarifado.query.filter_by(ativo=True)).all()
    sub_almoxarifados = ScopeFilter.filter_sub_almoxarifados(SubAlmoxarifado.query.filter_by(ativo=True)).all()
    setores = ScopeFilter.filter_setores(Setor.query.filter_by(ativo=True)).all()
    
    # Converter objetos para dicionários para serialização JSON
    centrais_dict = [{'id': c.id, 'nome': c.nome} for c in centrais]
    almoxarifados_dict = [{'id': a.id, 'nome': a.nome, 'central_id': a.central_id} for a in almoxarifados]
    sub_almoxarifados_dict = [{'id': s.id, 'nome': s.nome, 'almoxarifado_id': s.almoxarifado_id} for s in sub_almoxarifados]
    setores_dict = [{'id': s.id, 'nome': s.nome} for s in setores]
    
    return render_template('movimentacoes/index.html',
                         centrais=centrais_dict,
                         almoxarifados=almoxarifados_dict,
                         sub_almoxarifados=sub_almoxarifados_dict,
                         setores=setores_dict)

# ==================== USUÁRIOS ====================

@main_bp.route('/configuracoes/usuarios')
@require_admin_or_above
def configuracoes_usuarios():
    """Página de gerenciamento de usuários"""
    from models.categoria import CategoriaProduto
    
    # Busca todos os usuários com suas hierarquias
    usuarios = Usuario.query.options(
        db.joinedload(Usuario.central),
        db.joinedload(Usuario.almoxarifado).joinedload(Almoxarifado.central),
        db.joinedload(Usuario.sub_almoxarifado).joinedload(SubAlmoxarifado.almoxarifado).joinedload(Almoxarifado.central),
        db.joinedload(Usuario.setor).joinedload(Setor.sub_almoxarifado).joinedload(SubAlmoxarifado.almoxarifado).joinedload(Almoxarifado.central)
    ).all()
    
    # Busca hierarquias para formulário de criação/edição
    centrais = Central.query.filter_by(ativo=True).all()
    almoxarifados = Almoxarifado.query.filter_by(ativo=True).all()
    sub_almoxarifados = SubAlmoxarifado.query.filter_by(ativo=True).all()
    setores = Setor.query.filter_by(ativo=True).all()
    categorias = CategoriaProduto.query.filter_by(ativo=True).order_by(CategoriaProduto.nome).all()
    
    return render_template('users/index.html',
                         usuarios=usuarios,
                         centrais=centrais,
                         almoxarifados=almoxarifados,
                         sub_almoxarifados=sub_almoxarifados,
                         setores=setores,
                         categorias=categorias)

@main_bp.route('/configuracoes/categorias')
@require_admin_or_above
def configuracoes_categorias():
    """Página de configuração de categorias de produtos"""
    return render_template('categorias/index.html')

# ==================== ROTAS DIRETAS PARA COMPATIBILIDADE COM TESTES ====================

@main_bp.route('/usuarios')
@require_admin_or_above
def usuarios():
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
