"""
Script de migração para criar tabelas de usuários e auditoria
Executa: python migrations/create_usuario_tables.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.usuario import Usuario, LogAuditoria
from models.hierarchy import Central, Almoxarifado, SubAlmoxarifado, Setor
from werkzeug.security import generate_password_hash

def create_tables():
    """Cria as tabelas de usuário e auditoria"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Criando tabelas de usuários e auditoria...")
            
            # Cria as tabelas
            db.create_all()
            
            print("✓ Tabelas criadas com sucesso!")
            
            # Verifica se já existe um super admin
            super_admin = Usuario.query.filter_by(nivel_acesso='super_admin').first()
            
            if not super_admin:
                print("\nCriando usuário Super Administrador padrão...")
                
                # Cria usuário super admin padrão
                admin = Usuario(
                    username='admin',
                    email='admin@almoxsms.com',
                    nome_completo='Administrador do Sistema',
                    nivel_acesso='super_admin',
                    ativo=True
                )
                admin.set_password('admin123')  # Senha padrão - DEVE SER ALTERADA
                
                db.session.add(admin)
                db.session.commit()
                
                print("✓ Super Administrador criado!")
                print("  Usuário: admin")
                print("  Senha: admin123")
                print("  ⚠️  IMPORTANTE: Altere a senha padrão após o primeiro login!")
            else:
                print("✓ Super Administrador já existe no sistema")
            
            # Cria usuários de exemplo se não existirem
            create_sample_users()
            
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            return False
    
    return True

def create_sample_users():
    """Cria usuários de exemplo para demonstração"""
    try:
        # Verifica se já existem usuários de exemplo
        if Usuario.query.count() > 1:
            print("✓ Usuários de exemplo já existem")
            return
        
        print("\nCriando usuários de exemplo...")
        
        # Busca hierarquias existentes para associar aos usuários
        central = Central.query.first()
        almoxarifado = Almoxarifado.query.first()
        sub_almoxarifado = SubAlmoxarifado.query.first()
        setor = Setor.query.first()
        
        usuarios_exemplo = []
        
        # Admin de Central
        if central:
            admin_central = Usuario(
                username='admin_central',
                email='admin.central@almoxsms.com',
                nome_completo='Administrador da Central',
                nivel_acesso='admin_central',
                central_id=central.id,
                ativo=True
            )
            admin_central.set_password('central123')
            usuarios_exemplo.append(admin_central)
        
        # Gerente de Almoxarifado
        if almoxarifado:
            gerente_almox = Usuario(
                username='gerente_almox',
                email='gerente.almox@almoxsms.com',
                nome_completo='Gerente do Almoxarifado',
                nivel_acesso='gerente_almox',
                almoxarifado_id=almoxarifado.id,
                ativo=True
            )
            gerente_almox.set_password('almox123')
            usuarios_exemplo.append(gerente_almox)
        
        # Responsável de Sub-Almoxarifado
        if sub_almoxarifado:
            resp_sub_almox = Usuario(
                username='resp_farmacia',
                email='farmacia@almoxsms.com',
                nome_completo='Responsável da Farmácia',
                nivel_acesso='resp_sub_almox',
                sub_almoxarifado_id=sub_almoxarifado.id,
                ativo=True
            )
            resp_sub_almox.set_password('farmacia123')
            usuarios_exemplo.append(resp_sub_almox)
        
        # Operador de Setor
        if setor:
            operador_setor = Usuario(
                username='operador_setor',
                email='operador.setor@almoxsms.com',
                nome_completo='Operador do Setor',
                nivel_acesso='operador_setor',
                setor_id=setor.id,
                ativo=True
            )
            operador_setor.set_password('setor123')
            usuarios_exemplo.append(operador_setor)
        
        # Adiciona todos os usuários
        for usuario in usuarios_exemplo:
            db.session.add(usuario)
        
        db.session.commit()
        
        print(f"✓ {len(usuarios_exemplo)} usuários de exemplo criados!")
        print("\nUsuários criados:")
        for usuario in usuarios_exemplo:
            print(f"  - {usuario.username} ({usuario.nivel_acesso})")
        
        print("\n⚠️  IMPORTANTE: Todas as senhas padrão devem ser alteradas!")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuários de exemplo: {e}")
        db.session.rollback()

def verify_tables():
    """Verifica se as tabelas foram criadas corretamente"""
    app = create_app()
    
    with app.app_context():
        try:
            # Testa consultas básicas
            usuarios_count = Usuario.query.count()
            logs_count = LogAuditoria.query.count()
            
            print(f"\n📊 Verificação das tabelas:")
            print(f"  - Usuários: {usuarios_count}")
            print(f"  - Logs de Auditoria: {logs_count}")
            
            # Lista usuários criados
            if usuarios_count > 0:
                print(f"\n👥 Usuários no sistema:")
                usuarios = Usuario.query.all()
                for usuario in usuarios:
                    status = "🟢 Ativo" if usuario.ativo else "🔴 Inativo"
                    print(f"  - {usuario.username} ({usuario.nivel_acesso}) - {status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na verificação: {e}")
            return False

if __name__ == '__main__':
    print("🚀 Iniciando migração de usuários...")
    
    if create_tables():
        if verify_tables():
            print("\n✅ Migração concluída com sucesso!")
            print("\n🔐 Sistema de autenticação pronto para uso!")
            print("   Acesse: http://localhost:5000/auth/login")
        else:
            print("\n❌ Falha na verificação das tabelas")
    else:
        print("\n❌ Falha na criação das tabelas")