# Dockerfile para Thermal Reliability Agent
# Imagen base: Python 3.10 slim

FROM python:3.10-slim

# Metadatos
LABEL maintainer="Thermal Reliability Agent System"
LABEL description="Sistema de análisis y predicción de fiabilidad térmica"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Streamlit y dependencias adicionales
RUN pip install --no-cache-dir \
    streamlit>=1.28.0 \
    reportlab>=4.0.0 \
    mlflow>=2.8.0

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/data /app/results /app/mlruns /app/logs

# Exponer puerto de Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando por defecto
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

