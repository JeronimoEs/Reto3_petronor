# Documentación de API - Thermal Reliability Agent

## 📚 Índice

1. [Módulo de Análisis de Fiabilidad](#módulo-de-análisis-de-fiabilidad)
2. [Módulo de Predicción en Tiempo Real](#módulo-de-predicción-en-tiempo-real)
3. [Módulo de Tracking MLOps](#módulo-de-tracking-mlops)
4. [Interfaz Web](#interfaz-web)

---

## Módulo de Análisis de Fiabilidad

### Clase: `ReliabilityAnalyzer`

#### `__init__(window=5, sigma_threshold=None, correlation_method='pearson')`

Inicializa el analizador de fiabilidad.

**Parámetros:**
- `window` (int): Ventana móvil para cálculo de sigma (default: 5)
- `sigma_threshold` (float, optional): Umbral para clasificar batches. Si None, se calcula automáticamente
- `correlation_method` (str): Método de correlación ('pearson' o 'spearman')

**Ejemplo:**
```python
from steps.4_reliability_analysis import ReliabilityAnalyzer

analyzer = ReliabilityAnalyzer(window=5, correlation_method='pearson')
```

---

#### `compute_sigma(df, columns=['Caudal', 'Nivel TK %'])`

Calcula desviaciones estándar móviles (sigma) para columnas especificadas.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con datos históricos
- `columns` (list): Lista de columnas para calcular sigma

**Retorna:**
- `pd.DataFrame`: DataFrame con columnas adicionales 'sigma_{col}'

**Ejemplo:**
```python
df_with_sigma = analyzer.compute_sigma(df, ['Caudal', 'Nivel TK %'])
print(df_with_sigma[['sigma_Caudal', 'sigma_Nivel TK %']].head())
```

---

#### `classify_batches(df, sigma_columns=['sigma_Caudal', 'sigma_Nivel TK %'])`

Clasifica períodos en batch estable (sigma bajo) o batch turbulento (sigma alto).

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con columnas sigma calculadas
- `sigma_columns` (list): Columnas de sigma para clasificar

**Retorna:**
- `pd.DataFrame`: DataFrame con columna 'batch_type' ('estable' o 'turbulento')

**Ejemplo:**
```python
df_classified = analyzer.classify_batches(df)
print(df_classified['batch_type'].value_counts())
```

---

#### `correlate_reliability(df)`

Calcula correlaciones entre precisión térmica (gradientes) y sigma.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con datos térmicos y sigma

**Retorna:**
- `dict`: Diccionario con correlaciones y significancia estadística

**Ejemplo:**
```python
correlations = analyzer.correlate_reliability(df)
print(correlations['thermal_gradient_max']['sigma_Caudal'])
```

---

#### `validate_hypothesis_anova(df)`

Valida la hipótesis usando ANOVA comparando batches estables vs turbulentos.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con datos clasificados

**Retorna:**
- `dict`: Resultados de ANOVA con F-statistic, p-value y conclusión

**Ejemplo:**
```python
anova_results = analyzer.validate_hypothesis_anova(df)
print(f"Hipótesis validada: {anova_results['hypothesis_validated']}")
```

---

#### `analyze_reliability(df)`

Ejecuta el análisis completo de fiabilidad térmica.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con datos históricos y features térmicas

**Retorna:**
- `dict`: Diccionario con todos los resultados del análisis

**Ejemplo:**
```python
results = analyzer.analyze_reliability(df)
print(results['hypothesis_validated'])
print(results['comparative_report'])
```

---

## Módulo de Predicción en Tiempo Real

### Clase: `RealtimeThermalPredictor`

#### `__init__(reference_data=None, processing_time_limit=5.0)`

Inicializa el predictor en tiempo real.

**Parámetros:**
- `reference_data` (pd.DataFrame, optional): Datos históricos de referencia
- `processing_time_limit` (float): Límite máximo de tiempo de procesamiento (segundos)

**Ejemplo:**
```python
from steps.5_realtime_predictor import RealtimeThermalPredictor

predictor = RealtimeThermalPredictor(reference_data=df)
```

---

#### `predict_new_image(image_path, extract_timestamp=True)`

Procesa nueva imagen y genera predicción completa con score de fiabilidad.

**Parámetros:**
- `image_path` (str): Ruta a la imagen térmica
- `extract_timestamp` (bool): Si True, intenta extraer timestamp del nombre

**Retorna:**
- `dict`: Diccionario completo con features, score y metadatos

**Ejemplo:**
```python
result = predictor.predict_new_image('tanque_20250101_120000.jpg')
print(f"Score: {result['reliability_score']}")
print(f"Categoría: {result['reliability_category']}")
```

**Estructura del resultado:**
```python
{
    'thermal_gradient_max': float,
    'thermal_interface_confidence': float,
    'thermal_emulsion_ratio': float,
    'thermal_agua_ratio': float,
    'thermal_crudo_ratio': float,
    'reliability_score': float,  # 0-100
    'reliability_category': str,  # 'alta', 'media', 'baja'
    'processing_time': float,
    'timestamp': str,
    'status': str
}
```

---

#### `batch_predict(image_paths)`

Procesa múltiples imágenes en batch.

**Parámetros:**
- `image_paths` (list): Lista de rutas a imágenes

**Retorna:**
- `pd.DataFrame`: DataFrame con resultados de todas las predicciones

**Ejemplo:**
```python
results_df = predictor.batch_predict(['img1.jpg', 'img2.jpg'])
print(results_df[['image_filename', 'reliability_score']])
```

---

## Módulo de Tracking MLOps

### Clase: `MLFlowTracker`

#### `__init__(experiment_name='thermal_reliability', tracking_uri=None)`

Inicializa el tracker MLFlow.

**Parámetros:**
- `experiment_name` (str): Nombre del experimento
- `tracking_uri` (str, optional): URI del servidor MLFlow

**Ejemplo:**
```python
from utils.mlops_tracking import MLFlowTracker

tracker = MLFlowTracker(experiment_name="thermal_reliability")
```

---

#### `start_run(run_name=None, tags=None)`

Inicia un nuevo run de MLFlow.

**Parámetros:**
- `run_name` (str, optional): Nombre del run
- `tags` (dict, optional): Tags adicionales

**Ejemplo:**
```python
tracker.start_run(run_name="analysis_20250101", tags={'version': '1.0'})
```

---

#### `log_params(params)`

Registra parámetros del modelo/experimento.

**Parámetros:**
- `params` (dict): Diccionario de parámetros

**Ejemplo:**
```python
tracker.log_params({'window': 5, 'sigma_threshold': 0.5})
```

---

#### `log_metrics(metrics, step=None)`

Registra métricas.

**Parámetros:**
- `metrics` (dict): Diccionario de métricas
- `step` (int, optional): Paso/iteración

**Ejemplo:**
```python
tracker.log_metrics({'reliability_score': 85.5, 'p_value': 0.03})
```

---

## Interfaz Web

### Endpoints de Streamlit

La aplicación Streamlit (`app.py`) proporciona una interfaz web con las siguientes páginas:

1. **Análisis Histórico**
   - Carga de CSV con datos históricos
   - Análisis de fiabilidad
   - Visualización de resultados ANOVA
   - Gráficos comparativos

2. **Predicción en Tiempo Real**
   - Subida de imágenes térmicas
   - Procesamiento en tiempo real
   - Visualización de mapas térmicos
   - Score de fiabilidad

3. **Visualizaciones**
   - Gráficos estadísticos interactivos
   - Scatter plots
   - Boxplots
   - Histogramas

4. **Exportar Reporte**
   - Generación de reportes PDF
   - Exportación de resultados

### Autenticación

La aplicación requiere autenticación con roles:
- **Operator**: Acceso básico
- **Data Scientist**: Acceso completo
- **Admin**: Acceso total

### Uso

```bash
# Ejecutar localmente
streamlit run app.py

# Ejecutar en Docker
docker run -p 8501:8501 thermal-reliability-agent
```

Acceder a: `http://localhost:8501`

