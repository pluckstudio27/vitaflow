#!/usr/bin/env python3
"""
Migração: Adicionar tabela usuario_categorias para relacionamento many-to-many
Permite que usuários gerenciem múltiplas categorias específicas
"""

import sqlite3
import os
import sys

def get_db_path():
    """Retorna o caminho do banco de dados"""
    # Assumindo que o script está em migrations/ e o banco está na raiz
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'almoxarifado.db')

def create_usuario_categorias_table():
    """Cria a tabela usuario_categorias"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Criando tabela usuario_categorias...")
        
        # Criar tabela usuario_categorias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuario_categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                categoria_id INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (categoria_id) REFERENCES categorias_produtos(id) ON DELETE CASCADE
            )
        """)
        
        # Criar índices
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_usuario_categoria_unique
            ON usuario_categorias(usuario_id, categoria_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usuario_categoria_usuario
            ON usuario_categorias(usuario_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usuario_categoria_categoria
            ON usuario_categorias(categoria_id)
        """)
        
        conn.commit()
        print("✓ Tabela usuario_categorias criada com sucesso")
        print("✓ Índices criados com sucesso")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela usuario_categorias: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verifica se a migração foi aplicada corretamente"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='usuario_categorias'
        """)
        
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Verificar estrutura da tabela
            cursor.execute("PRAGMA table_info(usuario_categorias)")
            columns = cursor.fetchall()
            
            expected_columns = ['id', 'usuario_id', 'categoria_id']
            actual_columns = [col[1] for col in columns]
            
            print(f"Tabela usuario_categorias: {'✓' if table_exists else '✗'}")
            print(f"Colunas esperadas: {expected_columns}")
            print(f"Colunas encontradas: {actual_columns}")
            
            # Verificar índices
            cursor.execute("PRAGMA index_list(usuario_categorias)")
            indexes = cursor.fetchall()
            index_names = [idx[1] for idx in indexes]
            
            expected_indexes = [
                'idx_usuario_categoria_unique',
                'idx_usuario_categoria_usuario', 
                'idx_usuario_categoria_categoria'
            ]
            
            print(f"Índices encontrados: {index_names}")
            
            return table_exists and all(col in actual_columns for col in expected_columns)
        else:
            print("✗ Tabela usuario_categorias não encontrada")
            return False
            
    except sqlite3.Error as e:
        print(f"Erro ao verificar migração: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """Função principal da migração"""
    print("=== Migração: Adicionar tabela usuario_categorias ===")
    print()
    
    # Verificar se já foi aplicada
    if verify_migration():
        print("Migração já foi aplicada anteriormente.")
        return True
    
    # Aplicar migração
    print("Aplicando migração...")
    success = create_usuario_categorias_table()
    
    if success:
        print()
        print("=== Verificação pós-migração ===")
        verify_migration()
        print()
        print("✓ Migração concluída com sucesso!")
        print()
        print("Agora os usuários podem gerenciar múltiplas categorias específicas")
        print("além da categoria principal ou todas as categorias.")
    else:
        print("✗ Falha na migração")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)