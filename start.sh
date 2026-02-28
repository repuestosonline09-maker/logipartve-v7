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

# ============================================================
# Inyectar meta tags SEO en el index.html de Streamlit
# ============================================================
STREAMLIT_INDEX=$(python3 -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static', 'index.html'))")

if [ -f "$STREAMLIT_INDEX" ]; then
    echo "Inyectando meta tags SEO en: $STREAMLIT_INDEX"
    sed -i 's|<title>App</title>|<title>LogiPartVE - Cotizador Global de Repuestos</title>\n    <meta name="description" content="LogiPartVE es el sistema profesional de cotizacion y asesoria de autopartes importadas. Cotizaciones precisas en dolares con calculo de flete, impuestos y diferencial cambiario para Venezuela." />\n    <meta name="keywords" content="cotizador repuestos, autopartes Venezuela, importacion repuestos, cotizacion autopartes, LogiPartVE" />\n    <meta name="robots" content="index, follow" />\n    <meta property="og:title" content="LogiPartVE - Cotizador Global de Repuestos" />\n    <meta property="og:description" content="Sistema profesional de cotizacion de autopartes importadas para Venezuela." />\n    <meta property="og:url" content="https://www.logipartve.com" />\n    <meta property="og:type" content="website" />|g' "$STREAMLIT_INDEX"
    echo "Meta tags SEO inyectados correctamente."
else
    echo "ADVERTENCIA: No se encontro el index.html de Streamlit"
fi

# Iniciar Streamlit con puerto correcto
exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
