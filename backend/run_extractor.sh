#!/bin/bash
# Script wrapper para rodar o extrator com as variáveis de ambiente corretas
# Ajuste o caminho se necessário

cd /workspace/backend

# Carregar variáveis de ambiente se houver um arquivo .env (opcional)
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Executar o script python
python3 extractor.py
