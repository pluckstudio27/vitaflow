"""
Script para inicializar o banco de dados
"""

from app import create_app
from models.hierarchy import db

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    
    app = create_app()
    
    with app.app_context():
        print("🚀 Inicializando banco de dados...")
        
        # Cria todas as tabelas
        db.create_all()
        
        print("✅ Banco de dados inicializado com sucesso!")
        print("📊 Tabelas criadas:")
        
        # Lista as tabelas criadas
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            print(f"  • {table}")

if __name__ == "__main__":
    init_database()