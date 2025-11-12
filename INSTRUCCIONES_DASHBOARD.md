# 🚀 Instrucciones para Ejecutar PETRONAITOR Dashboard Localmente

## 📋 Requisitos Previos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Terminal/Consola

---

## 🔧 Instalación

### Paso 1: Verificar Python

```bash
python --version
# o
python3 --version
```

Debe mostrar Python 3.10 o superior.

### Paso 2: Instalar Dependencias

```bash
# Navegar al directorio del proyecto
cd Reto3_petronor

# Instalar todas las dependencias
pip install -r requirements.txt
```

**Nota:** Si tienes problemas, puedes instalar en un entorno virtual:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🎯 Ejecutar el Dashboard

### Opción 1: Usando el Script (Recomendado)

#### En macOS/Linux:
```bash
./run_dashboard.sh
```

#### En Windows:
```bash
run_dashboard.bat
```

### Opción 2: Comando Directo

```bash
streamlit run app.py
```

### Opción 3: Con Puerto Específico

```bash
streamlit run app.py --server.port=8501 --server.address=localhost
```

---

## 🌐 Acceder al Dashboard

Una vez ejecutado, el dashboard estará disponible en:

**http://localhost:8501**

Abre tu navegador y ve a esa dirección.

---

## 🔐 Autenticación

Al abrir el dashboard, verás una pantalla de login. Puedes usar:

- **Usuario que empiece con "admin"**: Acceso completo (admin)
- **Usuario que empiece con "scientist"**: Acceso de científico de datos
- **Cualquier otro usuario**: Acceso de operador

**Ejemplos:**
- `admin1` / cualquier contraseña → Rol: Admin
- `scientist1` / cualquier contraseña → Rol: Data Scientist  
- `operator1` / cualquier contraseña → Rol: Operator

---

## 📊 Uso del Dashboard

### 1. Análisis Histórico

1. Ve a la página "Análisis Histórico"
2. Carga el archivo `resultados_completos.csv`
3. El sistema analizará los datos automáticamente
4. Verás:
   - Validación de hipótesis (SÍ/NO)
   - Reporte comparativo
   - Resultados ANOVA
   - Gráficos estadísticos

### 2. Predicción en Tiempo Real

1. Ve a la página "Predicción en Tiempo Real"
2. (Opcional) Carga datos de referencia históricos
3. Sube una imagen térmica
4. Verás:
   - Score de fiabilidad (0-100)
   - Mapa térmico coloreado
   - Ratios de capas
   - Gradientes térmicos

### 3. Visualizaciones

1. Ve a la página "Visualizaciones"
2. Explora gráficos estadísticos interactivos

### 4. Exportar Reporte

1. Ve a la página "Exportar Reporte"
2. Genera reportes PDF (funcionalidad en desarrollo)

---

## ⚠️ Solución de Problemas

### Error: "ModuleNotFoundError"

```bash
# Reinstalar dependencias
pip install --upgrade -r requirements.txt
```

### Error: "Streamlit no encontrado"

```bash
pip install streamlit
```

### Error: "No se puede cargar módulo"

Verifica que estés en el directorio raíz del proyecto y que todos los archivos estén presentes:
- `app.py`
- `steps/4_reliability_analysis.py`
- `steps/5_realtime_predictor.py`
- `steps/2_image_proccessing.py`

### Puerto 8501 ya en uso

```bash
# Usar otro puerto
streamlit run app.py --server.port=8502
```

### Problemas con imports

Si hay errores de importación, verifica que:
1. Todos los módulos en `steps/` existan
2. Las dependencias estén instaladas
3. Estés usando Python 3.10+

---

## 🐳 Alternativa: Usar Docker

Si prefieres usar Docker:

```bash
# Construir imagen
docker build -t thermal-reliability-agent .

# Ejecutar contenedor
docker run -p 8501:8501 thermal-reliability-agent
```

---

## 📝 Notas

- El dashboard se recarga automáticamente cuando cambias el código
- Los datos se procesan en tiempo real
- Los resultados se guardan en `resultados_analisis/`
- Los logs se guardan en `logs/` (si está configurado)

---

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs en la consola
2. Verifica que todas las dependencias estén instaladas
3. Asegúrate de estar en el directorio correcto
4. Revisa la documentación en `docs/`

---

¡Disfruta usando PETRONAITOR! 🌡️

