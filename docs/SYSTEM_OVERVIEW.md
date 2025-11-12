# Resumen del Sistema - Thermal Reliability Agent

## 📋 Visión General

El **Thermal Reliability Agent** es un sistema completo que valida la hipótesis de fiabilidad térmica y permite análisis operativo en la nube. El sistema procesa imágenes térmicas de tanques de almacenamiento y correlaciona la fiabilidad con la variabilidad operacional.

---

## 📁 Estructura de Archivos

### `/steps/` - Módulos de Procesamiento

#### `1_read.py` - Lectura y Limpieza de Datos
**Propósito:** Carga y limpia datos CSV de sensores.

**Funciones principales:**
- `cargar_datos(ruta_csv)`: Carga CSV con validación
- `limpiar_datos(df)`: Limpia nombres de columnas, convierte tipos
- `vincular_imagenes_a_data(df)`: Vincula imágenes con datos secuencialmente

**Uso:**
```python
from steps.1_read import cargar_datos, limpiar_datos, vincular_imagenes_a_data
df = cargar_datos('csv/TK 103_1.xlsx-Hoja1.csv')
df = limpiar_datos(df)
df = vincular_imagenes_a_data(df)
```

---

#### `2_image_proccessing.py` - Procesamiento de Imágenes Térmicas
**Propósito:** Procesa imágenes térmicas y detecta interfaces entre capas.

**Clase principal:**
- `ThermalAnalyzer`: Analizador de imágenes térmicas

**Métodos clave:**
- `process_image(img_path)`: Procesa imagen y extrae features
- `show_interfaces(img_path)`: Visualiza interfaces detectadas

**Features extraídas:**
- Posiciones de interfaces (top/bottom)
- Espesores de capas (px y ratios)
- Temperaturas medias por capa
- Gradientes térmicos (max, std)
- Confianza de detección

**Uso:**
```python
from steps.2_image_proccessing import ThermalAnalyzer
analyzer = ThermalAnalyzer()
features = analyzer.process_image('./imagenes/Imagen1.jpg')
```

---

#### `3_analisis.py` - Análisis de Resultados
**Propósito:** Analiza resultados de imágenes térmicas y correlaciona con condiciones operativas.

**Funciones principales:**
- `cargar_config(config_path)`: Carga configuración YAML
- `cargar_datos_procesados(csv_path)`: Carga datos con features térmicas
- `calcular_metricas_derivadas(df, config)`: Calcula métricas derivadas
- `analizar_correlaciones(df, config)`: Analiza correlaciones
- `detectar_tendencias(df, config)`: Detecta tendencias
- `calcular_metricas_agregadas(df, config)`: Métricas por día/estado
- `generar_visualizaciones(...)`: Genera gráficos
- `generar_resumen_interpretativo(...)`: Resumen automático
- `exportar_resultados(...)`: Exporta todos los resultados

**Uso:**
```python
from steps.3_analisis import main
main()  # Ejecuta análisis completo
```

---

#### `4_reliability_analysis.py` - Análisis de Fiabilidad Térmica ⭐ NUEVO
**Propósito:** Valida hipótesis de fiabilidad térmica con análisis estadístico.

**Clase principal:**
- `ReliabilityAnalyzer`: Analizador de fiabilidad

**Métodos clave:**
- `compute_sigma(df)`: Calcula variabilidad móvil (sigma)
- `classify_batches(df)`: Clasifica en batch estable/turbulento
- `correlate_reliability(df)`: Calcula correlaciones
- `validate_hypothesis_anova(df)`: Valida hipótesis con ANOVA
- `analyze_reliability(df)`: Análisis completo

**Uso:**
```python
from steps.4_reliability_analysis import ReliabilityAnalyzer, load_data
df = load_data('resultados_completos.csv')
analyzer = ReliabilityAnalyzer(window=5)
results = analyzer.analyze_reliability(df)
```

---

#### `5_realtime_predictor.py` - Predicción en Tiempo Real ⭐ NUEVO
**Propósito:** Procesa nuevas imágenes y genera scores de fiabilidad (< 5s).

**Clase principal:**
- `RealtimeThermalPredictor`: Predictor en tiempo real

**Métodos clave:**
- `predict_new_image(image_path)`: Predicción completa
- `process_image_fast(image_path)`: Procesamiento rápido
- `calculate_reliability_score(features)`: Calcula score (0-100)
- `batch_predict(image_paths)`: Procesamiento en batch

**Uso:**
```python
from steps.5_realtime_predictor import RealtimeThermalPredictor
predictor = RealtimeThermalPredictor(reference_data=df)
result = predictor.predict_new_image('tanque_20250101_120000.jpg')
print(f"Score: {result['reliability_score']:.1f}%")
```

---

### `/utils/` - Utilidades

#### `mlops_tracking.py` - Tracking MLOps ⭐ NUEVO
**Propósito:** Sistema de logging y tracking para reproducibilidad.

**Clases principales:**
- `MLFlowTracker`: Tracker MLFlow
- `DataVersioning`: Versionado de datos
- `StructuredLogger`: Logger estructurado

**Funcionalidades:**
- Tracking de experimentos con MLFlow
- Versionado de datos e imágenes (hashes)
- Logging estructurado con trazabilidad
- Registro de parámetros, métricas y artefactos

**Uso:**
```python
from utils.mlops_tracking import MLFlowTracker
tracker = MLFlowTracker(experiment_name="thermal_reliability")
tracker.start_run()
tracker.log_params({'window': 5})
tracker.log_metrics({'reliability_score': 85.5})
tracker.end_run()
```

---

