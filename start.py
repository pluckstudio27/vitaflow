#!/usr/bin/env python3
"""
Script de inicialização para deploy no Render
Executa migrações e cria usuário admin antes de iniciar a aplicação
"""
import os
import sys
from app import create_app
from extensions import db
from models.usuario import Usuario
from werkzeug.security import generate_password_hash

def init_database():
    """Inicializa o banco de dados e cria usuário admin"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Criando tabelas do banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # Verifica se já existe um super admin
            super_admin = Usuario.query.filter_by(nivel_acesso='super_admin').first()
            
            if not super_admin:
                print("🔄 Criando usuário Super Administrador...")
                
                # Verifica se já existe usuário com username 'admin'
                existing_admin = Usuario.query.filter_by(username='admin').first()
                if existing_admin:
                    print("⚠️  Usuário 'admin' já existe, atualizando para super_admin...")
                    existing_admin.nivel_acesso = 'super_admin'
                    existing_admin.ativo = True
                    db.session.commit()
                    print("✅ Usuário admin atualizado para super_admin!")
                else:
                    # Cria usuário super admin padrão
                    admin = Usuario(
                        username='admin',
                        email='admin@almoxsms.com',
                        nome_completo='Administrador do Sistema',
                        nivel_acesso='super_admin',
                        ativo=True
                    )
                    admin.set_password('admin123')  # Senha padrão
                    
                    db.session.add(admin)
                    db.session.commit()
                    
                    print("✅ Super Administrador criado!")
                    print("   Usuário: admin")
                    print("   Senha: admin123")
                    print("   ⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
            else:
                print("✅ Super Administrador já existe no sistema")
                print(f"   Usuário: {super_admin.username}")
                
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inicializar banco de dados: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Função principal"""
    print("🚀 Iniciando aplicação Almox SMS...")
    
    # Inicializa o banco de dados
    if not init_database():
        print("❌ Falha na inicialização do banco de dados")
        sys.exit(1)
    
    print("✅ Inicialização concluída com sucesso!")
    print("🌐 Aplicação pronta para uso!")

if __name__ == '__main__':
    main()