PRD • PluckLog — Sistema de Gestão de Almoxarifado e Setores

Versão: 1.0
Data: 2025-12-13

1. Visão Geral
- PluckLog é um sistema web para gestão de estoque hospitalar/organizacional com múltiplos níveis (Central, Almoxarifado, Sub‑Almoxarifado, Setor), controle de movimentações, demandas, recebimento, lotes e relatórios operacionais em tempo real.
- Frontend em React UMD montado em templates Flask; backend em Flask com persistência principal em MongoDB e autenticação de usuários.

2. Objetivos
- Centralizar requisições e transferências de materiais entre níveis de estoque.
- Oferecer visibilidade do consumo por setor e status de lotes (validade).
- Padronizar processos de recebimento, atendimento de demandas e saídas com trilha de auditoria.
- Garantir segurança e escopo de acesso conforme nível de usuário.

3. Escopo
- Incluso: autenticação, dashboard, demandas (solicitação e gerência), movimentações (consulta e filtros), estoque por setor, registro de consumo diário, recebimento de produto, hierarquia de locais, utilidades de backup e restauração.
- Excluído nesta versão: integração a ERPs externos, faturamento, ordens de compra, workflow de aprovação multinível fora da gerência de demandas.

4. Personas e Níveis de Acesso
- Super Admin: administração global.
- Admin Central: gestão por central.
- Gerente Almox: gestão de almoxarifados vinculados à central.
- Responsável Sub‑Almox: gestão de sub‑almoxarifados.
- Operador Setor: visualização e operação do seu setor (estoque, consumo, lotes).

5. Requisitos Funcionais
- Autenticação
  - Login via formulário em `/auth/login` com CSRF e rate limit básico.
  - Verificação de sessão em `/auth/check-session`.
- Demandas (Usuário)
  - Criar demanda única ou por lista com produto, quantidade, destino e observações.
  - Gerenciar rascunho: adicionar, remover, limpar e finalizar lista.
  - Consultar “Minhas Demandas” com busca.
- Demandas (Gerência)
  - Visualizar pendentes e resolvidas; abrir modal para atender.
  - Selecionar origem (tipo/local), informar quantidade e enviar para setor.
  - Suporte a atendimento parcial e total; atualização de status.
- Movimentações
  - Listar com paginação e filtros: tipo, produto, intervalo de datas e incremental `updated_since`.
  - Ver detalhes padronizados: produto, quantidade, origem/destino, responsável, motivo.
- Operador • Setor
  - Selecionar produto e visualizar estoque do próprio setor (total, disponível, reservado; data de atualização).
  - Visualizar “Resumo do dia” (recebido por origem, usado, disponível).
  - Exibir lotes com validade, status de vencimento (válido, vence em X dias, vencido).
  - Registrar consumo diário do produto no setor.
- Recebimento de Produto
  - Selecionar produto, almoxarifado, quantidades e metadados (preço, lote, fornecedor, datas, nota).
  - Confirmar e registrar recebimento.
- Hierarquia e Configurações
  - Visualizar e operar hierarquia de locais e relacionamentos (Central ↔ Almox ↔ Sub ↔ Setor).
  - Ferramentas administrativas: backup, restauração, agendamento, reset controlado.

6. Requisitos Não Funcionais
- Segurança: cabeçalhos de segurança, CSRF em formulários, escopo de acesso por central e nível.
- Confiabilidade: validações de dados e fallback para cenários sem Mongo em preview local.
- Desempenho: caching leve de respostas e pré‑buscas em lote para reduzir N+1.
- Usabilidade: componentes com estados de carregamento, feedbacks e filtros rápidos.

7. Fluxos Principais
- Solicitar demanda
  - Usuário escolhe produto, quantidade, destino preferencial e observações; envia demanda ou adiciona a lista; finaliza quando pronto.
- Atender demanda
  - Gerência abre demanda, escolhe origem e local com disponibilidade; define quantidade; executa transferência; status muda para atendido/parcial.
- Registrar consumo de setor
  - Operador seleciona produto, informa quantidade usada no dia; sistema atualiza resumo e estoque.
- Receber produto
  - Responsável seleciona produto e almox; informa dados de recebimento; confirma; estoque é atualizado.
- Consultar movimentações
  - Usuário filtra por tipo, produto e período; navega por paginação e visualiza detalhes.

8. Principais Endpoints de API
- Movimentações
  - `GET /api/movimentacoes` com `per_page`, `page`, `tipo`, `produto`, `data_inicio`, `data_fim`, `updated_since`.
  - `POST /api/movimentacoes/transferencia` para atender demanda com origem/destino e motivo.
