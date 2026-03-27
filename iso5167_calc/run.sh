#!/bin/bash
echo ""
echo " ==================================================="
echo "  ISO 5167-2  Placa de Orifício — Calculadora"
echo " ==================================================="
echo ""
echo " [1/3] Instalando dependências..."
pip install -r requirements.txt --quiet
echo " [2/3] Iniciando servidor Flask na porta 5167..."
echo " [3/3] Acesse: http://localhost:5167"
echo ""
python app.py
