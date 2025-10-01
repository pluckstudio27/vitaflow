#!/usr/bin/env python3
"""
Migração para adicionar sistema de categorias de produtos
- Cria tabela categorias_produtos
- Adiciona categoria_id aos modelos Usuario e Produto
- Cria categorias padrão
- Migra dados existentes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from models.categoria import CategoriaProduto
from models.usuario import Usuario
from models.produto import Produto
from sqlalchemy import text
import sqlite3

def backup_data():
    """Backup dos dados existentes usando SQL direto"""
    print("Fazendo backup dos dados...")
    
    try:
        # Backup de usuários usando SQL direto
        usuarios_result = db.session.execute(text("SELECT * FROM usuarios")).fetchall()
        usuarios_data = []
        for row in usuarios_result:
            usuarios_data.append(dict(row._mapping))
        
        # Backup de produtos usando SQL direto
        produtos_result = db.session.execute(text("SELECT * FROM produtos")).fetchall()
        produtos_data = []
        for row in produtos_result:
            produtos_data.append(dict(row._mapping))
        
        print(f"Backup realizado: {len(usuarios_data)} usuários, {len(produtos_data)} produtos")
        return usuarios_data, produtos_data
        
    except Exception as e:
        print(f"Erro no backup: {e}")
        return [], []

def create_categoria_table():
    """Criar tabela de categorias"""
    print("Criando tabela categorias_produtos...")
    
    try:
        # Verificar se a tabela já existe
        result = db.session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='categorias_produtos'
        """)).fetchone()
        
        if result:
            print("Tabela categorias_produtos já existe")
            return
        
        # Criar tabela
        db.session.execute(text("""
            CREATE TABLE categorias_produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(100) NOT NULL UNIQUE,
                descricao TEXT,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                cor VARCHAR(7) DEFAULT '#007bff',
                ativo BOOLEAN DEFAULT 1,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                CHECK (ativo IN (0, 1))
            )
        """))
        
        # Criar índices
        db.session.execute(text("""
            CREATE INDEX idx_categoria_nome ON categorias_produtos(nome)
        """))
        
        db.session.execute(text("""
            CREATE INDEX idx_categoria_codigo ON categorias_produtos(codigo)
        """))
        
        db.session.execute(text("""
            CREATE INDEX idx_categoria_ativo ON categorias_produtos(ativo)
        """))
        
        db.session.commit()
        print("Tabela categorias_produtos criada com sucesso")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar tabela categorias_produtos: {e}")
        raise

def add_categoria_columns():
    """Adicionar colunas categoria_id nas tabelas existentes"""
    print("Adicionando colunas categoria_id...")
    
    try:
        # Verificar se coluna categoria_id já existe na tabela usuarios
        result = db.session.execute(text("""
            PRAGMA table_info(usuarios)
        """)).fetchall()
        
        columns = [col[1] for col in result]
        
        if 'categoria_id' not in columns:
            db.session.execute(text("""
                ALTER TABLE usuarios ADD COLUMN categoria_id INTEGER 
                REFERENCES categorias_produtos(id)
            """))
            print("Coluna categoria_id adicionada à tabela usuarios")
        else:
            print("Coluna categoria_id já existe na tabela usuarios")
        
        # Verificar se coluna categoria_id já existe na tabela produtos
        result = db.session.execute(text("""
            PRAGMA table_info(produtos)
        """)).fetchall()
        
        columns = [col[1] for col in result]
        
        if 'categoria_id' not in columns:
            db.session.execute(text("""
                ALTER TABLE produtos ADD COLUMN categoria_id INTEGER 
                REFERENCES categorias_produtos(id)
            """))
            print("Coluna categoria_id adicionada à tabela produtos")
        else:
            print("Coluna categoria_id já existe na tabela produtos")
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao adicionar colunas categoria_id: {e}")
        raise

def create_default_categories():
    """Criar categorias padrão"""
    print("Criando categorias padrão...")
    
    categorias_padrao = [
        {
            'nome': 'Material Hospitalar',
            'codigo': 'HOSP',
            'descricao': 'Materiais e equipamentos hospitalares',
            'cor': '#28a745'
        },
        {
            'nome': 'Material Odontológico',
            'codigo': 'ODONTO',
            'descricao': 'Materiais e equipamentos odontológicos',
            'cor': '#007bff'
        },
        {
            'nome': 'Medicamentos',
            'codigo': 'MED',
            'descricao': 'Medicamentos e produtos farmacêuticos',
            'cor': '#dc3545'
        },
        {
            'nome': 'Material de Limpeza',
            'codigo': 'LIMP',
            'descricao': 'Produtos de limpeza e higienização',
            'cor': '#ffc107'
        },
        {
            'nome': 'Material de Escritório',
            'codigo': 'ESC',
            'descricao': 'Materiais de escritório e papelaria',
            'cor': '#6f42c1'
        },
        {
            'nome': 'Equipamentos',
            'codigo': 'EQUIP',
            'descricao': 'Equipamentos diversos',
            'cor': '#fd7e14'
        }
    ]
    
    try:
        for cat_data in categorias_padrao:
            # Verificar se categoria já existe
            existing = CategoriaProduto.query.filter_by(codigo=cat_data['codigo']).first()
            if not existing:
                categoria = CategoriaProduto(
                    nome=cat_data['nome'],
                    codigo=cat_data['codigo'],
                    descricao=cat_data['descricao'],
                    cor=cat_data['cor'],
                    ativo=True
                )
                db.session.add(categoria)
                print(f"Categoria criada: {cat_data['nome']}")
            else:
                print(f"Categoria já existe: {cat_data['nome']}")
        
        db.session.commit()
        print("Categorias padrão criadas com sucesso")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar categorias padrão: {e}")
        raise

