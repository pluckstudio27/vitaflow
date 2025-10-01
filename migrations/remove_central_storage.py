"""
Migração para remover Central como local de armazenamento

Esta migração remove as referências de Central como local de armazenamento:
1. Remove central_id da tabela estoque_produto
2. Remove origem_central_id e destino_central_id da tabela movimentacao_produto
3. Remove índices relacionados
4. Atualiza constraints

IMPORTANTE: Execute esta migração apenas após backup do banco de dados!
"""

import sqlite3
import os
from datetime import datetime

def backup_database(db_path):
    """Cria backup do banco de dados"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Conectar ao banco original
    source = sqlite3.connect(db_path)
    
    # Criar backup
    backup = sqlite3.connect(backup_path)
    source.backup(backup)
    
    source.close()
    backup.close()
    
    print(f"Backup criado: {backup_path}")
    return backup_path

def migrate_database(db_path):
    """Executa a migração do banco de dados"""
    
    # Criar backup antes da migração
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Iniciando migração...")
        
        # 1. Verificar se existem dados de estoque em central
        cursor.execute("SELECT COUNT(*) FROM estoque_produto WHERE central_id IS NOT NULL")
        central_stock_count = cursor.fetchone()[0]
        
        if central_stock_count > 0:
            print(f"AVISO: Encontrados {central_stock_count} registros de estoque em Central.")
            print("Estes registros serão removidos durante a migração.")
            
            # Listar os produtos afetados
            cursor.execute("""
                SELECT p.nome, ep.quantidade_disponivel, c.nome as central_nome
                FROM estoque_produto ep
                JOIN produto p ON ep.produto_id = p.id
                JOIN central c ON ep.central_id = c.id
                WHERE ep.central_id IS NOT NULL
            """)
            
            affected_products = cursor.fetchall()
            print("Produtos afetados:")
            for produto_nome, quantidade, central_nome in affected_products:
                print(f"  - {produto_nome}: {quantidade} unidades em {central_nome}")
        
        # 2. Verificar movimentações com central
        cursor.execute("""
            SELECT COUNT(*) FROM movimentacao_produto 
            WHERE origem_central_id IS NOT NULL OR destino_central_id IS NOT NULL
        """)
        central_movements_count = cursor.fetchone()[0]
        
        if central_movements_count > 0:
            print(f"AVISO: Encontradas {central_movements_count} movimentações envolvendo Central.")
            print("Os campos central_id serão removidos, mas os registros serão mantidos.")
        
        # 3. Remover índices relacionados a central
        print("Removendo índices...")
        
        indices_to_drop = [
            'idx_estoque_produto_central',
            'idx_movimentacao_origem_central', 
            'idx_movimentacao_destino_central'
        ]
        
        for index_name in indices_to_drop:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                print(f"  - Índice {index_name} removido")
            except sqlite3.Error as e:
                print(f"  - Erro ao remover índice {index_name}: {e}")
        
        # 4. Criar nova tabela estoque_produto sem central_id
        print("Criando nova tabela estoque_produto...")
        
        cursor.execute("""
            CREATE TABLE estoque_produto_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                almoxarifado_id INTEGER,
                sub_almoxarifado_id INTEGER,
                setor_id INTEGER,
                quantidade_disponivel DECIMAL(10,3) NOT NULL DEFAULT 0,
                quantidade_reservada DECIMAL(10,3) NOT NULL DEFAULT 0,
                data_ultima_movimentacao DATE,
                FOREIGN KEY (produto_id) REFERENCES produto (id) ON DELETE CASCADE,
                FOREIGN KEY (almoxarifado_id) REFERENCES almoxarifado (id) ON DELETE CASCADE,
                FOREIGN KEY (sub_almoxarifado_id) REFERENCES sub_almoxarifado (id) ON DELETE CASCADE,
                FOREIGN KEY (setor_id) REFERENCES setor (id) ON DELETE CASCADE,
                CONSTRAINT check_single_location CHECK (
                    (almoxarifado_id IS NOT NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NULL) OR
                    (almoxarifado_id IS NULL AND sub_almoxarifado_id IS NOT NULL AND setor_id IS NULL) OR
                    (almoxarifado_id IS NULL AND sub_almoxarifado_id IS NULL AND setor_id IS NOT NULL)
                )
            )
        """)
        
        # 5. Migrar dados (excluindo registros com central_id)
        print("Migrando dados de estoque (excluindo registros de Central)...")
        
        cursor.execute("""
            INSERT INTO estoque_produto_new (
                id, produto_id, almoxarifado_id, sub_almoxarifado_id, setor_id,
                quantidade_disponivel, quantidade_reservada, data_ultima_movimentacao
            )
            SELECT 
                id, produto_id, almoxarifado_id, sub_almoxarifado_id, setor_id,
                quantidade_disponivel, quantidade_reservada, data_ultima_movimentacao
            FROM estoque_produto
            WHERE central_id IS NULL
        """)
        
        migrated_count = cursor.rowcount
        print(f"  - {migrated_count} registros migrados")
        
        # 6. Substituir tabela antiga
        cursor.execute("DROP TABLE estoque_produto")
        cursor.execute("ALTER TABLE estoque_produto_new RENAME TO estoque_produto")
        
        # 7. Criar nova tabela movimentacao_produto sem campos central
        print("Criando nova tabela movimentacao_produto...")
        
        cursor.execute("""
            CREATE TABLE movimentacao_produto_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                tipo_movimentacao VARCHAR(20) NOT NULL,
                quantidade DECIMAL(10,3) NOT NULL,
                data_movimentacao DATE NOT NULL,
                motivo VARCHAR(255),
                observacoes TEXT,
                usuario_responsavel VARCHAR(255),
                origem_almoxarifado_id INTEGER,
                origem_sub_almoxarifado_id INTEGER,
                origem_setor_id INTEGER,
                destino_almoxarifado_id INTEGER,
                destino_sub_almoxarifado_id INTEGER,
                destino_setor_id INTEGER,
                FOREIGN KEY (produto_id) REFERENCES produto (id) ON DELETE CASCADE,
                FOREIGN KEY (origem_almoxarifado_id) REFERENCES almoxarifado (id) ON DELETE SET NULL,
                FOREIGN KEY (origem_sub_almoxarifado_id) REFERENCES sub_almoxarifado (id) ON DELETE SET NULL,
                FOREIGN KEY (origem_setor_id) REFERENCES setor (id) ON DELETE SET NULL,
                FOREIGN KEY (destino_almoxarifado_id) REFERENCES almoxarifado (id) ON DELETE SET NULL,
                FOREIGN KEY (destino_sub_almoxarifado_id) REFERENCES sub_almoxarifado (id) ON DELETE SET NULL,
                FOREIGN KEY (destino_setor_id) REFERENCES setor (id) ON DELETE SET NULL
            )
        """)
        
        # 8. Migrar dados de movimentação (removendo campos central)
        print("Migrando dados de movimentação...")
        
        cursor.execute("""
            INSERT INTO movimentacao_produto_new (
                id, produto_id, tipo_movimentacao, quantidade, data_movimentacao,
                motivo, observacoes, usuario_responsavel,
                origem_almoxarifado_id, origem_sub_almoxarifado_id, origem_setor_id,
                destino_almoxarifado_id, destino_sub_almoxarifado_id, destino_setor_id
            )
            SELECT 
                id, produto_id, tipo_movimentacao, quantidade, data_movimentacao,
                motivo, observacoes, usuario_responsavel,
                origem_almoxarifado_id, origem_sub_almoxarifado_id, origem_setor_id,
                destino_almoxarifado_id, destino_sub_almoxarifado_id, destino_setor_id
            FROM movimentacao_produto
        """)
        
        migrated_movements = cursor.rowcount
        print(f"  - {migrated_movements} movimentações migradas")
        
        # 9. Substituir tabela antiga
        cursor.execute("DROP TABLE movimentacao_produto")
        cursor.execute("ALTER TABLE movimentacao_produto_new RENAME TO movimentacao_produto")
        
        # 10. Recriar índices necessários
        print("Recriando índices...")
        
        indices_to_create = [
            "CREATE INDEX idx_estoque_produto_produto ON estoque_produto(produto_id)",
            "CREATE INDEX idx_estoque_produto_almoxarifado ON estoque_produto(almoxarifado_id)",
            "CREATE INDEX idx_estoque_produto_sub_almoxarifado ON estoque_produto(sub_almoxarifado_id)",
            "CREATE INDEX idx_estoque_produto_setor ON estoque_produto(setor_id)",
            "CREATE INDEX idx_movimentacao_produto ON movimentacao_produto(produto_id)",
            "CREATE INDEX idx_movimentacao_data ON movimentacao_produto(data_movimentacao)",
            "CREATE INDEX idx_movimentacao_origem_almoxarifado ON movimentacao_produto(origem_almoxarifado_id)",
            "CREATE INDEX idx_movimentacao_origem_sub_almoxarifado ON movimentacao_produto(origem_sub_almoxarifado_id)",
            "CREATE INDEX idx_movimentacao_origem_setor ON movimentacao_produto(origem_setor_id)",
            "CREATE INDEX idx_movimentacao_destino_almoxarifado ON movimentacao_produto(destino_almoxarifado_id)",
            "CREATE INDEX idx_movimentacao_destino_sub_almoxarifado ON movimentacao_produto(destino_sub_almoxarifado_id)",
            "CREATE INDEX idx_movimentacao_destino_setor ON movimentacao_produto(destino_setor_id)"
        ]
        
        for index_sql in indices_to_create:
            try:
                cursor.execute(index_sql)
                print(f"  - Índice criado: {index_sql.split()[-1]}")
            except sqlite3.Error as e:
                print(f"  - Erro ao criar índice: {e}")
        
        # Commit das mudanças
        conn.commit()
        
        print("\nMigração concluída com sucesso!")
        print(f"Backup disponível em: {backup_path}")
        
        # Estatísticas finais
        cursor.execute("SELECT COUNT(*) FROM estoque_produto")
        final_stock_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM movimentacao_produto")
        final_movement_count = cursor.fetchone()[0]
        
        print(f"\nEstatísticas finais:")
        print(f"  - Registros de estoque: {final_stock_count}")
        print(f"  - Registros de movimentação: {final_movement_count}")
        
        if central_stock_count > 0:
            print(f"  - Registros de estoque em Central removidos: {central_stock_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        print(f"Restaure o backup se necessário: {backup_path}")
        raise

def main():
    """Função principal da migração"""
    
    # Caminhos possíveis do banco de dados
    possible_db_paths = [
        'almoxarifado.db',
        'instance/almox_sms.db',
        'instance/almoxarifado.db'
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("Erro: Banco de dados não encontrado!")
        print("Caminhos verificados:")
        for path in possible_db_paths:
            print(f"  - {path}")
        return
    
    print(f"Banco de dados encontrado: {db_path}")
    
    # Confirmar execução
    response = input("\nDeseja executar a migração? Esta ação é irreversível! (digite 'SIM' para confirmar): ")
    
    if response != 'SIM':
        print("Migração cancelada.")
        return
    
    # Executar migração
    migrate_database(db_path)

if __name__ == "__main__":
    main()