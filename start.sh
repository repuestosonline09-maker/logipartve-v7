#!/bin/bash

# Script de inicio para LogiPartVE en Railway
# Verifica y configura la conexión a PostgreSQL

echo "================================================"
echo "LogiPartVE Pro v7.0 - Iniciando en Railway"
echo "================================================"

# Mostrar información de debug
echo ""
echo "🔍 Verificando variables de entorno..."
echo ""

# Verificar DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL no está configurada"
    echo ""
    echo "Variables de entorno disponibles:"
    env | grep -i "database\|postgres\|pg" || echo "  (ninguna encontrada)"
    echo ""
    echo "⚠️  ADVERTENCIA: La aplicación usará SQLite (temporal)"
    echo "   Los datos se perderán al reiniciar el contenedor"
    echo ""
else
    echo "✅ DATABASE_URL detectado:"
    echo "   ${DATABASE_URL:0:30}..."
    echo ""
    echo "✅ La aplicación usará PostgreSQL (permanente)"
    echo ""
fi

# Mostrar información del sistema
echo "💻 Sistema: $(uname -s) $(uname -m)"
echo "🐍 Python: $(python3 --version)"
echo "📦 Streamlit: $(streamlit version 2>&1 | head -n 1)"
echo ""

echo "================================================"
echo "🚀 Iniciando aplicación..."
echo "================================================"
echo ""

# Iniciar Streamlit
exec streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
