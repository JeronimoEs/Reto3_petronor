import pandas as pd
import sys
import re
import os

"""
EXTRACTOR DE IMÁGENES TÉRMICAS - TK 103_1.xlsx

DESCUBRIMIENTOS:
- El archivo TK 103_1.xlsx contiene 37 imágenes JPEG en xl/media/
- Las imágenes están embebidas en la primera columna
- Hay 38 filas de datos (sin contar header)
- Mapeo: Secuencial (primera imagen → primera fila de datos)

PROCESO:
1. Extraer todas las imágenes de xl/media/
2. Leer datos del Excel
3. Vincular secuencialmente imagen[i] ↔ fila[i]
4. Renombrar con timestamp de la fila
"""

# ============================================================================
# CONFIGURACIÓN
# ============================================================================


NOMBRE_CSV = 'csv/TK 103_1.xlsx-Hoja1.csv'

# ============================================================================
# PASO 1: LEER DATOS DEL EXCEL
# ============================================================================

def cargar_datos(ruta_csv):
    """
    Carga los datos del CSV usando pandas, omitiendo la fila 1 (índice 0) del CSV.
    """
    try:
        df = pd.read_csv(ruta_csv, decimal=',', skiprows=[1])
        return df
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo: {ruta_csv}")
        return None
    except Exception as e:
        print(f"Error al leer el CSV: {e}")
        return None

# ============================================================================
# PASO 2: LIMPIAR DATOS
# ============================================================================

def limpiar_datos(df):
    """
    Limpia el DataFrame para que los datos sean utilizables.
    """
    print("\nIniciando limpieza de datos...")
    
    # 1. Limpiar nombres de columnas (VERSIÓN MEJORADA)
    # Reemplaza CUALQUIER secuencia de espacios/saltos de línea (\s+) con UN solo espacio
    print("Nombres de columnas ANTES:", df.columns.tolist())
    df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
    print("Nombres de columnas DESPUÉS:", df.columns.tolist())

    # 2. Corregir rutas de imagen (quitar ..\) - solo si la columna existe
    if 'Imagen' in df.columns:
        df['Imagen'] = df['Imagen'].str.replace(r'..\\', '', regex=False)
    
    # 3. Convertir columnas de texto ('object') a números (float)
    def limpiar_a_numero(texto):
        if isinstance(texto, str):
            texto = texto.replace(',', '.')  # Reemplaza coma decimal
            match = re.search(r'(-?\d+\.?\d*)', texto) # Busca el primer número
            if match:
                return float(match.group(1))
        return None 

    columnas_a_limpiar = [
        'Caudal', 'Nivel TK %', 'T_TK', 'T_amb', 'Humedad Relativa', 
        'Radiación Solar', 'Precipitación', 'Velocidad Viento', 'Dirección Viento'
    ]
    
    print("\nIniciando conversión de columnas a número:")
    for col in columnas_a_limpiar:
        if col in df.columns:
            print(f"  - Convirtiendo '{col}'...")
            df[col] = df[col].apply(limpiar_a_numero)
        else:
            # ¡Este mensaje nos dirá si no encuentra el nombre de la columna!
            print(f"  - ADVERTENCIA: No se encontró la columna '{col}' para limpiar.")

    print("¡Datos limpios!")
    return df

# ============================================================================
# PASO 3: VINCULAR IMÁGENES A LA DATA SECUENCIALMENTE
# ============================================================================

def vincular_imagenes_a_data(df):
    """
    Vincula las imágenes a la data secuencialmente.
    Lee las imágenes desde ./imagenes y las vincula secuencialmente con las filas del DataFrame.
    """
    print("\n🔗 PASO 3: Vinculando imágenes con filas...")
    
    df['imagen_path'] = None
    df['imagen_numero'] = None

    # Obtener todas las imágenes del directorio ./imagenes
    imagenes_dir = './imagenes'
    image_files_mapping = {}  # {numero: ruta_completa}
    
    if not os.path.exists(imagenes_dir):
        print(f"   ⚠ ADVERTENCIA: No se encontró el directorio {imagenes_dir}")
        return df
    
    # Leer todos los archivos de imagen
    for filename in os.listdir(imagenes_dir):
        # Filtrar solo archivos de imagen
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            # Extraer número de imagen (ej: "Imagen1.png" -> 1, "Imagen10.jpg" -> 10)
            match = re.search(r'Imagen(\d+)', filename, re.IGNORECASE)
            if match:
                img_num = int(match.group(1))
                img_path = os.path.join(imagenes_dir, filename)
                image_files_mapping[img_num] = img_path
    
    print(f"   ✓ Encontradas {len(image_files_mapping)} imágenes en {imagenes_dir}")
    
    # Ordenar imágenes por número
    sorted_images = sorted(image_files_mapping.items())

    vinculadas = 0
    for i, (img_num, img_path) in enumerate(sorted_images):
        if i < len(df):
            df.at[i, 'imagen_path'] = img_path
            df.at[i, 'imagen_numero'] = img_num
            vinculadas += 1

    print(f"   ✓ {vinculadas} imágenes vinculadas con datos")

    return df