### `/app.py` - Interfaz Web ⭐ NUEVO
**Propósito:** Aplicación Streamlit con interfaz web segura.

**Páginas:**
1. **Análisis Histórico**: Validación de hipótesis con datos históricos
2. **Predicción en Tiempo Real**: Procesamiento de nuevas imágenes
3. **Visualizaciones**: Gráficos estadísticos interactivos
4. **Exportar Reporte**: Generación de reportes PDF

**Funcionalidades:**
- Autenticación con roles (Operator/Data Scientist/Admin)
- Carga de CSVs e imágenes
- Visualización de mapas térmicos coloreados
- Scores de fiabilidad en tiempo real
- Gráficos estadísticos
- Logging de auditoría

**Uso:**
```bash
streamlit run app.py
```

---

### `/config.yaml` - Configuración
**Propósito:** Configuración centralizada del sistema.

**Secciones:**
- `umbrales_proporciones`: Rangos esperados de crudo/emulsión/agua
- `fiabilidad_termica`: Umbrales de fiabilidad
- `estado_operacional`: Criterios para LLENADO/DECANTACION/VACIADO
- `meteorologia`: Umbrales meteorológicos
- `analisis`: Configuración de análisis
- `output`: Configuración de salida

---

### `/main.py` - Script Principal
**Propósito:** Pipeline completo de procesamiento.

**Flujo:**
1. Carga y limpia datos CSV
2. Vincula imágenes térmicas
3. Procesa imágenes térmicas
4. Combina datos y features
5. Guarda resultados

**Uso:**
```bash
python main.py
```

---

### `/Dockerfile` - Contenedor Docker ⭐ NUEVO
**Propósito:** Imagen Docker para despliegue en la nube.

**Características:**
- Base: Python 3.10-slim
- Dependencias instaladas
- Streamlit configurado
- Healthcheck incluido
- Puerto 8501 expuesto

**Uso:**
```bash
docker build -t thermal-reliability-agent .
docker run -p 8501:8501 thermal-reliability-agent
```

---

### `/requirements.txt` - Dependencias
**Propósito:** Lista de dependencias Python.

**Dependencias principales:**
- pandas, numpy, scipy: Análisis de datos
- opencv-python: Procesamiento de imágenes
- matplotlib, seaborn: Visualización
- streamlit: Interfaz web
- mlflow: Tracking MLOps
- pyyaml: Configuración

---

### `/docs/` - Documentación

#### `ARCHITECTURE.md` ⭐ NUEVO
Arquitectura completa del sistema, componentes, flujos de trabajo, seguridad.

#### `API_DOCUMENTATION.md` ⭐ NUEVO
Documentación de API de todos los módulos, clases y funciones.

#### `USAGE_GUIDE.md` ⭐ NUEVO
Guía de uso paso a paso, ejemplos, solución de problemas.

#### `SYSTEM_OVERVIEW.md` (este archivo)
Resumen file por file del sistema completo.

---

## 🔄 Flujos de Trabajo Principales

### Flujo 1: Análisis Histórico Completo

```
main.py
  ↓
1_read.py (cargar y limpiar datos)
  ↓
2_image_proccessing.py (procesar imágenes)
  ↓
3_analisis.py (análisis y correlaciones)
  ↓
4_reliability_analysis.py (validar hipótesis)
  ↓
Resultados en resultados_analisis/
```

### Flujo 2: Predicción en Tiempo Real

```
app.py (interfaz web)
  ↓
Usuario sube imagen
  ↓
5_realtime_predictor.py (procesar imagen)
  ↓
Calcular score de fiabilidad
  ↓
Mostrar resultados en interfaz
```

### Flujo 3: Tracking MLOps

```
Cualquier módulo
  ↓
utils/mlops_tracking.py
  ↓
MLFlowTracker (registrar parámetros/métricas)
  ↓
DataVersioning (versionar datos)
  ↓
StructuredLogger (logging estructurado)
  ↓
MLFlow UI / Logs
```

---

## 🔐 Seguridad y Compliance

### Autenticación
- OAuth2 / Azure AD (configurable)
- Tokens JWT temporales
- Sesiones seguras

### Control de Acceso (RBAC)
- **Operator**: view, upload, predict
- **Data Scientist**: + analyze, export
- **Admin**: todos los permisos

### Cifrado
- HTTPS forzado (TLS)
- Datos en reposo: AES-256
- Claves en Key Vault

### Auditoría
- Logging de todos los eventos
- Hash de imágenes procesadas
- Trazabilidad completa

---

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

---

## 🚀 Despliegue

### Local
```bash
streamlit run app.py
```

### Docker
```bash
docker build -t thermal-reliability-agent .
docker run -p 8501:8501 thermal-reliability-agent
```

### Cloud (Azure Web App)
```bash
az webapp create --name thermal-reliability --resource-group rg-thermal
az webapp config container set --name thermal-reliability --docker-custom-image-name thermal-reliability-agent
```

---

## ✅ Criterios de Éxito

- ✅ ≥85% de coherencia térmica
- ✅ p < 0.05 en validación ANOVA
- ✅ Procesamiento < 5s por imagen
- ✅ Cumplimiento de seguridad (ISO 27001, GDPR)
- ✅ Logging con trazabilidad completa

---

## 📝 Notas Finales

- Todos los módulos están documentados con docstrings
- El sistema es modular y extensible
- La configuración está centralizada en `config.yaml`
- El tracking MLOps permite reproducibilidad
- La interfaz web es segura y escalable

---

**Sistema desarrollado para Reto3 Petronor - Thermal Reliability Agent**