- Demandas
  - `GET /api/demandas` com filtros `status`, `mine`, `per_page`.
  - `POST /api/demandas` para criar demanda unitária.
  - `GET/POST/DELETE /api/demandas/lista` e `POST /api/demandas/finalizar` para lista de rascunho.
  - `PUT /api/demandas/{id}` para atualizar status e quantidades atendidas.
- Produtos
  - `GET /api/produtos` com busca; `GET /api/produtos/{id}/estoque`; `GET /api/produtos/{id}/lotes`.
  - `POST /api/produtos/{id}/recebimento` para registrar recebimento.
- Setores
  - `GET /api/setores` e `GET /api/setores/{id}`.
  - `GET /api/setores/{id}/produtos/{pid}/resumo-dia`.
- Setor • Registro de consumo
  - `POST /api/setor/registro` com `{ produto_id, saida_dia }`.
- Autenticação
  - `GET/POST /auth/login`, `GET /auth/check-session`.

9. Regras de Negócio
- Escopo por Central
  - Usuários abaixo de Super Admin só acessam dados da central derivada do seu vínculo; buscas e listagens respeitam esse escopo.
- Estoque Disponível e Reservado
  - Disponível deriva de quantidade atual menos reservas; exibição detalha total, disponível e reservado com unidade.
- Atendimento de Demanda
  - Transferência que cobre 100% da quantidade solicitada muda status para “atendido”; menor que 100% resulta em “parcialmente_atendido”.
  - Grupo de itens admite atendimento item a item com validação de disponibilidade por origem/local.
- Origem de Transferência
  - Origem válida para envio não pode ser “setor”; somente níveis acima com disponibilidade positiva.
- Validade de Lotes
  - Status calculado por diferença de dias para vencimento: vencido (<0), próximo (≤30), válido (>30).

10. Estruturas de Dados (conceituais)
- Produto: id, nome, código, unidade, central_id.
- Estoque: tipo (central/almox/sub/setor), local_id, nome_local, quantidade, quantidade_disponível, data_atualização.
- Lote: número_lote, produto_id, local_tipo/local_id, quantidade_atual, datas de fabricação e vencimento, observações.
- Movimentação: produto_id, quantidade, tipo_movimentação, origem/destino (tipo/id/nome), usuário, data, motivo, observações.
- Demanda: id/display_id, produto_id/nome, setor_id/nome, quantidade_solicitada, destino_tipo, status, items (grupo).

11. Métricas e Indicadores
- Consumo médio por setor (média móvel 7 dias).
- Tempo de atendimento de demandas (pendente → resolvida).
- Percentual de atendimento parcial vs total.
- Quantidades recebidas e saídas por nível.
- Lotes vencidos e próximos do vencimento.

12. Critérios de Aceitação (exemplos)
- Usuário consegue criar demanda, vê rascunho e finalizar, e a demanda aparece em “Minhas Demandas”.
- Gerência consegue abrir demanda, selecionar origem e local com disponibilidade, executar transferência e ver status atualizado.
- Operador visualiza estoque e lotes do seu setor após escolher produto; consegue registrar consumo e ver resumo do dia atualizado.
- Listagem de movimentações respeita escopo e filtros, retornando dados coerentes com período e tipo.

13. Restrições e Suposições
- Persistência principal em MongoDB; rotas devem lidar com indisponibilidade em ambiente de preview.
- IDs podem existir em formato sequencial e ObjectId; sistema resolve candidatos de id conforme contexto.
- Navegador pode cancelar requisições durante navegação; frontend deve tratar estados de carregamento/erro.

14. Riscos e Mitigações
- Inconsistência de escopo por central
  - Mitigar com filtros no backend e verificações de acesso por usuário.
- Cancelamento de requisições (ERR_ABORTED)
  - Mitigar com UX que evita navegação durante carregamento e tratamento de reintentos quando aplicável.
- Dados incompletos entre níveis
  - Mitigar com fallbacks (consultas hierárquicas) e mensagens claras ao usuário.

15. Roadmap (alto nível)
- Integrações externas (ERP/Compras) e webhook de eventos.
- Painéis analíticos avançados e exportações customizadas.
- Aprimorar regras de atendimento em grupo com otimização de origem/múltiplos locais.
- Auditoria detalhada e trilha de aprovação opcional em demandas.

16. Referências Técnicas
- Login: `templates/auth/login.html:170` e `assets/react-app.js:980`.
- Operador Setor: `templates/operador/setor.html:491` e `assets/react-app.js:1237`.
- Demandas (Usuário): `templates/demandas/index.html:145` e `assets/react-app.js:1093`.
- Demandas (Gerência): `templates/demandas/gerencia.html:809` e `assets/react-app.js:939`.
- API Movimentações: `blueprints/main.py:6393`.
