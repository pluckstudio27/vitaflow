#!/bin/bash
# Script de deploy para Render
# Executa inicialização do banco e inicia a aplicação

echo "🚀 Iniciando deploy da aplicação Almox SMS..."

# Executa a inicialização do banco de dados
echo "🔄 Executando inicialização do banco de dados..."
python start.py

# Verifica se a inicialização foi bem-sucedida
if [ $? -eq 0 ]; then
    echo "✅ Inicialização concluída com sucesso!"
    echo "🌐 Iniciando servidor Gunicorn..."
    
    # Inicia o Gunicorn
    exec gunicorn -w 2 -b 0.0.0.0:$PORT app:app
else
    echo "❌ Falha na inicialização do banco de dados"
    exit 1
fi