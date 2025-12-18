# Config package for ALMOX-SMS
# This file makes the config directory a Python package

import os
from pathlib import Path
from dotenv import load_dotenv

# Sempre carregar o .env da raiz do projeto para evitar confusão com diretórios duplicados
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configuração de banco de dados RELACIONAL (mantido apenas para compatibilidade)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///almox_sms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuração de banco de dados MongoDB (persistência oficial)
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/almox_sms'
    MONGO_DB = os.environ.get('MONGO_DB') or 'almox_sms'
    
    # Configurações da aplicação
    ITEMS_PER_PAGE = 20
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de sessão
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora em segundos
    
    # Configurações de cookies de lembrar
    REMEMBER_COOKIE_DURATION = 86400 * 7  # 7 dias em segundos
    REMEMBER_COOKIE_SECURE = False  # True em produção com HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    # Controles de segurança dinâmicos
    DISABLE_LOGIN_RATE_LIMIT = True  # Pode ser sobrescrito em produção
    # Permitir fallback de banco simulado em dev/test
    ALLOW_MOCK_DB = True
    # Permitir leitura pública de endpoints GET da API em dev/test
    ALLOW_PUBLIC_API_READ = True
    # Desabilitar CSRF para JSON em dev/test
    DISABLE_API_CSRF = True

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///almox_sms_dev.db'

class ProductionConfig(Config):
    DEBUG = False
    # Em produção, use PostgreSQL ou outro banco robusto
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://username:password@localhost/almox_sms'
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True  # Requer HTTPS
    REMEMBER_COOKIE_SECURE = True  # Requer HTTPS
    DISABLE_LOGIN_RATE_LIMIT = False
    ALLOW_MOCK_DB = False
    ALLOW_PUBLIC_API_READ = False
    DISABLE_API_CSRF = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
