# Config package for ALMOX-SMS
# This file makes the config directory a Python package

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configuração do banco de dados principal - MongoDB
    USE_MONGODB_PRIMARY = True
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/'
    MONGO_DB = os.environ.get('MONGO_DB') or 'almox_sms'
    
    # Configuração SQLAlchemy (mantido para compatibilidade/fallback)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///almox_sms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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

class DevelopmentConfig(Config):
    DEBUG = True
    # MongoDB para desenvolvimento
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/'
    MONGO_DB = os.environ.get('MONGO_DB') or 'almox_sms_dev'
    # SQLAlchemy como fallback
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///almox_sms_dev.db'

class ProductionConfig(Config):
    DEBUG = False
    # MongoDB para produção
    MONGO_URI = os.environ.get('MONGO_URI')  # Deve ser definido em produção
    MONGO_DB = os.environ.get('MONGO_DB') or 'almox_sms'
    # SQLAlchemy como fallback (PostgreSQL em produção)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://username:password@localhost/almox_sms'
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True  # Requer HTTPS
    REMEMBER_COOKIE_SECURE = True  # Requer HTTPS

class TestingConfig(Config):
    TESTING = True
    # MongoDB para testes (banco separado)
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/'
    MONGO_DB = 'almox_sms_test'
    # SQLAlchemy para testes (em memória)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}