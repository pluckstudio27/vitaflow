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
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT app:create_app()`

### 3. Configurar Variáveis de Ambiente

No painel do Render, adicionar as seguintes variáveis:

```bash
# MongoDB
MONGO_URI=mongodb+srv://arthurkall_db_user:S8x9xKx0pgpqsIQ4@cluster0.wjr3t0h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGO_DB=almox_sms

# Flask
SECRET_KEY=your-production-secret-key-here
FLASK_ENV=production

# Banco de dados principal (SQLite/PostgreSQL)
DATABASE_URL=sqlite:///almox_sms.db
```

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
gunicorn -w 2 -b 0.0.0.0:5000 app:create_app()
```

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

## 📞 Suporte

Se encontrar problemas:

1. **Verificar logs do Render**
2. **Testar endpoints de health**
3. **Verificar variáveis de ambiente**
4. **Consultar documentação do Render**

---

**Status**: ✅ **Pronto para deploy!**

A aplicação está configurada e testada para deploy no Render com MongoDB Atlas.