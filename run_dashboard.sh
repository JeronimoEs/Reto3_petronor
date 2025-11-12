#!/bin/bash
# Script para ejecutar el dashboard localmente

echo "🌡️  Iniciando PETRONAITOR Dashboard..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py no encontrado. Asegúrate de estar en el directorio raíz del proyecto."
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no encontrado. Por favor instala Python 3.10 o superior."
    exit 1
fi

# Verificar Streamlit
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Streamlit no está instalado. Instalando dependencias..."
    pip install -r requirements.txt
fi

# Crear directorios necesarios
mkdir -p logs
mkdir -p resultados_analisis
mkdir -p mlruns

# Ejecutar Streamlit
echo "✅ Iniciando servidor Streamlit..."
echo "📊 Dashboard disponible en: http://localhost:8501"
echo ""
streamlit run app.py --server.port=8501 --server.address=localhost

