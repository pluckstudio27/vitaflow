"""
Modelo MongoDB para usuários do sistema
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from bson import ObjectId
from .base import BaseMongoModel


class UsuarioMongo(BaseMongoModel, UserMixin):
    """Modelo MongoDB para usuários do sistema com controle hierárquico de acesso"""
    
    collection_name = 'usuarios'
    
    # Níveis de acesso válidos
    NIVEIS_ACESSO = [
        'super_admin',      # Acesso total ao sistema
        'admin_central',    # Administrador de uma central específica
        'gerente_almox',    # Gerente de um almoxarifado específico
        'resp_sub_almox',   # Responsável por um sub-almoxarifado específico
        'operador_setor',   # Operador de um setor específico
    ]
    
    def __init__(self, **kwargs):
        # Validações específicas do usuário
        if 'nivel_acesso' in kwargs and kwargs['nivel_acesso'] not in self.NIVEIS_ACESSO:
            raise ValueError(f"Nível de acesso inválido: {kwargs['nivel_acesso']}")
        
        # Define valores padrão
        kwargs.setdefault('ativo', True)
        kwargs.setdefault('ultimo_login', None)
        
        super().__init__(**kwargs)
    
    @property
    def username(self):
        return self.data.get('username')
    
    @property
    def email(self):
        return self.data.get('email')
    
    @property
    def nome_completo(self):
        return self.data.get('nome_completo')
    
    @property
    def nivel_acesso(self):
        return self.data.get('nivel_acesso')
    
    @property
    def ativo(self):
        return self.data.get('ativo', True)
    
    @property
    def central_id(self):
        return self.data.get('central_id')
    
    @property
    def almoxarifado_id(self):
        return self.data.get('almoxarifado_id')
    
    @property
    def sub_almoxarifado_id(self):
        return self.data.get('sub_almoxarifado_id')
    
    @property
    def setor_id(self):
        return self.data.get('setor_id')
    
    @property
    def categoria_id(self):
        return self.data.get('categoria_id')
    
    @property
    def ultimo_login(self):
        return self.data.get('ultimo_login')
    
    @ultimo_login.setter
    def ultimo_login(self, value):
        self.data['ultimo_login'] = value
    
    @property
    def data_criacao(self):
        return self.data.get('data_criacao')
    
    @property
    def data_atualizacao(self):
        return self.data.get('data_atualizacao')
    
    def set_password(self, password: str):
        """Define a senha do usuário (hash)"""
        self.data['password_hash'] = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verifica se a senha está correta"""
        password_hash = self.data.get('password_hash')
        if not password_hash:
            return False
        return check_password_hash(password_hash, password)
    
    def update_ultimo_login(self):
        """Atualiza o timestamp do último login"""
        self.data['ultimo_login'] = datetime.utcnow()
        self.save()
    
    def is_super_admin(self) -> bool:
        """Verifica se o usuário é super admin"""
        return self.nivel_acesso == 'super_admin'
    
    def is_admin_central(self) -> bool:
        """Verifica se o usuário é admin de central"""
        return self.nivel_acesso in ['super_admin', 'admin_central']
    
    def is_gerente_almox(self) -> bool:
        """Verifica se o usuário é gerente de almoxarifado"""
        return self.nivel_acesso in ['super_admin', 'admin_central', 'gerente_almox']
    
    def can_manage_categoria(self, categoria_id: str) -> bool:
        """Verifica se o usuário pode gerenciar uma categoria específica"""
        if self.is_super_admin():
            return True
        
        # Verifica se tem categoria específica atribuída
        if self.categoria_id == categoria_id:
            return True
        
        # Verifica categorias específicas (many-to-many)
        categorias_especificas = self.data.get('categorias_especificas', [])
        return categoria_id in categorias_especificas
    
    def get_scope_filter(self) -> Dict[str, Any]:
        """Retorna filtro baseado no escopo do usuário"""
        if self.is_super_admin():
            return {}  # Acesso total
        
        filter_dict = {}
        
        if self.nivel_acesso == 'admin_central' and self.central_id:
            filter_dict['central_id'] = self.central_id
        elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado_id:
            filter_dict['almoxarifado_id'] = self.almoxarifado_id
        elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado_id:
            filter_dict['sub_almoxarifado_id'] = self.sub_almoxarifado_id
        elif self.nivel_acesso == 'operador_setor' and self.setor_id:
            filter_dict['setor_id'] = self.setor_id
        
        return filter_dict
    
    def get_hierarchy_path(self) -> str:
        """Retorna o caminho hierárquico completo do usuário"""
        if self.nivel_acesso == 'super_admin':
            return 'Sistema'
        
        try:
            # Importar modelos aqui para evitar importação circular
            from .estrutura import CentralMongo, AlmoxarifadoMongo, SubAlmoxarifadoMongo, SetorMongo
            
            if self.nivel_acesso == 'admin_central' and self.central_id:
                central = CentralMongo.find_by_id(self.central_id)
                if central:
                    return central.nome
            
            elif self.nivel_acesso == 'gerente_almox' and self.almoxarifado_id:
                almoxarifado = AlmoxarifadoMongo.find_by_id(self.almoxarifado_id)
                if almoxarifado:
                    central = CentralMongo.find_by_id(almoxarifado.central_id)
                    if central:
                        return f'{central.nome} > {almoxarifado.nome}'
            
            elif self.nivel_acesso == 'resp_sub_almox' and self.sub_almoxarifado_id:
                sub_almoxarifado = SubAlmoxarifadoMongo.find_by_id(self.sub_almoxarifado_id)
                if sub_almoxarifado:
                    almoxarifado = AlmoxarifadoMongo.find_by_id(sub_almoxarifado.almoxarifado_id)
                    if almoxarifado:
                        central = CentralMongo.find_by_id(almoxarifado.central_id)
                        if central:
                            return f'{central.nome} > {almoxarifado.nome} > {sub_almoxarifado.nome}'
            
            elif self.nivel_acesso == 'operador_setor' and self.setor_id:
                setor = SetorMongo.find_by_id(self.setor_id)
                if setor:
                    sub_almoxarifado = SubAlmoxarifadoMongo.find_by_id(setor.sub_almoxarifado_id)
                    if sub_almoxarifado:
                        almoxarifado = AlmoxarifadoMongo.find_by_id(sub_almoxarifado.almoxarifado_id)
                        if almoxarifado:
                            central = CentralMongo.find_by_id(almoxarifado.central_id)
                            if central:
                                return f'{central.nome} > {almoxarifado.nome} > {sub_almoxarifado.nome} > {setor.nome}'
        
        except Exception:
            # Em caso de erro, retorna mensagem padrão
            pass
        
        return 'Hierarquia não definida'
    
    def get_categorias_display(self) -> Dict[str, Any]:
        """Retorna uma representação das categorias para exibição na interface"""
        # Se é super admin ou admin central, tem acesso a todas
        if self.nivel_acesso in ['super_admin', 'admin_central']:
            return {'tipo': 'todas', 'texto': 'Todas', 'categorias': []}
        
        try:
            # Importar modelo aqui para evitar importação circular
            from .categoria import CategoriaProdutoMongo
            
            # Busca categorias específicas
            categorias_especificas_ids = self.data.get('categorias_especificas', [])
            categorias_especificas = []
            
            if categorias_especificas_ids:
                for cat_id in categorias_especificas_ids:
                    categoria = CategoriaProdutoMongo.find_by_id(cat_id)
                    if categoria:
                        categorias_especificas.append(categoria)
            
            if not categorias_especificas:
                # Se não tem categorias específicas, verifica se tem categoria principal
                if self.categoria_id:
                    categoria_principal = CategoriaProdutoMongo.find_by_id(self.categoria_id)
                    if categoria_principal:
                        return {
                            'tipo': 'principal', 
                            'texto': f'{categoria_principal.codigo}', 
                            'categorias': [categoria_principal]
                        }
                
                # Se não tem nem específicas nem principal, é "Todas" (apenas para admins)
                return {'tipo': 'todas', 'texto': 'Todas', 'categorias': []}
            
            # Tem categorias específicas
            if len(categorias_especificas) == 1:
                cat = categorias_especificas[0]
                return {
                    'tipo': 'especifica', 
                    'texto': f'{cat.codigo}', 
                    'categorias': categorias_especificas
                }
            else:
                # Múltiplas categorias específicas
                return {
                    'tipo': 'multiplas', 
                    'texto': f'{len(categorias_especificas)} categorias', 
                    'categorias': categorias_especificas
                }
        
        except Exception:
            # Em caso de erro, retorna padrão
            return {'tipo': 'todas', 'texto': 'Todas', 'categorias': []}
    
    @classmethod
    def find_by_username(cls, username: str) -> Optional['UsuarioMongo']:
        """Encontra usuário pelo username"""
        return cls.find_one({'username': username})
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional['UsuarioMongo']:
        """Encontra usuário pelo email"""
        return cls.find_one({'email': email})
    
    @classmethod
    def find_ativos(cls) -> List['UsuarioMongo']:
        """Retorna todos os usuários ativos"""
        return cls.find_many({'ativo': True})
    
    @classmethod
    def find_by_nivel_acesso(cls, nivel: str) -> List['UsuarioMongo']:
        """Encontra usuários por nível de acesso"""
        return cls.find_many({'nivel_acesso': nivel, 'ativo': True})
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        # Índices únicos
        collection.create_index('username', unique=True)
        collection.create_index('email', unique=True)
        
        # Índices compostos para performance
        collection.create_index([('nivel_acesso', 1), ('ativo', 1)])
        collection.create_index([('central_id', 1), ('ativo', 1)])
        collection.create_index([('almoxarifado_id', 1), ('ativo', 1)])
        collection.create_index([('sub_almoxarifado_id', 1), ('ativo', 1)])
        collection.create_index([('setor_id', 1), ('ativo', 1)])
        collection.create_index([('categoria_id', 1), ('ativo', 1)])
        collection.create_index('data_criacao')
        collection.create_index('ultimo_login')
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário, excluindo dados sensíveis"""
        result = super().to_dict()
        
        # Remove dados sensíveis
        result.pop('password_hash', None)
        
        return result
    
    def to_dict_full(self) -> Dict[str, Any]:
        """Converte para dicionário completo (para admin)"""
        return super().to_dict()


class LogAuditoriaMongo(BaseMongoModel):
    """Modelo MongoDB para log de auditoria"""
    
    collection_name = 'logs_auditoria'
    
    def __init__(self, **kwargs):
        kwargs.setdefault('data_acao', datetime.utcnow())
        super().__init__(**kwargs)
    
    @property
    def usuario_id(self):
        return self.data.get('usuario_id')
    
    @property
    def acao(self):
        return self.data.get('acao')
    
    @property
    def tabela(self):
        return self.data.get('tabela')
    
    @property
    def registro_id(self):
        return self.data.get('registro_id')
    
    @property
    def dados_anteriores(self):
        return self.data.get('dados_anteriores')
    
    @property
    def dados_novos(self):
        return self.data.get('dados_novos')
    
    @property
    def ip_usuario(self):
        return self.data.get('ip_usuario')
    
    @property
    def user_agent(self):
        return self.data.get('user_agent')
    
    @property
    def data_acao(self):
        return self.data.get('data_acao')
    
    @classmethod
    def log_acao(cls, usuario_id: str, acao: str, tabela: str, 
                 registro_id: str = None, dados_anteriores: dict = None,
                 dados_novos: dict = None, ip_usuario: str = None,
                 user_agent: str = None) -> 'LogAuditoriaMongo':
        """Cria um log de auditoria"""
        log = cls(
            usuario_id=usuario_id,
            acao=acao,
            tabela=tabela,
            registro_id=registro_id,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            ip_usuario=ip_usuario,
            user_agent=user_agent
        )
        return log.save()
    
    @classmethod
    def find_by_usuario(cls, usuario_id: str, limit: int = 50) -> List['LogAuditoriaMongo']:
        """Encontra logs por usuário"""
        return cls.find_many(
            {'usuario_id': usuario_id},
            limit=limit,
            sort=[('data_acao', -1)]
        )
    
    @classmethod
    def find_by_tabela(cls, tabela: str, limit: int = 50) -> List['LogAuditoriaMongo']:
        """Encontra logs por tabela"""
        return cls.find_many(
            {'tabela': tabela},
            limit=limit,
            sort=[('data_acao', -1)]
        )
    
    @classmethod
    def create_indexes(cls):
        """Cria índices para otimizar consultas"""
        collection = cls.get_collection()
        
        collection.create_index([('usuario_id', 1), ('data_acao', -1)])
        collection.create_index([('tabela', 1), ('data_acao', -1)])
        collection.create_index([('acao', 1), ('data_acao', -1)])
        collection.create_index('data_acao')
        collection.create_index('registro_id')