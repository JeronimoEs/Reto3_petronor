# Arquitectura del Sistema - Thermal Reliability Agent

## 📐 Visión General

El **Thermal Reliability Agent** es un sistema completo de análisis y predicción de fiabilidad térmica para tanques de almacenamiento de crudo. El sistema valida la hipótesis de que las imágenes térmicas capturadas durante períodos de menor variabilidad operacional proporcionan mediciones más fiables.

## 🏗️ Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer (Streamlit)                │
│  - Interfaz Web Segura                                      │
│  - Autenticación OAuth2                                     │
│  - Visualizaciones Interactivas                             │
│  - Control de Acceso (RBAC)                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Application Layer                              │
│  - app.py (Streamlit App)                                  │
│  - Routing y Navegación                                     │
│  - Gestión de Sesiones                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Business Logic Layer                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Reliability      │  │ Realtime         │                │
│  │ Analysis         │  │ Predictor        │                │
│  │ (4_*.py)         │  │ (5_*.py)         │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Thermal          │  │ Data Analysis    │                │
│  │ Processing       │  │ (3_*.py)         │                │
│  │ (2_*.py)         │  └──────────────────┘                │
│  └──────────────────┘                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Data Layer                                     │
│  - CSV Files (resultados_completos.csv)                     │
│  - Thermal Images (640x480 px)                              │
│  - Configuration (config.yaml)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              MLOps & Observability Layer                     │
│  - MLFlow Tracking                                          │
│  - Structured Logging                                       │
│  - Data Versioning                                          │
│  - Audit Logs                                               │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Módulos del Sistema

### 1. Backend de Análisis (`steps/4_reliability_analysis.py`)

**Responsabilidades:**
- Cálculo de sigma (variabilidad móvil) en caudal y nivel
- Clasificación de períodos en batch estable vs turbulento
- Análisis de correlaciones (Pearson/Spearman)
- Validación de hipótesis con ANOVA
- Generación de reportes comparativos

**Clases Principales:**
- `ReliabilityAnalyzer`: Analizador principal de fiabilidad

**Funciones Core:**
- `compute_sigma()`: Calcula desviaciones estándar móviles
- `classify_batches()`: Clasifica períodos por estabilidad
- `correlate_reliability()`: Calcula correlaciones
- `validate_hypothesis_anova()`: Valida hipótesis estadísticamente

### 2. Pipeline de Predicción (`steps/5_realtime_predictor.py`)

**Responsabilidades:**
- Procesamiento rápido de imágenes térmicas (< 5 segundos)
- Segmentación por rangos térmicos
- Cálculo de gradientes térmicos verticales
- Identificación de interfaces (agua/emulsión/crudo)
- Cálculo de score de fiabilidad (0-100)

**Clases Principales:**
- `RealtimeThermalPredictor`: Predictor en tiempo real

**Funciones Core:**
- `process_image_fast()`: Procesamiento rápido de imagen
- `calculate_reliability_score()`: Cálculo de score de fiabilidad
- `predict_new_image()`: Predicción completa

### 3. Interfaz Web (`app.py`)

**Responsabilidades:**
- Interfaz Streamlit con autenticación
- Carga de CSVs e imágenes
- Visualización de mapas térmicos coloreados
- Gráficos estadísticos interactivos
- Exportación de reportes

**Páginas:**
- Análisis Histórico
- Predicción en Tiempo Real
- Visualizaciones
- Exportar Reporte

### 4. MLOps & Tracking (`utils/mlops_tracking.py`)

**Responsabilidades:**
- Tracking con MLFlow
- Logging estructurado
- Versionado de datos e imágenes
- Trazabilidad completa

**Clases Principales:**
- `MLFlowTracker`: Tracker MLFlow
- `DataVersioning`: Sistema de versionado
- `StructuredLogger`: Logger estructurado

## 🔄 Flujos de Trabajo

### Flujo 1: Análisis Histórico

```
1. Cargar resultados_completos.csv
   ↓
2. Calcular sigma móvil (window=5)
   ↓
3. Clasificar registros (estable/turbulento)
   ↓
4. Procesar imágenes y detectar interfaces
   ↓
5. Correlacionar gradientes con sigma
   ↓
6. Validar hipótesis con ANOVA
   ↓
7. Generar reporte comparativo
```

### Flujo 2: Predicción en Tiempo Real

```
1. Recibir imagen térmica nueva
   ↓
2. Extraer timestamp (si aplica)
   ↓
3. Procesar imagen (< 5s)
   ↓
4. Segmentar por temperatura
   ↓
5. Detectar interfaces
   ↓
6. Calcular ratios y gradientes
   ↓
7. Comparar con perfiles históricos
   ↓
8. Calcular score de fiabilidad (0-100)
   ↓
9. Retornar resultados
```

## 🔐 Seguridad

### Autenticación
- OAuth2 / Azure AD (configurable)
- Tokens JWT temporales
- Sesiones seguras

### Control de Acceso (RBAC)
- **Operator**: view, upload, predict
- **Data Scientist**: view, upload, predict, analyze, export
- **Admin**: todos los permisos

### Cifrado
- HTTPS forzado (TLS)
- Datos en reposo: AES-256
- Claves gestionadas en Key Vault

### Auditoría
- Logging de todos los eventos
- Hash de imágenes procesadas
- Trazabilidad completa (input → output → timestamp)

## 📊 Métricas y Observabilidad

### Métricas de Performance
- Tiempo de procesamiento por imagen
- Tasa de éxito de predicciones
- Latencia de la aplicación
- Uptime del servicio

### Tracking MLOps
- Parámetros de modelos
- Métricas de evaluación
- Artefactos (modelos, datos)
- Versionado de código y datos

## 🚀 Despliegue

### Local Development
```bash
python -m venv .v
source .v/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
streamlit run app.py
```

### Docker
```bash
docker build -t thermal-reliability-agent .
docker run -p 8501:8501 thermal-reliability-agent
```

### Cloud (Azure Web App)
```bash
az webapp create --name thermal-reliability --resource-group rg-thermal --plan app-plan
az webapp config container set --name thermal-reliability --docker-custom-image-name thermal-reliability-agent
```

## 📈 Escalabilidad

- **Horizontal**: Múltiples instancias con load balancer
- **Vertical**: Aumento de recursos según demanda
- **Caching**: Cache de resultados de análisis
- **Async**: Procesamiento asíncrono para batches grandes

## 🔄 Integración CI/CD

1. **GitHub Actions / Azure DevOps**
   - Tests unitarios
   - Linters (flake8, black)
   - Build de Docker image
   - Push a Container Registry

2. **Deployment Pipeline**
   - Validación de configuración
   - Despliegue a staging
   - Tests de integración
   - Despliegue a producción

## 📝 Compliance

- **ISO 27001**: Seguridad de la información
- **GDPR / LOPDGDD**: Protección de datos
- **Auditoría**: Logs completos y trazables
- **Backup**: Versionado de datos e imágenes

