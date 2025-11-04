import pandas as pd
import sys
import re

NOMBRE_CSV = 'csv/TK 103_1.xlsx - Hoja1.csv'

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

    # 2. Corregir rutas de imagen (quitar ..\)
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

def main():
    print(f"Cargando datos desde: {NOMBRE_CSV}")
    data_frame = cargar_datos(NOMBRE_CSV)
    
    if data_frame is not None:
        print("¡CSV cargado exitosamente!")
        
        data_frame_limpio = limpiar_datos(data_frame)
        
        print("\n--- Primeras 5 filas (Datos Limpios) ---")
        print(data_frame_limpio)
        
        print("\n--- Información de las columnas (Datos Limpios) ---")
        data_frame_limpio.info()
    else:
        print("No se pudieron cargar los datos.")

if __name__ == "__main__":
    main()