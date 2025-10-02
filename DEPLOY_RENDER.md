# Deploy no Render com MongoDB Atlas

Este guia detalha como fazer o deploy da aplicação ALMOX-SMS no Render usando MongoDB Atlas como banco de dados.

## ✅ Preparação Concluída

As seguintes modificações já foram implementadas no código:

### 1. Integração MongoDB
- ✅ Adicionado `pymongo` ao `requirements.txt`
- ✅ Criado sistema de inicialização MongoDB em `extensions.py`
- ✅ Adicionado chamada `init_mongo()` em `app.py`
- ✅ Criado endpoint de healthcheck `/health/mongo`
- ✅ Criado endpoint de teste `/test/mongo`
- ✅ Configurações MongoDB adicionadas à classe `Config`

### 2. Configuração para Deploy
- ✅ Adicionado `gunicorn` ao `requirements.txt`
- ✅ Adicionado `Flask-Login==0.6.3` ao `requirements.txt`
- ✅ Adicionado `Werkzeug==2.3.7` ao `requirements.txt`
- ✅ Criado `Procfile` para Render
- ✅ Criado arquivo `.env` com configurações

## 🚀 Passos para Deploy no Render

### 1. Configurar MongoDB Atlas

1. **Criar conta no MongoDB Atlas**: https://cloud.mongodb.com/
2. **Criar um cluster gratuito**
3. **Configurar acesso**:
   - Adicionar IP `0.0.0.0/0` (permitir de qualquer lugar)
   - Criar usuário de banco de dados
4. **Obter string de conexão**:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
   ```

### 2. Configurar Render

1. **Criar conta no Render**: https://render.com/
2. **Conectar repositório GitHub**
3. **Criar Web Service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python start.py && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`

### 3. Configurar Variáveis de Ambiente

No painel do Render, configure as seguintes variáveis de ambiente:

#### Variáveis Obrigatórias:
- `FLASK_ENV`: `production`
- `SECRET_KEY`: Uma chave secreta forte (gere uma nova para produção)
- `MONGO_URI`: URI de conexão do MongoDB (ex: `mongodb+srv://user:password@cluster.mongodb.net/`)
- `MONGO_DB`: Nome do banco de dados MongoDB (ex: `almox_sms`)

#### Observações Importantes:
- **MongoDB Apenas**: A aplicação em produção usa APENAS MongoDB (sem PostgreSQL)
- **Python 3.13**: Configuração otimizada para compatibilidade com Python 3.13 no Render
- **Sem psycopg2**: Removido para evitar conflitos de compilação no ambiente Render

```bash
# Flask (OBRIGATÓRIO)
FLASK_ENV=production
SECRET_KEY=your-production-secret-key-here

# MongoDB (OBRIGATÓRIO - URI deve incluir o nome do banco)
MONGO_URI=mongodb+srv://arthurkall_db_user:S8x9xKx0pgpqsIQ4@cluster0.wjr3t0h.mongodb.net/almox_sms?retryWrites=true&w=majority
MONGO_DB=almox_sms
```

**⚠️ IMPORTANTE:** 
- A variável `FLASK_ENV=production` é obrigatória para usar a configuração correta
- A `MONGO_URI` deve incluir o nome do banco (`/almox_sms`) antes dos parâmetros de query
- O Render detecta automaticamente a porta através da variável `$PORT`

### 4. Deploy

1. **Fazer push para GitHub**
2. **Render fará deploy automaticamente**
3. **Verificar logs de deploy**
4. **Testar endpoints**:
   - `https://your-app.onrender.com/health/mongo`
   - `https://your-app.onrender.com/test/mongo`

## 🧪 Testes Locais

### Healthcheck MongoDB
```bash
curl http://127.0.0.1:5000/health/mongo
```

**Resposta esperada:**
```json
{
  "db": "almox_sms",
  "mongo_ok": true
}
```

### Teste Completo
```bash
curl http://127.0.0.1:5000/test/mongo
```

**Resposta esperada:**
```json
{
  "database": "almox_sms",
  "documento_inserido": "ObjectId(...)",
  "documento_lido": {
    "app": "almox-sms",
    "teste": "deploy_render",
    "timestamp": "2025-10-01T12:32:51.259000"
  },
  "mongo_ok": true,
  "total_documentos": 1
}
```

## 📁 Estrutura de Arquivos Adicionados

```
almox-sms/
├── .env                    # Variáveis de ambiente locais
├── Procfile               # Configuração Render
├── DEPLOY_RENDER.md       # Este arquivo
├── test_mongo.py          # Script de teste independente
├── debug_env.py           # Script de debug
├── extensions.py          # ✅ Modificado - MongoDB
├── config/__init__.py     # ✅ Modificado - Config MongoDB
├── blueprints/main.py     # ✅ Modificado - Endpoints teste
├── app.py                 # ✅ Modificado - init_mongo()
└── requirements.txt       # ✅ Modificado - pymongo, gunicorn
```

