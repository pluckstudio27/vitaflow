#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar usuários padrão no sistema VitaFlow
Execute este script após inicializar o banco de dados
"""

from app import app, db, User
from datetime import datetime

def criar_usuarios_padrao():
    """Cria usuários padrão para o sistema"""
    
    with app.app_context():
        # Verificar se já existem usuários
        if User.query.count() > 0:
            print("Usuários já existem no sistema.")
            return
        
        usuarios_padrao = [
            {
                'username': 'admin',
                'email': 'admin@hospital-angicos.gov.br',
                'nome_completo': 'Administrador do Sistema',
                'cargo': 'admin',
                'setor': 'administracao',
                'password': 'admin123'
            },
            {
                'username': 'enfermeiro1',
                'email': 'enfermeiro@hospital-angicos.gov.br',
                'nome_completo': 'Maria Silva Santos',
                'cargo': 'tecnico',
                'setor': 'enfermagem',
                'password': 'enf123'
            },
            {
                'username': 'farmaceutico1',
                'email': 'farmaceutico@hospital-angicos.gov.br',
                'nome_completo': 'João Carlos Oliveira',
                'cargo': 'tecnico',
                'setor': 'farmacia',
                'password': 'farm123'
            },
            {
                'username': 'secretaria1',
                'email': 'secretaria@hospital-angicos.gov.br',
                'nome_completo': 'Ana Paula Costa',
                'cargo': 'secretaria',
                'setor': 'administracao',
                'password': 'sec123'
            },
            {
                'username': 'operador1',
                'email': 'operador@hospital-angicos.gov.br',
                'nome_completo': 'Carlos Eduardo Lima',
                'cargo': 'operador',
                'setor': 'almoxarifado',
                'password': 'op123'
            }
        ]
        
        print("Criando usuários padrão...")
        
        for dados_usuario in usuarios_padrao:
            usuario = User(
                username=dados_usuario['username'],
                email=dados_usuario['email'],
                nome_completo=dados_usuario['nome_completo'],
                cargo=dados_usuario['cargo'],
                setor=dados_usuario['setor'],
                ativo=True
            )
            usuario.set_password(dados_usuario['password'])
            
            try:
                db.session.add(usuario)
                db.session.commit()
                print(f"✓ Usuário criado: {dados_usuario['nome_completo']} ({dados_usuario['username']})")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Erro ao criar usuário {dados_usuario['username']}: {str(e)}")
        
        print("\n=== CREDENCIAIS DE ACESSO ===")
        print("Administrador:")
        print("  Usuário: admin")
        print("  Senha: admin123")
        print("\nEnfermeiro (Técnico):")
        print("  Usuário: enfermeiro1")
        print("  Senha: enf123")
        print("\nFarmacêutico (Técnico):")
        print("  Usuário: farmaceutico1")
        print("  Senha: farm123")
        print("\nSecretária:")
        print("  Usuário: secretaria1")
        print("  Senha: sec123")
        print("\nOperador:")
        print("  Usuário: operador1")
        print("  Senha: op123")
        print("\n⚠️  IMPORTANTE: Altere as senhas padrão após o primeiro login!")

if __name__ == '__main__':
    criar_usuarios_padrao()