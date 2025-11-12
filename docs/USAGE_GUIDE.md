# Guía de Uso - Thermal Reliability Agent

## 🚀 Inicio Rápido

### Instalación Local

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd Reto3_petronor

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar aplicación
streamlit run app.py
```

Acceder a: `http://localhost:8501`

---

## 📖 Uso del Sistema

### 1. Análisis Histórico

**Objetivo:** Validar la hipótesis de fiabilidad térmica con datos históricos.

**Pasos:**

1. Acceder a la página "Análisis Histórico"
2. Cargar archivo `resultados_completos.csv`
3. El sistema automáticamente:
   - Calcula sigma (variabilidad móvil)
   - Clasifica períodos (estable/turbulento)
   - Analiza correlaciones
   - Valida hipótesis con ANOVA
4. Revisar resultados:
   - Validación de hipótesis (SÍ/NO)
   - Reporte comparativo
   - Resultados ANOVA
   - Gráficos estadísticos

**Interpretación de Resultados:**

- **Hipótesis Validada = SÍ**: Hay diferencias significativas (p < 0.05) entre batches estables y turbulentos
- **p-value < 0.05**: Diferencia estadísticamente significativa
- **Correlación negativa**: Mayor sigma → menor fiabilidad (valida hipótesis)

---

### 2. Predicción en Tiempo Real

**Objetivo:** Procesar nuevas imágenes térmicas y obtener score de fiabilidad.

**Pasos:**

1. Acceder a la página "Predicción en Tiempo Real"
2. (Opcional) Cargar datos de referencia históricos
3. Subir imagen térmica (formato: `tanque_YYYYMMDD_HHMMSS.jpg`)
4. El sistema procesa la imagen (< 5 segundos) y muestra:
   - **Score de fiabilidad** (0-100)
   - **Categoría**: Alta (≥80), Media (60-79), Baja (<60)
   - **Mapa térmico coloreado**:
     - 🔵 Azul: Agua
     - 🟡 Amarillo: Emulsión
     - 🔴 Rojo: Crudo
   - **Ratios de capas** (%)
   - **Gradientes térmicos**

**Interpretación del Score:**

- **80-100 (Alta)**: Imagen muy confiable, patrones similares a batch estable
- **60-79 (Media)**: Imagen moderadamente confiable
- **0-59 (Baja)**: Imagen poco confiable, posiblemente período turbulento

---

### 3. Visualizaciones

**Objetivo:** Explorar datos históricos con gráficos interactivos.

**Gráficos Disponibles:**

1. **Scatter: Sigma vs Precisión**
   - Eje X: Sigma (variabilidad)
   - Eje Y: Gradiente térmico máximo
   - Colores: Verde (estable), Rojo (turbulento)

2. **Boxplot: Fiabilidad por Batch**
   - Comparación de confianza de interfaz entre batches

3. **Histogramas: Gradientes Térmicos**
   - Distribución de gradientes por tipo de batch

---

### 4. Exportar Reporte

**Objetivo:** Generar reporte PDF con resultados completos.

**Contenido del Reporte:**

- Resumen ejecutivo
- Validación de hipótesis
- Resultados ANOVA
- Correlaciones significativas
- Gráficos estadísticos
- Conclusiones y recomendaciones

---

## 🔧 Uso Programático (Python)

### Análisis de Fiabilidad

```python
from steps.4_reliability_analysis import ReliabilityAnalyzer, load_data

# Cargar datos
df = load_data('resultados_completos.csv')

# Crear analizador
analyzer = ReliabilityAnalyzer(window=5)

# Ejecutar análisis completo
results = analyzer.analyze_reliability(df)

# Acceder a resultados
print(f"Hipótesis validada: {results['hypothesis_validated']}")
print(results['comparative_report'])
print(results['anova_results'])
```

### Predicción en Tiempo Real

```python
from steps.5_realtime_predictor import RealtimeThermalPredictor
import pandas as pd

# Cargar datos de referencia (opcional)
reference_data = pd.read_csv('resultados_completos.csv')

# Crear predictor
predictor = RealtimeThermalPredictor(reference_data=reference_data)

# Predecir nueva imagen
result = predictor.predict_new_image('tanque_20250101_120000.jpg')

# Acceder a resultados
print(f"Score de fiabilidad: {result['reliability_score']:.1f}%")
print(f"Categoría: {result['reliability_category']}")
print(f"Ratios - Crudo: {result['thermal_crudo_ratio']:.2%}, "
      f"Emulsión: {result['thermal_emulsion_ratio']:.2%}, "
      f"Agua: {result['thermal_agua_ratio']:.2%}")
```

### Tracking MLOps