## 🔧 Comandos Úteis

### Testar conexão local
```bash
python test_mongo.py
```

### Debug variáveis de ambiente
```bash
python debug_env.py
```

### Executar servidor local
```bash
python app.py
```

### Executar com Gunicorn (produção)
```bash
# Comando usado pelo Render (via Procfile)
gunicorn -w 2 -b 0.0.0.0:$PORT app:app

# Para teste local com Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### Testar aplicação localmente
```bash
# Desenvolvimento
python app.py

# Produção local
FLASK_ENV=production python app.py
```

## Resolução de Problemas

### Erro psycopg2 com Python 3.13
Se encontrar erro relacionado ao psycopg2:
- ✅ **Resolvido**: psycopg2-binary foi removido do requirements.txt
- ✅ **Configuração**: Produção usa apenas MongoDB (USE_MONGODB_PRIMARY=True)
- ✅ **Compatibilidade**: Otimizado para Python 3.13 no Render

### Verificação de Deploy
1. Confirme que `FLASK_ENV=production` está configurado
2. Verifique se `MONGO_URI` está correto e acessível
3. Confirme que não há referências ao PostgreSQL nos logs

## 🎯 Próximos Passos

1. **Fazer push para GitHub**
2. **Configurar Render Web Service**
3. **Adicionar variáveis de ambiente**
4. **Testar deploy**
5. **Configurar domínio personalizado (opcional)**

## 🔒 Segurança

- ✅ Variáveis sensíveis em variáveis de ambiente
- ✅ Configurações diferentes para desenvolvimento/produção
- ✅ MongoDB com autenticação
- ✅ Conexões SSL/TLS

## 🔧 Troubleshooting

### Problemas Comuns e Soluções

#### 1. Erro: "ModuleNotFoundError: No module named 'flask_login'"
**Solução**: ✅ **CORRIGIDO** - Adicionado `Flask-Login==0.6.3` ao `requirements.txt`

#### 2. Erro: "ModuleNotFoundError: No module named 'werkzeug'"
**Solução**: ✅ **CORRIGIDO** - Adicionado `Werkzeug==2.3.7` ao `requirements.txt`

#### 3. Erro: "MongoDB URI options are key=value pairs"
**Solução**: ✅ **CORRIGIDO** - Removido parâmetro `appName` do MongoDB URI
- URI correto: `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority`
- Evitar parâmetros que podem causar problemas de parsing no PyMongo

#### 4. Erro de conexão MongoDB
**Verificar**:
- String de conexão `MONGO_URI` está correta
- IP `0.0.0.0/0` está liberado no MongoDB Atlas
- Usuário e senha estão corretos

#### 5. Erro: "AttributeError: module 'app' has no attribute 'app'"
**Solução**: ✅ **CORRIGIDO** - Modificado `app.py` para incluir instância `app` no nível do módulo
- `Procfile` atualizado para: `web: gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
- Aplicação agora funciona tanto com factory function quanto com instância direta

#### 6. Erro: "Usuário ou senha inválidos" - Admin não existe após deploy
**Solução**: ✅ **CORRIGIDO** - Adicionado script de inicialização automática
- `Procfile` atualizado para: `web: python start.py && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
- Script `start.py` cria automaticamente o usuário admin no primeiro deploy
- **Credenciais padrão**: usuário `admin`, senha `admin123`
- ⚠️ **IMPORTANTE**: Altere a senha após o primeiro login!

**Criação manual (se necessário)**:
```bash
# No console do Render ou localmente
python -c "
from app import create_app
from models.usuario import Usuario
from extensions import db

app = create_app()
with app.app_context():
    admin = Usuario(
        username='admin',
        email='admin@almoxsms.com',
        nome_completo='Administrador do Sistema',
        nivel_acesso='super_admin',
        ativo=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print('Admin criado com sucesso!')
"
```

#### 7. Aplicação não inicia
**Verificar**:
- `Procfile` está correto: `web: python start.py && gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
- Todas as variáveis de ambiente estão configuradas
- Build command: `pip install -r requirements.txt`

## 📞 Suporte

Se encontrar problemas:

1. **Verificar logs do Render**
2. **Testar endpoints de health**
3. **Verificar variáveis de ambiente**
4. **Consultar documentação do Render**

---

**Status**: ✅ **Pronto para deploy!**

A aplicação está configurada e testada para deploy no Render com MongoDB Atlas.