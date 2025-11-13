# Proposta de Melhorias e Correções

## Visão Geral
- Framework `Flask` com Blueprints `main` e `auth`, MongoDB como persistência principal e templates Jinja bem estruturados.
- Áreas-chave para melhoria: segurança (CSRF, autenticação), autorização/escopo, erros e logging, desempenho em relatórios, UX front‑end, índices do banco, e testes/observabilidade.

## Segurança
- Remover backdoor de login em modo debug: linha de substituição em `auth.py:627-629`.
- Eliminar seed de usuário `admin` com senha padrão "admin" em produção: ajuste do seed em `extensions.py:109-136` para exigir senha via variável de ambiente (`INITIAL_ADMIN_PASSWORD`) apenas em desenvolvimento.
- Fortalecer CSRF:
  - Enforcar token em toda requisição mutante sob `/api/*` quando autenticado, independentemente de `Accept`/`is_json` em `blueprints/main.py:41-52`.
  - Rotacionar `session['csrf_token']` no login e após mudanças sensíveis (p.ex., `auth.py:109-110`, e após `login_user` em `blueprints/auth.py:89-96`).
- Cabeçalhos de segurança globais: adicionar `after_request` em `app.py` para `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, e uma CSP básica compatível com os recursos atuais.
- Rate limiting de login: mover de memória para armazenamento com expiração (Mongo/Redis) e validar IP atrás de proxy confiável (_evitar confiar cegamente em `X-Forwarded-For`_) em `blueprints/auth.py:12-44`.

## Autorização e Escopo
- Corrigir decoradores que fazem `int(...)` de IDs (quebram com `ObjectId`):
  - `require_central_access` `auth.py:741-745`, `require_almoxarifado_access` `auth.py:779-783`, `require_sub_almoxarifado_access` `auth.py:817-821`, `require_setor_access` `auth.py:849-853` — passar o ID bruto e delegar resolução aos métodos `can_access_*`.
- Ajustar `/api/relatorios/admin/consumo-gastos` para respeitar escopo:
  - `admin_central` deve filtrar por central do usuário; `secretario` pode ser global; `super_admin` global — `blueprints/main.py:991-1247`.

## Erros e Logging
- Handlers globais:
  - Adicionar `@app.errorhandler(404/500)` com resposta JSON quando `Accept` indicar JSON e templates `errors/404.html`, `errors/500.html` para HTML.
- Logging estruturado:
  - Configurar `logging` em `app.py:10-41` com nível por ambiente e `RotatingFileHandler` (ou saída JSON para observabilidade); incluir `exc_info=True` nos logs de erro.
  - Injetar `X-Request-ID` (gerado) por requisição e incluir nos logs.

## Desempenho e Relatórios
- Otimizar `/api/relatorios/admin/consumo-gastos`:
  - Migrar para um único `aggregate` com `$match` por período e `$group` por `produto_id` para consumo e gastos (via `$facet`), seguido de `$lookup` em `produtos`.
  - Adicionar paginação/limite e ordenação no pipeline; reduzir round‑trips por produto.
  - Tornar integração de IA assíncrona (fila/caching) ou opcional por botão, com timeout menor.
- Corrigir índice de `movimentacoes`: o índice atual é em `data` (`extensions.py:41`) mas o campo usado é `data_movimentacao` (`blueprints/main.py:1041`); ajustar índice para o campo correto e incluir chaves auxiliares (`tipo`, `produto_id`).

## UX Front‑end
- Logout consistente:
  - O JS em `templates/base.html:889-912` espera JSON, mas a rota devolve redirect (`blueprints/auth.py:112-118`). Alterar o JS para redirecionar diretamente para `/auth/logout`.
- Melhorar mensagens amigáveis (já há `friendlyErrorMessage`): adicionar mapeamentos para `409/422` nos endpoints que retornam validação, padronizando envelope de erro (`error.code`, `error.message`).

## Banco de Dados e Índices
- Garantir índices:
  - `usuarios(username)` já único (`extensions.py:38`); manter.
  - `movimentacoes(data_movimentacao, tipo, produto_id)`.
  - `listas_compras(usuario_id, created_at)` OK (`extensions.py:46-48`).
- Normalização de IDs: consolidar armazenamento de `id` sequencial vs `_id` string e minimizar conversões tardias; criar helpers únicos (já há `_find_by_id` em `blueprints/main.py:120-138`).

## Testes e Observabilidade
- Novos testes:
  - CSRF mutante sem header deve falhar para qualquer `Content-Type` em `/api/*`.
  - Escopo de relatórios administrativos por nível de acesso.
  - Decoradores sem `int(...)` aceitando `ObjectId`.
  - Logout fluxo de navegador.
- Health:
  - Adicionar `GET /health/app` com versão/uptime e `MONGO_AVAILABLE` — base em `blueprints/main.py:60-118`.

## Passos de Implementação
1. Segurança:
   - Remover backdoor, ajustar seed do admin, endurecer CSRF e cabeçalhos.
2. Autorização:
   - Corrigir decoradores e escopo dos relatórios.
3. Erros/Logging:
   - Handlers globais e configuração de logger.
4. Banco/Índices:
   - Atualizar `ensure_collections_and_indexes` e criar índices faltantes.
5. Relatórios:
   - Migrar endpoint para `aggregate` com paginação e filtros.
6. Front‑end:
   - Corrigir logout e padronizar tratamento de erros.
7. Testes/Health:
   - Adicionar casos de teste e endpoint de health app.

## Entregáveis
- Código atualizado em `auth.py`, `extensions.py`, `blueprints/main.py`, `app.py`, `templates/base.html`.
- Novos templates `errors/404.html` e `errors/500.html` (simples e coesos com `base.html`).
- Índices Mongo atualizados e script de migração segura para produção.
- Suite de testes ampliada cobrindo segurança, escopo e relatórios.

## Benefícios
- Reduz risco crítico (senha padrão e backdoor) e vazios de CSRF.
- Respostas de erro consistentes para APIs, com melhor observabilidade.
- Relatórios mais performáticos e escaláveis.
- UX de logout e mensagens mais previsíveis.

Confirma prosseguir com esta implementação?**