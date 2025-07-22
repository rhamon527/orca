#!/bin/bash
# Script para iniciar o sistema e exibir link de acesso universal
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "==================================================="
echo "Acesse o sistema em qualquer PC da rede:"
echo "http://$IP:5000/login"
echo "==================================================="
python3 app.py