```python
from utils.mlops_tracking import MLFlowTracker

# Crear tracker
tracker = MLFlowTracker(experiment_name="thermal_reliability")

# Iniciar run
tracker.start_run(run_name="analysis_20250101")

# Registrar parámetros
tracker.log_params({
    'window': 5,
    'sigma_threshold': 0.5,
    'correlation_method': 'pearson'
})

# Registrar métricas
tracker.log_metrics({
    'reliability_score': 85.5,
    'p_value': 0.03,
    'hypothesis_validated': True
})

# Finalizar run
tracker.end_run()
```

---

## 🐳 Uso con Docker

### Construir Imagen

```bash
docker build -t thermal-reliability-agent .
```

### Ejecutar Contenedor

```bash
docker run -p 8501:8501 thermal-reliability-agent
```

### Ejecutar con Volúmenes (para datos persistentes)

```bash
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/mlruns:/app/mlruns \
  thermal-reliability-agent
```

---

## ☁️ Despliegue en la Nube

### Azure Web App

```bash
# 1. Login a Azure
az login

# 2. Crear resource group
az group create --name rg-thermal --location eastus

# 3. Crear App Service Plan
az appservice plan create --name app-plan --resource-group rg-thermal --sku B1 --is-linux

# 4. Crear Web App
az webapp create --name thermal-reliability --resource-group rg-thermal --plan app-plan

# 5. Configurar container
az webapp config container set \
  --name thermal-reliability \
  --resource-group rg-thermal \
  --docker-custom-image-name thermal-reliability-agent \
  --docker-registry-server-url <registry-url>
```

### Variables de Entorno

Configurar en Azure Portal o CLI:

```bash
az webapp config appsettings set \
  --name thermal-reliability \
  --resource-group rg-thermal \
  --settings \
    MLFLOW_TRACKING_URI=<uri> \
    SECRET_KEY=<secret> \
    LOG_LEVEL=INFO
```

---

## 🔐 Seguridad

### Autenticación

El sistema incluye autenticación básica. Para producción:

1. **Azure AD / OAuth2:**
   - Configurar `OAUTH2_CLIENT_ID`, `OAUTH2_CLIENT_SECRET`
   - Implementar callback de autenticación

2. **Tokens JWT:**
   - Generar tokens temporales para cada sesión
   - Validar tokens en cada request

### Control de Acceso

Roles disponibles:
- **Operator**: Acceso básico (view, upload, predict)
- **Data Scientist**: Acceso completo (analyze, export)
- **Admin**: Acceso total

### Cifrado

- **HTTPS**: Forzado en producción
- **Datos en reposo**: AES-256
- **Claves**: Gestionadas en Azure Key Vault / AWS KMS

---

## 📊 Interpretación de Resultados

### Score de Fiabilidad

- **80-100 (Alta)**: Imagen muy confiable
  - Patrones similares a batch estable
  - Gradientes térmicos coherentes
  - Interfaces bien definidas

- **60-79 (Media)**: Imagen moderadamente confiable
  - Algunas desviaciones de patrones históricos
  - Gradientes aceptables

- **0-59 (Baja)**: Imagen poco confiable
  - Posible período turbulento
  - Gradientes inconsistentes
  - Revisar condiciones operacionales

### Validación de Hipótesis

- **Hipótesis Validada = SÍ**:
  - p < 0.05 en ANOVA
  - Diferencias significativas entre batches
  - Correlaciones negativas significativas

- **Hipótesis Validada = NO**:
  - p ≥ 0.05
  - No hay diferencias significativas
  - Revisar datos o hipótesis

---

## 🐛 Solución de Problemas

### Error: "No se pudo cargar la imagen"

- Verificar formato de imagen (JPG, PNG)
- Verificar tamaño (640x480 px recomendado)
- Verificar permisos de archivo

### Error: "Insuficientes datos para análisis"

- Verificar que CSV tenga al menos 10 registros
- Verificar que columnas requeridas estén presentes
- Verificar que datos no estén vacíos

### Error: "MLFlow no disponible"

- Instalar MLFlow: `pip install mlflow`
- O usar logging básico (sin tracking)

### Performance: "Tiempo de procesamiento > 5s"

- Reducir tamaño de imagen
- Optimizar parámetros de procesamiento
- Usar procesamiento en GPU (si disponible)

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar documentación en `docs/`
2. Verificar logs en `logs/app.log`
3. Contactar al equipo de desarrollo

---

## 📝 Notas Adicionales

- Las imágenes deben seguir el formato: `tanque_YYYYMMDD_HHMMSS.jpg`
- El sistema procesa imágenes en escala de grises
- Los resultados se guardan automáticamente en `resultados_analisis/`
- El tracking MLFlow se guarda en `mlruns/`

