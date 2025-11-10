# Reto3 Petronor - Análisis de Imágenes Térmicas de Tanques Estratificados

Sistema de procesamiento y análisis de imágenes térmicas infrarrojas para la detección automática de interfaces entre capas en tanques de almacenamiento de petróleo (crudo, emulsión, agua).

## 📋 Descripción

Este proyecto procesa imágenes térmicas de tanques estratificados para:

- **Detectar interfaces** entre capas (crudo, emulsión, agua)
- **Calcular espesores** de cada capa (en píxeles y ratios)
- **Extraer métricas térmicas** (temperaturas medias, gradientes)
- **Vincular imágenes** con datos tabulares de sensores
- **Validar coherencia** de las detecciones mediante rangos de temperatura calibrados

## 🏗️ Estructura del Proyecto

```
Reto3_petronor/
├── csv/                          # Archivos CSV con datos de sensores
│   ├── TK 103_1.xlsx-Hoja1.csv
│   └── YTK103_datos.xlsx-Sheet1.csv
├── imagenes/                     # Imágenes térmicas infrarrojas
│   ├── Imagen1.jpg
│   ├── Imagen2.jpg
│   └── ...
├── steps/                        # Módulos de procesamiento
│   ├── 1_read.py                 # Lectura y limpieza de datos CSV
│   └── 2_image_proccessing.py    # Procesamiento de imágenes térmicas
├── main.py                       # Script principal
├── requirements.txt              # Dependencias del proyecto
└── README.md                     # Este archivo
```

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el repositorio**

2. **Crear un entorno virtual (recomendado)**

```bash
python -m venv venv

# En Windows
venv\Scripts\activate

# En macOS/Linux
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

## 📦 Dependencias

- **pandas**: Manipulación y análisis de datos tabulares
- **numpy**: Operaciones numéricas y arrays
- **opencv-python**: Procesamiento de imágenes
- **scipy**: Operaciones científicas (filtros, detección de picos)
- **matplotlib**: Visualización (opcional, para gráficos)

## 🔧 Uso

### Procesamiento Básico de Datos

```python
from steps.1_read import cargar_datos, limpiar_datos, vincular_imagenes_a_data

# Cargar datos CSV
df = cargar_datos('csv/TK 103_1.xlsx-Hoja1.csv')

# Limpiar datos
df_limpio = limpiar_datos(df)

# Vincular imágenes
df_con_imagenes = vincular_imagenes_a_data(df_limpio)
```

### Procesamiento de Imágenes Térmicas

```python
from steps.2_image_proccessing import ThermalAnalyzer

# Crear analizador
analyzer = ThermalAnalyzer(
    img_height=512,
    img_width=640,
    smoothing_sigma=3,
    normalize=True
)

# Procesar una imagen
features = analyzer.process_image('./imagenes/Imagen1.jpg')

# Ver resultados
print(f"Ratio de crudo: {features['thermal_crudo_ratio']:.2%}")
print(f"Ratio de emulsión: {features['thermal_emulsion_ratio']:.2%}")
print(f"Ratio de agua: {features['thermal_agua_ratio']:.2%}")
print(f"Confianza: {features['thermal_interface_confidence']:.2f}")
```

### Visualización de Interfaces (Opcional)

```python
# Mostrar imagen con interfaces detectadas
analyzer.show_interfaces('./imagenes/Imagen1.jpg')

# Guardar visualización
analyzer.show_interfaces('./imagenes/Imagen1.jpg', save_path='output.png')
```

### Pipeline Completo

```python
import pandas as pd
from steps.1_read import cargar_datos, limpiar_datos, vincular_imagenes_a_data
from steps.2_image_proccessing import ThermalAnalyzer

# 1. Cargar y limpiar datos
df = cargar_datos('csv/TK 103_1.xlsx-Hoja1.csv')
df = limpiar_datos(df)
df = vincular_imagenes_a_data(df)

# 2. Procesar imágenes térmicas
analyzer = ThermalAnalyzer()
thermal_features = []

for idx, row in df.iterrows():
    if pd.notna(row['imagen_path']):
        features = analyzer.process_image(row['imagen_path'])
        thermal_features.append(features)
    else:
        thermal_features.append(analyzer._default_output('no_image'))

# 3. Combinar features con datos originales
thermal_df = pd.DataFrame(thermal_features)
df_final = pd.concat([df, thermal_df], axis=1)

