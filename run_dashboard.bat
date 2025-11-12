@echo off
REM Script para ejecutar el dashboard localmente en Windows

echo 🌡️  Iniciando PETRONAITOR Dashboard...
echo.

REM Verificar que estamos en el directorio correcto
if not exist "app.py" (
    echo ❌ Error: app.py no encontrado. Asegúrate de estar en el directorio raíz del proyecto.
    exit /b 1
)

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no encontrado. Por favor instala Python 3.10 o superior.
    exit /b 1
)

REM Verificar Streamlit
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Streamlit no está instalado. Instalando dependencias...
    pip install -r requirements.txt
)

REM Crear directorios necesarios
if not exist "logs" mkdir logs
if not exist "resultados_analisis" mkdir resultados_analisis
if not exist "mlruns" mkdir mlruns

REM Ejecutar Streamlit
echo ✅ Iniciando servidor Streamlit...
echo 📊 Dashboard disponible en: http://localhost:8501
echo.
streamlit run app.py --server.port=8501 --server.address=localhost

pause

