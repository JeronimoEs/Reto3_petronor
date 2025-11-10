"""
Script principal para el procesamiento completo de datos e imágenes térmicas.

Este script ejecuta el pipeline completo:
1. Carga y limpia datos CSV
2. Vincula imágenes térmicas con los datos
3. Procesa imágenes térmicas para extraer features
4. Combina todos los datos en un DataFrame final
5. Guarda los resultados
"""

import pandas as pd
import os
import importlib.util
from pathlib import Path

# Obtener el directorio base del proyecto (donde está main.py)
BASE_DIR = Path(__file__).parent

# Importar módulos que empiezan con números usando importlib
spec_read = importlib.util.spec_from_file_location(
    "read_module", 
    BASE_DIR / "steps" / "1_read.py"
)
read_module = importlib.util.module_from_spec(spec_read)
spec_read.loader.exec_module(read_module)
cargar_datos = read_module.cargar_datos
limpiar_datos = read_module.limpiar_datos
vincular_imagenes_a_data = read_module.vincular_imagenes_a_data

spec_processing = importlib.util.spec_from_file_location(
    "processing_module", 
    BASE_DIR / "steps" / "2_image_proccessing.py"
)
processing_module = importlib.util.module_from_spec(spec_processing)
spec_processing.loader.exec_module(processing_module)
ThermalAnalyzer = processing_module.ThermalAnalyzer


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

NOMBRE_CSV = 'csv/TK 103_1.xlsx-Hoja1.csv'
OUTPUT_CSV = 'resultados_completos.csv'


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Ejecuta el pipeline completo de procesamiento.
    """
    print("="*80)
    print("🖼️  PROCESAMIENTO DE IMÁGENES TÉRMICAS - RETO3 PETRONOR")
    print("="*80)
    
    # ========================================================================
    # PASO 1: CARGAR Y LIMPIAR DATOS
    # ========================================================================
    
    print(f"\n📊 PASO 1: Cargando datos desde: {NOMBRE_CSV}")
    df = cargar_datos(NOMBRE_CSV)
    
    if df is None:
        print("❌ Error: No se pudieron cargar los datos.")
        return
    
    print(f"   ✓ {len(df)} filas cargadas")
    
    print("\n🧹 PASO 2: Limpiando datos...")
    df = limpiar_datos(df)
    
    print(f"\n   ✓ Datos limpios: {len(df)} filas, {len(df.columns)} columnas")
    print(f"   ✓ Columnas: {list(df.columns)[:5]}...")  # Mostrar primeras 5
    
    # ========================================================================
    # PASO 2: VINCULAR IMÁGENES
    # ========================================================================
    
    df = vincular_imagenes_a_data(df)
    
    # Contar cuántas imágenes se vincularon
    imagenes_vinculadas = df['imagen_path'].notna().sum()
    print(f"\n   ✓ Total de imágenes vinculadas: {imagenes_vinculadas}/{len(df)}")
    
    # ========================================================================
    # PASO 3: PROCESAR IMÁGENES TÉRMICAS
    # ========================================================================
    
    print("\n🌡️  PASO 3: Procesando imágenes térmicas...")
    
    # Crear analizador térmico
    analyzer = ThermalAnalyzer(
        img_height=512,
        img_width=640,
        smoothing_sigma=3,
        normalize=True
    )
    
    # Procesar cada imagen vinculada
    thermal_features = []
    procesadas_exitosas = 0
    procesadas_con_error = 0
    
    for idx, row in df.iterrows():
        if pd.notna(row['imagen_path']) and os.path.exists(row['imagen_path']):
            print(f"   Procesando: {os.path.basename(row['imagen_path'])}...", end=' ')
            
            try:
                features = analyzer.process_image(row['imagen_path'])
                
                if features.get('status') == 'success':
                    procesadas_exitosas += 1
                    print("✓")
                else:
                    procesadas_con_error += 1
                    print(f"⚠ ({features.get('status')})")
                
                thermal_features.append(features)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                thermal_features.append(analyzer._default_output('processing_error'))
                procesadas_con_error += 1
        else:
            # No hay imagen vinculada
            thermal_features.append(analyzer._default_output('no_image'))
    
    print(f"\n   ✓ Procesadas exitosamente: {procesadas_exitosas}")
    if procesadas_con_error > 0:
        print(f"   ⚠ Procesadas con errores: {procesadas_con_error}")
    
    # ========================================================================
    # PASO 4: COMBINAR DATOS
    # ========================================================================
    
    print("\n🔗 PASO 4: Combinando datos y features térmicas...")
    
    # Convertir lista de features a DataFrame
    thermal_df = pd.DataFrame(thermal_features)
    
    # Combinar con datos originales
    df_final = pd.concat([df, thermal_df], axis=1)
    
    print(f"   ✓ DataFrame final: {len(df_final)} filas, {len(df_final.columns)} columnas")
    
    # ========================================================================
    # PASO 5: GUARDAR RESULTADOS
    # ========================================================================
    
    print(f"\n💾 PASO 5: Guardando resultados en: {OUTPUT_CSV}")
    
    try:
        df_final.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        print(f"   ✓ Resultados guardados exitosamente")
    except Exception as e:
        print(f"   ❌ Error al guardar: {e}")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL")
    print("="*80)
    print(f"   • Filas procesadas: {len(df_final)}")
    print(f"   • Imágenes vinculadas: {imagenes_vinculadas}")
    print(f"   • Imágenes procesadas exitosamente: {procesadas_exitosas}")
    print(f"   • Columnas totales: {len(df_final.columns)}")
    print(f"   • Archivo de salida: {OUTPUT_CSV}")
    
    # Mostrar estadísticas de detección si hay datos
    if procesadas_exitosas > 0:
        print("\n   📈 Estadísticas de detección:")
        print(f"      • Promedio ratio crudo: {df_final['thermal_crudo_ratio'].mean():.2%}")
        print(f"      • Promedio ratio emulsión: {df_final['thermal_emulsion_ratio'].mean():.2%}")
        print(f"      • Promedio ratio agua: {df_final['thermal_agua_ratio'].mean():.2%}")
        print(f"      • Confianza promedio: {df_final['thermal_interface_confidence'].mean():.2f}")
    
    print("\n" + "="*80)
    print("✅ Procesamiento completado")
    print("="*80)
    
    return df_final


# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    resultado = main()
    
    # Opcional: mostrar primeras filas del resultado
    if resultado is not None:
        print("\n📋 Primeras 3 filas del resultado:")
        print(resultado.head(3))