# 4. Guardar resultados
df_final.to_csv('resultados_completos.csv', index=False)
```

## 📊 Features Extraídas

El módulo `ThermalAnalyzer` extrae las siguientes métricas:

### Interfaces
- `thermal_interface_top_px`: Posición de la interfaz superior (píxeles)
- `thermal_interface_bottom_px`: Posición de la interfaz inferior (píxeles)
- `thermal_interface_confidence`: Confianza en la detección (0-1)

### Espesores
- `thermal_crudo_px`: Espesor de crudo en píxeles
- `thermal_emulsion_px`: Espesor de emulsión en píxeles
- `thermal_agua_px`: Espesor de agua en píxeles
- `thermal_crudo_ratio`: Ratio de crudo (0-1)
- `thermal_emulsion_ratio`: Ratio de emulsión (0-1)
- `thermal_agua_ratio`: Ratio de agua (0-1)

### Temperaturas
- `thermal_temp_crudo_mean`: Temperatura media del crudo
- `thermal_temp_emulsion_mean`: Temperatura media de la emulsión
- `thermal_temp_agua_mean`: Temperatura media del agua

### Gradientes
- `thermal_gradient_max`: Gradiente máximo del perfil térmico
- `thermal_gradient_std`: Desviación estándar del gradiente

### Estado
- `status`: Estado del procesamiento (`'success'`, `'not_found'`, `'no_interfaces_detected'`, `'processing_error'`)

## 🔬 Metodología

### Detección de Interfaces

1. **Preprocesamiento**: La imagen se convierte a escala de grises, se aplica suavizado gaussiano y normalización.

2. **Perfil Térmico**: Se calcula el perfil térmico vertical promediando horizontalmente cada fila de la imagen.

3. **Detección de Gradientes**: Se detectan picos negativos en el gradiente del perfil (donde la temperatura cae bruscamente).

4. **Validación**: Se evalúan combinaciones de interfaces candidatas según:
   - **Rangos de temperatura calibrados**:
     - Aire: 0-70
     - Agua: 70-130
     - Emulsión: 130-180
     - Crudo: 180-255
   - **Orden térmico**: Crudo > Emulsión > Agua
   - **Gradientes razonables** entre capas

5. **Selección**: Se elige la combinación de interfaces con mayor score de coherencia.

## ⚙️ Configuración

### Parámetros de ThermalAnalyzer

```python
analyzer = ThermalAnalyzer(
    img_height=512,        # Altura de imagen procesada
    img_width=640,         # Ancho de imagen procesada
    smoothing_sigma=3,     # Suavizado gaussiano (mayor = más suave)
    normalize=True         # Normalizar imagen al rango [0, 255]
)
```

### Ajuste de Rangos de Temperatura

Los rangos de temperatura están calibrados en la escala de píxeles (0-255). Pueden ajustarse en el método `__init__` de `ThermalAnalyzer`:

```python
self.TEMP_RANGES = {
    'aire':      (0, 70),
    'agua':      (70, 130),
    'emulsion':  (130, 180),
    'crudo':     (180, 255)
}
```

## 🐛 Solución de Problemas

### Error: "No se pudo cargar la imagen"
- Verifica que la ruta de la imagen sea correcta
- Asegúrate de que el archivo existe y es accesible
- Verifica que la imagen esté en un formato soportado (JPG, PNG, etc.)

### Error: "no_interfaces_detected"
- La imagen puede no tener interfaces claras
- Ajusta `smoothing_sigma` para más/menos suavizado
- Verifica que la imagen sea una imagen térmica válida

### Error de importación
- Asegúrate de haber instalado todas las dependencias: `pip install -r requirements.txt`
- Verifica que estás usando Python 3.8+

## 📝 Notas

- Las imágenes deben estar nombradas con el patrón `Imagen{N}.jpg` (ej: `Imagen1.jpg`, `Imagen10.jpg`)
- El procesamiento es secuencial: primera imagen → primera fila de datos
- Los resultados incluyen un campo `status` que indica el éxito o tipo de error del procesamiento

## 📄 Licencia

Este proyecto es parte del Reto3 Petronor.

## 👥 Contribuciones

Para contribuir al proyecto, por favor:
1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📧 Contacto

Para preguntas o soporte, contacta al equipo del proyecto.

