"""
Sistema de Configuração de Blocos de Interface
Permite personalizar a interface baseada no nível de acesso do usuário
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AccessLevel(Enum):
    """Níveis de acesso do sistema"""
    SUPER_ADMIN = 'super_admin'
    ADMIN_CENTRAL = 'admin_central'
    GERENTE_ALMOX = 'gerente_almox'
    RESP_SUB_ALMOX = 'resp_sub_almox'
    OPERADOR_SETOR = 'operador_setor'

@dataclass
class MenuBlock:
    """Configuração de um bloco de menu"""
    id: str
    label: str
    icon: str
    url: Optional[str] = None
    access_levels: List[AccessLevel] = None
    children: List['MenuBlock'] = None
    active_endpoints: List[str] = None
    
    def __post_init__(self):
        if self.access_levels is None:
            self.access_levels = list(AccessLevel)
        if self.children is None:
            self.children = []
        if self.active_endpoints is None:
            self.active_endpoints = []

@dataclass
class DashboardWidget:
    """Configuração de um widget do dashboard"""
    id: str
    title: str
    template: str
    size: str = 'lg-6'  # Bootstrap column size
    access_levels: List[AccessLevel] = None
    priority: int = 0  # Ordem de exibição
    
    def __post_init__(self):
        if self.access_levels is None:
            self.access_levels = list(AccessLevel)

@dataclass
class PageSection:
    """Configuração de uma seção de página"""
    id: str
    title: str
    content: str
    icon: str = 'fas fa-cog'
    size: str = 'lg-6'
    access_levels: List[AccessLevel] = None
    action_url: Optional[str] = None
    action_text: str = 'Acessar'
    
    def __post_init__(self):
        if self.access_levels is None:
            self.access_levels = list(AccessLevel)

class UIBlocksConfig:
    """Configuração central dos blocos de interface"""
    
    def __init__(self):
        self._menu_blocks = self._init_menu_blocks()
        self._dashboard_widgets = self._init_dashboard_widgets()
        self._settings_sections = self._init_settings_sections()
    
    def _init_menu_blocks(self) -> List[MenuBlock]:
        """Inicializa a configuração dos blocos de menu"""
        return [
            MenuBlock(
                id='dashboard',
                label='Dashboard',
                icon='fas fa-home',
                url='main.index',
                active_endpoints=['main.index']
            ),
            MenuBlock(
                id='produtos_gerenciar',
                label='Gerenciar Produtos',
                icon='fas fa-list',
                url='main.produtos',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX
                ],
                active_endpoints=['main.produtos']
            ),
            MenuBlock(
                id='produtos_estoque',
                label='Consultar Estoque',
                icon='fas fa-warehouse',
                url='main.estoque',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX,
                    AccessLevel.RESP_SUB_ALMOX
                ],
                active_endpoints=['main.estoque']
            ),
            MenuBlock(
                id='movimentacoes',
                label='Movimentações',
                icon='fas fa-exchange-alt',
                url='main.movimentacoes',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX,
                    AccessLevel.RESP_SUB_ALMOX
                ],
                active_endpoints=['main.movimentacoes']
            ),
            # Página do Operador de Setor para gestão diária
            MenuBlock(
                id='operador_setor',
                label='Gestão do Setor',
                icon='fas fa-warehouse',
                url='main.operador_setor_pagina',
                access_levels=[
                    AccessLevel.OPERADOR_SETOR
                ],
                active_endpoints=['main.operador_setor_pagina']
            ),
            MenuBlock(
                id='demandas',
                label='Demandas',
                icon='fas fa-clipboard-list',
                url='main.demandas',
                access_levels=[
                    AccessLevel.OPERADOR_SETOR
                ],
                active_endpoints=['main.demandas']
            ),
            MenuBlock(
                id='demandas_gerencia',
                label='Demandas • Gerência',
                icon='fas fa-tasks',
                url='main.demandas_gerencia',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX
                ],
                active_endpoints=['main.demandas_gerencia']
            ),
            MenuBlock(
                id='relatorios',
                label='Relatórios',
                icon='fas fa-chart-bar',
                url='main.relatorios',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX
                ],
                active_endpoints=['main.relatorios']
            ),
            MenuBlock(
                id='configuracoes',
                label='Configurações',
                icon='fas fa-cog',
                url='main.configuracoes',
                active_endpoints=['main.configuracoes', 'main.configuracoes_hierarquia', 'main.users']
            )
        ]
    
    def _init_dashboard_widgets(self) -> List[DashboardWidget]:
        """Inicializa a configuração dos widgets do dashboard"""
        return [
            DashboardWidget(
                id='stats_general',
                title='Estatísticas Gerais',
                template='blocks/widgets/stats_general.html',
                size='lg-3',
                priority=1
            ),
            DashboardWidget(
                id='estoque_baixo',
                title='Estoque Baixo',
                template='blocks/widgets/estoque_baixo.html',
                size='lg-3',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX,
                    AccessLevel.RESP_SUB_ALMOX
                ],
                priority=2
            ),
            DashboardWidget(
                id='movimentacoes_recentes',
                title='Movimentações Recentes',
                template='blocks/widgets/movimentacoes_recentes.html',
                size='lg-6',
                priority=3
            ),
            DashboardWidget(
                id='usuarios_stats',
                title='Estatísticas de Usuários',
                template='blocks/widgets/usuarios_stats.html',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL
                ],
                priority=4
            ),
            DashboardWidget(
                id='hierarquia_usuario',
                title='Hierarquia do Usuário',
                template='blocks/widgets/hierarquia_usuario.html',
                size='lg-6',
                priority=5
            ),
            DashboardWidget(
                id='acoes_rapidas',
                title='Ações Rápidas',
                template='blocks/widgets/acoes_rapidas.html',
                size='lg-6',
                priority=6
            )
        ]
    
    def _init_settings_sections(self) -> List[PageSection]:
        """Inicializa as seções da página de configurações"""
        return [
            PageSection(
                id='hierarquia',
                title='Hierarquia Organizacional',
                content='Gerencie a estrutura hierárquica: Centrais, Almoxarifados, Sub-Almoxarifados e Setores.',
                icon='fas fa-sitemap',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL
                ],
                action_url='main.configuracoes_hierarquia',
                action_text='Gerenciar Hierarquia'
            ),
            PageSection(
                id='usuarios',
                title='Gerenciamento de Usuários',
                content='Adicione, edite e gerencie usuários do sistema com diferentes níveis de acesso.',
                icon='fas fa-users',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL
                ],
                action_url='main.configuracoes_usuarios',
                action_text='Gerenciar Usuários'
            ),
            PageSection(
                id='categorias',
                title='Categorias de Produtos',
                content='Configure as categorias de produtos disponíveis no sistema.',
                icon='fas fa-tags',
                access_levels=[
                    AccessLevel.SUPER_ADMIN,
                    AccessLevel.ADMIN_CENTRAL,
                    AccessLevel.GERENTE_ALMOX
                ],
                action_url='main.configuracoes_categorias',
                action_text='Gerenciar Categorias'
            ),
            PageSection(
                id='sistema',
                title='Configurações do Sistema',
                content='Configure parâmetros gerais do sistema, backup, logs e manutenção.',
                icon='fas fa-cogs',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN
                ],
                action_url='#',
                action_text='Configurar Sistema'
            ),
            PageSection(
                id='auditoria',
                title='Auditoria e Logs',
                content='Visualize logs de sistema, auditoria de ações e relatórios de segurança.',
                icon='fas fa-clipboard-list',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN
                ],
                action_url='#',
                action_text='Ver Auditoria'
            ),
            PageSection(
                id='backup',
                title='Backup e Restauração',
                content='Gerencie backups automáticos, restauração de dados e arquivamento.',
                icon='fas fa-database',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN
                ],
                action_url='#',
                action_text='Gerenciar Backup'
            ),
            PageSection(
                id='integracao',
                title='Integrações Externas',
                content='Configure APIs, webhooks e integrações com sistemas externos.',
                icon='fas fa-plug',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN
                ],
                action_url='#',
                action_text='Configurar APIs'
            ),
            PageSection(
                id='relatorios_admin',
                title='Relatórios Administrativos',
                content='Acesse relatórios detalhados de uso, performance e estatísticas do sistema.',
                icon='fas fa-chart-bar',
                size='lg-6',
                access_levels=[
                    AccessLevel.SUPER_ADMIN
                ],
                action_url='main.relatorios',
                action_text='Ver Relatórios'
            ),
            PageSection(
                id='perfil',
                title='Meu Perfil',
                content='Edite suas informações pessoais e configurações de conta.',
                icon='fas fa-user-edit',
                size='lg-6',
                action_url='auth.profile',
                action_text='Editar Perfil'
            )
        ]
    
    def get_menu_blocks_for_user(self, user_level: str) -> List[MenuBlock]:
        """Retorna os blocos de menu disponíveis para o nível do usuário"""
        try:
            access_level = AccessLevel(user_level)
        except ValueError:
            return []
        
        filtered_blocks = []
        for block in self._menu_blocks:
            if access_level in block.access_levels:
                # Filtrar filhos também
                filtered_children = [
                    child for child in block.children
                    if access_level in child.access_levels
                ]
                
                # Criar uma cópia do bloco com filhos filtrados
                filtered_block = MenuBlock(
                    id=block.id,
                    label=block.label,
                    icon=block.icon,
                    url=block.url,
                    access_levels=block.access_levels,
                    children=filtered_children,
                    active_endpoints=block.active_endpoints
                )
                filtered_blocks.append(filtered_block)
        
        return filtered_blocks
    
    def get_dashboard_widgets_for_user(self, user_level: str) -> List[DashboardWidget]:
        """Retorna os widgets do dashboard disponíveis para o nível do usuário"""
        try:
            access_level = AccessLevel(user_level)
        except ValueError:
            return []
        
        filtered_widgets = [
            widget for widget in self._dashboard_widgets
            if access_level in widget.access_levels
        ]
        
        # Ordenar por prioridade
        return sorted(filtered_widgets, key=lambda w: w.priority)
    
    def get_settings_sections_for_user(self, user_level: str) -> List[PageSection]:
        """Retorna as seções de configurações disponíveis para o nível do usuário"""
        try:
            access_level = AccessLevel(user_level)
        except ValueError:
            return []
        
        return [
            section for section in self._settings_sections
            if access_level in section.access_levels
        ]

# Instância global da configuração
ui_blocks_config = UIBlocksConfig()

def get_ui_blocks_config() -> UIBlocksConfig:
    """Retorna a instância da configuração de blocos"""
    return ui_blocks_config