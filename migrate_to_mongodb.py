#!/usr/bin/env python3
"""
Script de migração de dados do SQLite para MongoDB
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from extensions import db, init_mongo

# Importa modelos SQLAlchemy
from models.usuario import Usuario
from models.categoria import CategoriaProduto
from models.produto import Produto, EstoqueProduto, LoteProduto, MovimentacaoProduto
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor

# Importa modelos MongoDB
from models_mongo import (
    UsuarioMongo, LogAuditoriaMongo, CategoriaProdutoMongo, ConfiguracaoCategoriaMongo,
    ProdutoMongo, EstoqueProdutoMongo, LoteProdutoMongo, MovimentacaoProdutoMongo,
    CentralMongo, AlmoxarifadoMongo, SubAlmoxarifadoMongo, SetorMongo,
    init_mongodb
)


class DataMigrator:
    """Classe para migração de dados do SQLite para MongoDB"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.stats = {
            'centrais': {'migrated': 0, 'errors': 0},
            'almoxarifados': {'migrated': 0, 'errors': 0},
            'sub_almoxarifados': {'migrated': 0, 'errors': 0},
            'categorias': {'migrated': 0, 'errors': 0},
            'produtos': {'migrated': 0, 'errors': 0},
            'usuarios': {'migrated': 0, 'errors': 0},
            'estoque': {'migrated': 0, 'errors': 0},
            'lotes': {'migrated': 0, 'errors': 0},
            'movimentacoes': {'migrated': 0, 'errors': 0}
        }
        self.id_mapping = {
            'centrais': {},
            'almoxarifados': {},
            'sub_almoxarifados': {},
            'categorias': {},
            'produtos': {},
            'usuarios': {},
            'setores': {}
        }
    
    def log(self, message: str, level: str = 'INFO'):
        """Log com timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def migrate_centrais(self):
        """Migra centrais do SQLite para MongoDB"""
        self.log("Iniciando migração de centrais...")
        
        try:
            centrais = Central.query.all()
            
            for central in centrais:
                try:
                    # Verifica se já existe
                    existing = CentralMongo.find_by_nome(central.nome)
                    if existing:
                        self.log(f"Central '{central.nome}' já existe no MongoDB")
                        self.id_mapping['centrais'][central.id] = str(existing._id)
                        continue
                    
                    # Cria nova central no MongoDB
                    central_mongo = CentralMongo(
                        nome=central.nome,
                        descricao=central.descricao or '',
                        codigo=central.codigo or '',
                        ativo=central.ativo,
                        endereco={
                            'logradouro': getattr(central, 'endereco', ''),
                            'cidade': getattr(central, 'cidade', ''),
                            'estado': getattr(central, 'estado', ''),
                            'cep': getattr(central, 'cep', '')
                        },
                        contato={
                            'telefone': getattr(central, 'telefone', ''),
                            'email': getattr(central, 'email', '')
                        },
                        data_criacao=central.data_criacao or datetime.utcnow(),
                        data_atualizacao=central.data_atualizacao or datetime.utcnow()
                    )
                    
                    central_mongo.save()
                    self.id_mapping['centrais'][central.id] = str(central_mongo._id)
                    self.stats['centrais']['migrated'] += 1
                    
                    self.log(f"Central '{central.nome}' migrada com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar central '{central.nome}': {e}", 'ERROR')
                    self.stats['centrais']['errors'] += 1
            
            self.log(f"Migração de centrais concluída: {self.stats['centrais']['migrated']} migradas, {self.stats['centrais']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de centrais: {e}", 'ERROR')
    
    def migrate_almoxarifados(self):
        """Migra almoxarifados do SQLite para MongoDB"""
        self.log("Iniciando migração de almoxarifados...")
        
        try:
            almoxarifados = Almoxarifado.query.all()
            
            for almox in almoxarifados:
                try:
                    # Busca central correspondente
                    central_mongo_id = self.id_mapping['centrais'].get(almox.central_id)
                    if not central_mongo_id:
                        self.log(f"Central não encontrada para almoxarifado '{almox.nome}'", 'ERROR')
                        self.stats['almoxarifados']['errors'] += 1
                        continue
                    
                    # Verifica se já existe
                    existing = AlmoxarifadoMongo.find_by_nome_central(almox.nome, central_mongo_id)
                    if existing:
                        self.log(f"Almoxarifado '{almox.nome}' já existe no MongoDB")
                        self.id_mapping['almoxarifados'][almox.id] = str(existing._id)
                        continue
                    
                    # Cria novo almoxarifado no MongoDB
                    almox_mongo = AlmoxarifadoMongo(
                        nome=almox.nome,
                        descricao=almox.descricao or '',
                        codigo=almox.codigo or '',
                        central_id=central_mongo_id,
                        ativo=almox.ativo,
                        tipo=getattr(almox, 'tipo', 'geral'),
                        endereco={
                            'logradouro': getattr(almox, 'endereco', ''),
                            'cidade': getattr(almox, 'cidade', ''),
                            'estado': getattr(almox, 'estado', ''),
                            'cep': getattr(almox, 'cep', '')
                        },
                        contato={
                            'telefone': getattr(almox, 'telefone', ''),
                            'email': getattr(almox, 'email', '')
                        },
                        capacidade_maxima=getattr(almox, 'capacidade_maxima', 0),
                        area_m2=getattr(almox, 'area_m2', 0.0),
                        data_criacao=almox.data_criacao or datetime.utcnow(),
                        data_atualizacao=almox.data_atualizacao or datetime.utcnow()
                    )
                    
                    almox_mongo.save()
                    self.id_mapping['almoxarifados'][almox.id] = str(almox_mongo._id)
                    self.stats['almoxarifados']['migrated'] += 1
                    
                    self.log(f"Almoxarifado '{almox.nome}' migrado com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar almoxarifado '{almox.nome}': {e}", 'ERROR')
                    self.stats['almoxarifados']['errors'] += 1
            
            self.log(f"Migração de almoxarifados concluída: {self.stats['almoxarifados']['migrated']} migrados, {self.stats['almoxarifados']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de almoxarifados: {e}", 'ERROR')
    
    def migrate_sub_almoxarifados(self):
        """Migra sub-almoxarifados do SQLite para MongoDB"""
        self.log("Iniciando migração de sub-almoxarifados...")
        
        try:
            sub_almoxs = SubAlmoxarifado.query.all()
            
            for sub_almox in sub_almoxs:
                try:
                    # Busca almoxarifado correspondente
                    almox_mongo_id = self.id_mapping['almoxarifados'].get(sub_almox.almoxarifado_id)
                    if not almox_mongo_id:
                        self.log(f"Almoxarifado não encontrado para sub-almoxarifado '{sub_almox.nome}'", 'ERROR')
                        self.stats['sub_almoxarifados']['errors'] += 1
                        continue
                    
                    # Verifica se já existe
                    existing = SubAlmoxarifadoMongo.find_by_nome_almoxarifado(sub_almox.nome, almox_mongo_id)
                    if existing:
                        self.log(f"Sub-almoxarifado '{sub_almox.nome}' já existe no MongoDB")
                        self.id_mapping['sub_almoxarifados'][sub_almox.id] = str(existing._id)
                        continue
                    
                    # Cria novo sub-almoxarifado no MongoDB
                    sub_almox_mongo = SubAlmoxarifadoMongo(
                        nome=sub_almox.nome,
                        descricao=sub_almox.descricao or '',
                        codigo=sub_almox.codigo or '',
                        almoxarifado_id=almox_mongo_id,
                        ativo=sub_almox.ativo,
                        tipo=getattr(sub_almox, 'tipo', 'geral'),
                        localizacao=getattr(sub_almox, 'localizacao', ''),
                        capacidade_maxima=getattr(sub_almox, 'capacidade_maxima', 0),
                        area_m2=getattr(sub_almox, 'area_m2', 0.0),
                        temperatura_controlada=getattr(sub_almox, 'temperatura_controlada', False),
                        umidade_controlada=getattr(sub_almox, 'umidade_controlada', False),
                        data_criacao=sub_almox.data_criacao or datetime.utcnow(),
                        data_atualizacao=sub_almox.data_atualizacao or datetime.utcnow()
                    )
                    
                    sub_almox_mongo.save()
                    self.id_mapping['sub_almoxarifados'][sub_almox.id] = str(sub_almox_mongo._id)
                    self.stats['sub_almoxarifados']['migrated'] += 1
                    
                    self.log(f"Sub-almoxarifado '{sub_almox.nome}' migrado com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar sub-almoxarifado '{sub_almox.nome}': {e}", 'ERROR')
                    self.stats['sub_almoxarifados']['errors'] += 1
            
            self.log(f"Migração de sub-almoxarifados concluída: {self.stats['sub_almoxarifados']['migrated']} migrados, {self.stats['sub_almoxarifados']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de sub-almoxarifados: {e}", 'ERROR')
    
    def migrate_categorias(self):
        """Migra categorias do SQLite para MongoDB"""
        self.log("Iniciando migração de categorias...")
        
        try:
            categorias = CategoriaProduto.query.all()
            
            for categoria in categorias:
                try:
                    # Busca central correspondente
                    central_mongo_id = self.id_mapping['centrais'].get(categoria.central_id) if hasattr(categoria, 'central_id') else None
                    
                    # Verifica se já existe
                    existing = CategoriaProdutoMongo.find_by_nome(categoria.nome, central_mongo_id)
                    if existing:
                        self.log(f"Categoria '{categoria.nome}' já existe no MongoDB")
                        self.id_mapping['categorias'][categoria.id] = str(existing._id)
                        continue
                    
                    # Cria nova categoria no MongoDB
                    categoria_mongo = CategoriaProdutoMongo(
                        nome=categoria.nome,
                        descricao=categoria.descricao or '',
                        ativo=categoria.ativo,
                        cor_identificacao=getattr(categoria, 'cor_identificacao', '#007bff'),
                        icone=getattr(categoria, 'icone', 'fas fa-box'),
                        ordem_exibicao=getattr(categoria, 'ordem_exibicao', 0),
                        permite_estoque_negativo=getattr(categoria, 'permite_estoque_negativo', False),
                        requer_lote=getattr(categoria, 'requer_lote', False),
                        requer_validade=getattr(categoria, 'requer_validade', False),
                        dias_alerta_vencimento=getattr(categoria, 'dias_alerta_vencimento', 30),
                        estoque_minimo_padrao=getattr(categoria, 'estoque_minimo_padrao', 0),
                        estoque_maximo_padrao=getattr(categoria, 'estoque_maximo_padrao', 0),
                        central_id=central_mongo_id,
                        data_criacao=categoria.data_criacao or datetime.utcnow(),
                        data_atualizacao=categoria.data_atualizacao or datetime.utcnow()
                    )
                    
                    categoria_mongo.save()
                    self.id_mapping['categorias'][categoria.id] = str(categoria_mongo._id)
                    self.stats['categorias']['migrated'] += 1
                    
                    self.log(f"Categoria '{categoria.nome}' migrada com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar categoria '{categoria.nome}': {e}", 'ERROR')
                    self.stats['categorias']['errors'] += 1
            
            self.log(f"Migração de categorias concluída: {self.stats['categorias']['migrated']} migradas, {self.stats['categorias']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de categorias: {e}", 'ERROR')
    
    def migrate_produtos(self):
        """Migra produtos do SQLite para MongoDB"""
        self.log("Iniciando migração de produtos...")
        
        try:
            produtos = Produto.query.all()
            
            for produto in produtos:
                try:
                    # Busca categoria correspondente
                    categoria_mongo_id = self.id_mapping['categorias'].get(produto.categoria_id)
                    if not categoria_mongo_id:
                        self.log(f"Categoria não encontrada para produto '{produto.nome}'", 'ERROR')
                        self.stats['produtos']['errors'] += 1
                        continue
                    
                    # Busca central correspondente
                    central_mongo_id = self.id_mapping['centrais'].get(produto.central_id) if hasattr(produto, 'central_id') else None
                    
                    # Verifica se já existe pelo código de barras ou nome
                    existing = None
                    if produto.codigo_barras:
                        existing = ProdutoMongo.find_by_codigo_barras(produto.codigo_barras)
                    
                    if existing:
                        self.log(f"Produto '{produto.nome}' já existe no MongoDB")
                        self.id_mapping['produtos'][produto.id] = str(existing._id)
                        continue
                    
                    # Cria novo produto no MongoDB
                    produto_mongo = ProdutoMongo(
                        nome=produto.nome,
                        descricao=produto.descricao or '',
                        categoria_id=categoria_mongo_id,
                        ativo=produto.ativo,
                        unidade_medida=produto.unidade_medida or 'UN',
                        codigo_barras=produto.codigo_barras or '',
                        codigo_interno=produto.codigo_interno or '',
                        marca=getattr(produto, 'marca', ''),
                        modelo=getattr(produto, 'modelo', ''),
                        especificacoes=getattr(produto, 'especificacoes', {}),
                        preco_unitario=float(produto.preco_unitario or 0),
                        preco_medio=float(getattr(produto, 'preco_medio', 0)),
                        estoque_minimo=produto.estoque_minimo or 0,
                        estoque_maximo=produto.estoque_maximo or 0,
                        permite_estoque_negativo=getattr(produto, 'permite_estoque_negativo', False),
                        requer_lote=getattr(produto, 'requer_lote', False),
                        requer_validade=getattr(produto, 'requer_validade', False),
                        dias_alerta_vencimento=getattr(produto, 'dias_alerta_vencimento', 30),
                        observacoes=getattr(produto, 'observacoes', ''),
                        central_id=central_mongo_id,
                        data_criacao=produto.data_criacao or datetime.utcnow(),
                        data_atualizacao=produto.data_atualizacao or datetime.utcnow()
                    )
                    
                    produto_mongo.save()
                    self.id_mapping['produtos'][produto.id] = str(produto_mongo._id)
                    self.stats['produtos']['migrated'] += 1
                    
                    self.log(f"Produto '{produto.nome}' migrado com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar produto '{produto.nome}': {e}", 'ERROR')
                    self.stats['produtos']['errors'] += 1
            
            self.log(f"Migração de produtos concluída: {self.stats['produtos']['migrated']} migrados, {self.stats['produtos']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de produtos: {e}", 'ERROR')
    
    def migrate_usuarios(self):
        """Migra usuários do SQLite para MongoDB"""
        self.log("Iniciando migração de usuários...")
        
        try:
            usuarios = Usuario.query.all()
            
            for usuario in usuarios:
                try:
                    # Verifica se já existe
                    existing = UsuarioMongo.find_by_username(usuario.username)
                    if existing:
                        self.log(f"Usuário '{usuario.username}' já existe no MongoDB")
                        self.id_mapping['usuarios'][usuario.id] = str(existing._id)
                        continue
                    
                    # Busca IDs correspondentes
                    central_mongo_id = self.id_mapping['centrais'].get(usuario.central_id) if hasattr(usuario, 'central_id') else None
                    almox_mongo_id = self.id_mapping['almoxarifados'].get(usuario.almoxarifado_id) if hasattr(usuario, 'almoxarifado_id') else None
                    sub_almox_mongo_id = self.id_mapping['sub_almoxarifados'].get(usuario.sub_almoxarifado_id) if hasattr(usuario, 'sub_almoxarifado_id') else None
                    categoria_mongo_id = self.id_mapping['categorias'].get(usuario.categoria_id) if hasattr(usuario, 'categoria_id') else None
                    
                    # Cria novo usuário no MongoDB
                    usuario_mongo = UsuarioMongo(
                        username=usuario.username,
                        email=usuario.email,
                        nome_completo=getattr(usuario, 'nome_completo', ''),
                        nivel_acesso=getattr(usuario, 'nivel_acesso', 'operador_setor'),
                        ativo=usuario.ativo,
                        central_id=central_mongo_id,
                        almoxarifado_id=almox_mongo_id,
                        sub_almoxarifado_id=sub_almox_mongo_id,
                        categoria_id=categoria_mongo_id,
                        ultimo_login=getattr(usuario, 'ultimo_login', None),
                        data_criacao=usuario.data_criacao or datetime.utcnow(),
                        data_atualizacao=usuario.data_atualizacao or datetime.utcnow()
                    )
                    
                    # Copia o hash da senha
                    if hasattr(usuario, 'password_hash'):
                        usuario_mongo.data['password_hash'] = usuario.password_hash
                    
                    usuario_mongo.save()
                    self.id_mapping['usuarios'][usuario.id] = str(usuario_mongo._id)
                    self.stats['usuarios']['migrated'] += 1
                    
                    self.log(f"Usuário '{usuario.username}' migrado com sucesso")
                    
                except Exception as e:
                    self.log(f"Erro ao migrar usuário '{usuario.username}': {e}", 'ERROR')
                    self.stats['usuarios']['errors'] += 1
            
            self.log(f"Migração de usuários concluída: {self.stats['usuarios']['migrated']} migrados, {self.stats['usuarios']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de usuários: {e}", 'ERROR')
    
    def migrate_estoque(self):
        """Migra dados de estoque do SQLite para MongoDB"""
        self.log("Iniciando migração de estoque...")
        
        try:
            estoques = EstoqueProduto.query.all()
            
            for estoque in estoques:
                try:
                    # Busca produto correspondente
                    produto_mongo_id = self.id_mapping['produtos'].get(estoque.produto_id)
                    if not produto_mongo_id:
                        self.log(f"Produto não encontrado para estoque ID {estoque.id}", 'ERROR')
                        self.stats['estoque']['errors'] += 1
                        continue
                    
                    # Determina o tipo de local e ID
                    local_id = None
                    tipo_local = None
                    
                    if hasattr(estoque, 'almoxarifado_id') and estoque.almoxarifado_id:
                        local_id = self.id_mapping['almoxarifados'].get(estoque.almoxarifado_id)
                        tipo_local = 'almoxarifado'
                    elif hasattr(estoque, 'sub_almoxarifado_id') and estoque.sub_almoxarifado_id:
                        local_id = self.id_mapping['sub_almoxarifados'].get(estoque.sub_almoxarifado_id)
                        tipo_local = 'sub_almoxarifado'
                    
                    if not local_id or not tipo_local:
                        self.log(f"Local não encontrado para estoque ID {estoque.id}", 'ERROR')
                        self.stats['estoque']['errors'] += 1
                        continue
                    
                    # Verifica se já existe
                    existing = EstoqueProdutoMongo.find_by_produto_local(produto_mongo_id, local_id, tipo_local)
                    if existing:
                        self.log(f"Estoque já existe para produto {produto_mongo_id} no local {local_id}")
                        continue
                    
                    # Cria novo estoque no MongoDB
                    estoque_mongo = EstoqueProdutoMongo(
                        produto_id=produto_mongo_id,
                        local_id=local_id,
                        tipo_local=tipo_local,
                        quantidade_atual=float(estoque.quantidade_atual or 0),
                        quantidade_reservada=float(getattr(estoque, 'quantidade_reservada', 0)),
                        quantidade_disponivel=float(estoque.quantidade_atual or 0) - float(getattr(estoque, 'quantidade_reservada', 0)),
                        estoque_minimo=estoque.estoque_minimo or 0,
                        estoque_maximo=estoque.estoque_maximo or 0,
                        ultima_movimentacao=getattr(estoque, 'ultima_movimentacao', None),
                        data_criacao=estoque.data_criacao or datetime.utcnow(),
                        data_atualizacao=estoque.data_atualizacao or datetime.utcnow()
                    )
                    
                    estoque_mongo.save()
                    self.stats['estoque']['migrated'] += 1
                    
                except Exception as e:
                    self.log(f"Erro ao migrar estoque ID {estoque.id}: {e}", 'ERROR')
                    self.stats['estoque']['errors'] += 1
            
            self.log(f"Migração de estoque concluída: {self.stats['estoque']['migrated']} migrados, {self.stats['estoque']['errors']} erros")
            
        except Exception as e:
            self.log(f"Erro geral na migração de estoque: {e}", 'ERROR')
    
    def migrate_all(self):
        """Executa toda a migração"""
        self.log("=== INICIANDO MIGRAÇÃO COMPLETA DO SQLITE PARA MONGODB ===")
        
        with self.app.app_context():
            # Inicializa MongoDB
            init_mongodb()
            
            # Executa migrações na ordem correta (respeitando dependências)
            self.migrate_centrais()
            self.migrate_almoxarifados()
            self.migrate_sub_almoxarifados()
            self.migrate_categorias()
            self.migrate_produtos()
            self.migrate_usuarios()
            self.migrate_estoque()
            
            # Exibe estatísticas finais
            self.log("=== MIGRAÇÃO CONCLUÍDA ===")
            total_migrated = sum(stat['migrated'] for stat in self.stats.values())
            total_errors = sum(stat['errors'] for stat in self.stats.values())
            
            self.log(f"TOTAL MIGRADO: {total_migrated}")
            self.log(f"TOTAL ERROS: {total_errors}")
            
            for entity, stats in self.stats.items():
                self.log(f"{entity.upper()}: {stats['migrated']} migrados, {stats['errors']} erros")


def main():
    """Função principal"""
    # Cria aplicação Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializa extensões
    db.init_app(app)
    init_mongo(app)
    
    # Executa migração
    migrator = DataMigrator(app)
    migrator.migrate_all()


if __name__ == '__main__':
    main()