def migrate_existing_data():
    """Migrar dados existentes para usar categorias"""
    print("Migrando dados existentes...")
    
    try:
        # Mapear categorias antigas para novas
        categoria_mapping = {
            'material hospitalar': 'HOSP',
            'hospitalar': 'HOSP',
            'material odontológico': 'ODONTO',
            'odontológico': 'ODONTO',
            'odonto': 'ODONTO',
            'medicamento': 'MED',
            'medicamentos': 'MED',
            'farmácia': 'MED',
            'limpeza': 'LIMP',
            'higiene': 'LIMP',
            'escritório': 'ESC',
            'papelaria': 'ESC',
            'equipamento': 'EQUIP',
            'equipamentos': 'EQUIP'
        }
        
        # Obter categorias criadas usando SQL direto
        categorias_result = db.session.execute(text("SELECT codigo, id FROM categorias_produtos")).fetchall()
        categorias = {row[0]: row[1] for row in categorias_result}
        
        # Migrar produtos usando SQL direto
        produtos_result = db.session.execute(text("""
            SELECT id, categoria FROM produtos 
            WHERE categoria_id IS NULL AND categoria IS NOT NULL
        """)).fetchall()
        
        produtos_migrados = 0
        
        for row in produtos_result:
            produto_id, categoria_antiga = row[0], row[1]
            
            if categoria_antiga:
                categoria_lower = categoria_antiga.lower().strip()
                
                # Buscar mapeamento direto
                codigo_categoria = None
                for key, value in categoria_mapping.items():
                    if key in categoria_lower:
                        codigo_categoria = value
                        break
                
                # Se não encontrou mapeamento, usar categoria padrão
                if not codigo_categoria:
                    codigo_categoria = 'HOSP'  # Padrão: Material Hospitalar
                
                if codigo_categoria in categorias:
                    db.session.execute(text("""
                        UPDATE produtos SET categoria_id = :categoria_id 
                        WHERE id = :produto_id
                    """), {
                        'categoria_id': categorias[codigo_categoria],
                        'produto_id': produto_id
                    })
                    produtos_migrados += 1
        
        db.session.commit()
        print(f"Migrados {produtos_migrados} produtos para usar categorias")
        
        # Criar índices para otimização
        try:
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usuario_categoria_id 
                ON usuarios(categoria_id)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_produto_categoria_id_ativo 
                ON produtos(categoria_id, ativo)
            """))
            
            db.session.commit()
            print("Índices criados com sucesso")
            
        except Exception as e:
            print(f"Aviso: Erro ao criar índices: {e}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao migrar dados existentes: {e}")
        raise

def verify_migration():
    """Verificar se a migração foi bem-sucedida"""
    print("\nVerificando migração...")
    
    try:
        # Verificar tabela categorias usando SQL direto
        categorias_result = db.session.execute(text("SELECT COUNT(*) FROM categorias_produtos")).fetchone()
        categorias_count = categorias_result[0] if categorias_result else 0
        print(f"Categorias criadas: {categorias_count}")
        
        # Verificar produtos com categoria usando SQL direto
        produtos_com_categoria_result = db.session.execute(text("""
            SELECT COUNT(*) FROM produtos WHERE categoria_id IS NOT NULL
        """)).fetchone()
        produtos_com_categoria = produtos_com_categoria_result[0] if produtos_com_categoria_result else 0
        
        produtos_total_result = db.session.execute(text("SELECT COUNT(*) FROM produtos")).fetchone()
        produtos_total = produtos_total_result[0] if produtos_total_result else 0
        
        print(f"Produtos com categoria: {produtos_com_categoria}/{produtos_total}")
        
        # Verificar estrutura das tabelas
        result = db.session.execute(text("""
            PRAGMA table_info(usuarios)
        """)).fetchall()
        
        usuario_columns = [col[1] for col in result]
        has_categoria_id_usuario = 'categoria_id' in usuario_columns
        
        result = db.session.execute(text("""
            PRAGMA table_info(produtos)
        """)).fetchall()
        
        produto_columns = [col[1] for col in result]
        has_categoria_id_produto = 'categoria_id' in produto_columns
        
        print(f"Coluna categoria_id em usuarios: {'✓' if has_categoria_id_usuario else '✗'}")
        print(f"Coluna categoria_id em produtos: {'✓' if has_categoria_id_produto else '✗'}")
        
        if categorias_count > 0 and has_categoria_id_usuario and has_categoria_id_produto:
            print("\n✓ Migração concluída com sucesso!")
            return True
        else:
            print("\n✗ Migração incompleta!")
            return False
            
    except Exception as e:
        print(f"Erro na verificação: {e}")
        return False

def main():
    """Executar migração completa"""
    print("=== Migração: Sistema de Categorias de Produtos ===\n")
    
    try:
        # 1. Backup dos dados
        usuarios_backup, produtos_backup = backup_data()
        
        # 2. Criar tabela de categorias
        create_categoria_table()
        
        # 3. Adicionar colunas categoria_id
        add_categoria_columns()
        
        # 4. Criar categorias padrão
        create_default_categories()
        
        # 5. Migrar dados existentes
        migrate_existing_data()
        
        # 6. Verificar migração
        success = verify_migration()
        
        if success:
            print("\n🎉 Migração concluída com sucesso!")
            print("\nPróximos passos:")
            print("1. Reiniciar a aplicação Flask")
            print("2. Atualizar interfaces de usuário")
            print("3. Testar funcionalidades de categoria")
        else:
            print("\n❌ Migração falhou. Verifique os logs acima.")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {e}")
        print("A migração foi interrompida.")
        return False
    
    return True

if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        success = main()
        sys.exit(0 if success else 1)