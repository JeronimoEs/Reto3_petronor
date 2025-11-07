"""
Análisis de resultados de imágenes térmicas procesadas.

Este módulo analiza los resultados de las imágenes térmicas y correlaciona
las proporciones de crudo, emulsión y agua con condiciones operativas y
meteorológicas del tanque.

PROCESO:
1. Cargar datos procesados con features térmicas
2. Calcular métricas derivadas (delta térmico, fiabilidad, estado operacional)
3. Analizar correlaciones entre variables
4. Detectar tendencias de acumulación de agua/emulsión
5. Calcular métricas agregadas por día y estado operacional
6. Generar visualizaciones comparativas
7. Generar resumen interpretativo con conclusiones automáticas
8. Exportar resultados
"""

import pandas as pd
import numpy as np
import os
import yaml
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / 'resultados_completos.csv'
CONFIG_FILE = BASE_DIR / 'config.yaml'
OUTPUT_DIR = BASE_DIR / 'resultados_analisis'

# ============================================================================
# FUNCIONES DE CARGA Y PREPARACIÓN
# ============================================================================

def cargar_config(config_path):
    """
    Carga la configuración desde un archivo YAML.
    
    Args:
        config_path (Path): Ruta al archivo de configuración.
    
    Returns:
        dict: Diccionario con la configuración.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuración cargada desde: {config_path}")
        return config
    except FileNotFoundError:
        print(f"⚠ ADVERTENCIA: No se encontró {config_path}. Usando valores por defecto.")
        return {}
    except Exception as e:
        print(f"⚠ Error al cargar configuración: {e}. Usando valores por defecto.")
        return {}

def cargar_datos_procesados(csv_path):
    """
    Carga los datos procesados con features térmicas.
    
    Args:
        csv_path (Path): Ruta al CSV con resultados completos.
    
    Returns:
        pd.DataFrame: DataFrame con los datos cargados.
    """
    print(f"\n📊 Cargando datos desde: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Convertir columna Día a datetime
        if 'Día' in df.columns:
            df['Día'] = pd.to_datetime(df['Día'], errors='coerce')
            df['fecha'] = df['Día'].dt.date
            df['hora'] = df['Día'].dt.hour
        
        print(f"   ✓ {len(df)} registros cargados")
        print(f"   ✓ {len(df.columns)} columnas")
        
        return df
    
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo: {csv_path}")
        return None
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")
        return None

def calcular_metricas_derivadas(df, config):
    """
    Calcula métricas derivadas: delta térmico, fiabilidad, estado operacional.
    
    Args:
        df (pd.DataFrame): DataFrame con datos originales.
        config (dict): Configuración con umbrales.
    
    Returns:
        pd.DataFrame: DataFrame con métricas adicionales.
    """
    print("\n🔢 Calculando métricas derivadas...")
    
    df = df.copy()
    
    # 1. Delta térmico (diferencia entre temperatura del tanque y ambiente)
    if 'T_TK' in df.columns and 'T_amb' in df.columns:
        df['delta_t_tank_ambient'] = df['T_TK'] - df['T_amb']
        print("   ✓ Delta térmico calculado")
    
    # 2. Fiabilidad térmica (basada en confidence)
    if 'thermal_interface_confidence' in df.columns:
        df['fiabilidad_termica'] = df['thermal_interface_confidence']
        
        # Clasificar fiabilidad
        umbrales = config.get('fiabilidad_termica', {})
        alta = umbrales.get('alta', 0.7)
        media = umbrales.get('media', 0.4)
        
        def clasificar_fiabilidad(conf):
            if pd.isna(conf):
                return 'desconocida'
            elif conf >= alta:
                return 'alta'
            elif conf >= media:
                return 'media'
            else:
                return 'baja'
        
        df['fiabilidad_categoria'] = df['fiabilidad_termica'].apply(clasificar_fiabilidad)
        print("   ✓ Fiabilidad térmica calculada")
    
    # 3. Estado operacional (LLENADO, DECANTACION, VACIADO)
    if 'Nivel TK %' in df.columns and 'Caudal' in df.columns:
        estados_config = config.get('estado_operacional', {})
        
        def determinar_estado(row):
            nivel = row.get('Nivel TK %', 0)
            caudal = row.get('Caudal', 0)
            
            if pd.isna(nivel) or pd.isna(caudal):
                return 'desconocido'
            
            # LLENADO: nivel bajo-medio y caudal positivo alto
            llenado = estados_config.get('llenado', {})
            if nivel >= llenado.get('nivel_min', 20) and caudal >= llenado.get('caudal_min', 100):
                return 'LLENADO'
            
            # VACIADO: nivel medio-alto y caudal negativo
            vaciado = estados_config.get('vaciado', {})
            if nivel >= vaciado.get('nivel_min', 20) and caudal <= vaciado.get('caudal_max', -100):
                return 'VACIADO'
            
            # DECANTACION: nivel alto y caudal cerca de cero
            decantacion = estados_config.get('decantacion', {})
            if nivel >= decantacion.get('nivel_min', 50):
                caudal_min = decantacion.get('caudal_min', -50)
                caudal_max = decantacion.get('caudal_max', 50)
                if caudal_min <= caudal <= caudal_max:
                    return 'DECANTACION'
            
            return 'TRANSICION'
        
        df['estado_operacional'] = df.apply(determinar_estado, axis=1)
        print("   ✓ Estado operacional determinado")
    
    # 4. Validar proporciones según umbrales
    umbrales = config.get('umbrales_proporciones', {})
    for capa in ['crudo', 'emulsion', 'agua']:
        col = f'thermal_{capa}_ratio'
        if col in df.columns:
            umbral_capa = umbrales.get(capa, {})
            min_val = umbral_capa.get('minimo', 0)
            max_val = umbral_capa.get('maximo', 1)
            
            df[f'{capa}_fuera_rango'] = (
                (df[col] < min_val) | (df[col] > max_val)
            ).astype(int)
    
    print(f"   ✓ Métricas derivadas calculadas: {len(df)} registros")
    
    return df

# ============================================================================
# ANÁLISIS DE CORRELACIONES
# ============================================================================

def analizar_correlaciones(df, config):
    """
    Analiza correlaciones entre proporciones térmicas y variables operativas/meteorológicas.
    
    Args:
        df (pd.DataFrame): DataFrame con datos y métricas.
        config (dict): Configuración.
    
    Returns:
        dict: Diccionario con resultados de correlaciones.
    """
    print("\n📈 Analizando correlaciones...")
    
    # Filtrar solo registros con status 'success'
    df_validos = df[df['status'] == 'success'].copy()
    
    if len(df_validos) == 0:
        print("   ⚠ No hay registros válidos para análisis")
        return {}
    
    # Variables térmicas a analizar
    vars_termicas = [
        'thermal_emulsion_ratio',
        'thermal_agua_ratio',
        'thermal_crudo_ratio',
        'thermal_interface_confidence'
    ]
    
    # Variables operativas
    vars_operativas = [
        'Nivel TK %',
        'Caudal',
        'T_TK',
        'delta_t_tank_ambient'
    ]
    
    # Variables meteorológicas
    vars_meteorologicas = [
        'Velocidad Viento',
        'Radiación Solar',
        'Humedad Relativa',
        'T_amb'
    ]
    
    # Todas las variables a correlacionar
    todas_vars = vars_operativas + vars_meteorologicas
    
    correlaciones = {}
    umbral_min = config.get('analisis', {}).get('correlacion_minima', 0.3)
    
    for var_termica in vars_termicas:
        if var_termica not in df_validos.columns:
            continue
        
        correlaciones[var_termica] = {}
        
        for var in todas_vars:
            if var not in df_validos.columns:
                continue
            
            # Filtrar valores válidos
            mask = df_validos[[var_termica, var]].notna().all(axis=1)
            if mask.sum() < 3:  # Mínimo 3 puntos para correlación
                continue
            
            try:
                corr, p_value = pearsonr(
                    df_validos.loc[mask, var_termica],
                    df_validos.loc[mask, var]
                )
                
                if abs(corr) >= umbral_min:
                    correlaciones[var_termica][var] = {
                        'correlacion': round(corr, 3),
                        'p_value': round(p_value, 4),
                        'significativa': p_value < 0.05
                    }
            except Exception as e:
                continue
    
    # Mostrar correlaciones significativas
    print(f"   ✓ Correlaciones analizadas")
    for var_termica, corrs in correlaciones.items():
        if corrs:
            print(f"      {var_termica}: {len(corrs)} correlaciones significativas")
    
    return correlaciones

# ============================================================================
# DETECCIÓN DE TENDENCIAS
# ============================================================================

def detectar_tendencias(df, config):
    """
    Detecta tendencias de acumulación de agua o aumento de emulsión.
    
    Args:
        df (pd.DataFrame): DataFrame con datos.
        config (dict): Configuración.
    
    Returns:
        dict: Diccionario con tendencias detectadas.
    """
    print("\n📊 Detectando tendencias...")
    
    df_validos = df[df['status'] == 'success'].copy()
    
    if len(df_validos) < 3:
        print("   ⚠ Insuficientes datos para detectar tendencias")
        return {}
    
    # Ordenar por fecha
    if 'Día' in df_validos.columns:
        df_validos = df_validos.sort_values('Día')
    
    tendencias = {}
    window = config.get('analisis', {}).get('tendencia_window', 5)
    umbral_cambio = config.get('analisis', {}).get('umbral_cambio_tendencia', 0.05)
    
    for ratio_col in ['thermal_emulsion_ratio', 'thermal_agua_ratio']:
        if ratio_col not in df_validos.columns:
            continue
        
        valores = df_validos[ratio_col].values
        cambios = []
        
        # Calcular cambios en ventana móvil
        for i in range(window, len(valores)):
            ventana_anterior = valores[i-window:i]
            ventana_actual = valores[i-window+1:i+1]
            
            if np.all(~np.isnan(ventana_anterior)) and np.all(~np.isnan(ventana_actual)):
                cambio = np.mean(ventana_actual) - np.mean(ventana_anterior)
                cambios.append(cambio)
        
        if cambios:
            cambio_promedio = np.mean(cambios)
            cambio_std = np.std(cambios)
            
            # Determinar tendencia
            if cambio_promedio > umbral_cambio:
                tendencia = 'aumento'
            elif cambio_promedio < -umbral_cambio:
                tendencia = 'disminucion'
            else:
                tendencia = 'estable'
            
            tendencias[ratio_col] = {
                'tendencia': tendencia,
                'cambio_promedio': round(cambio_promedio, 4),
                'cambio_std': round(cambio_std, 4),
                'magnitud': 'alta' if abs(cambio_promedio) > umbral_cambio * 2 else 'moderada'
            }
    
    for ratio, info in tendencias.items():
        print(f"   ✓ {ratio}: {info['tendencia']} ({info['magnitud']})")
    
    return tendencias

# ============================================================================
# MÉTRICAS AGREGADAS
# ============================================================================

def calcular_metricas_agregadas(df, config):
    """
    Calcula métricas agregadas por día y por estado operacional.
    
    Args:
        df (pd.DataFrame): DataFrame con datos.
        config (dict): Configuración.
    
    Returns:
        dict: Diccionario con métricas agregadas.
    """
    print("\n📊 Calculando métricas agregadas...")
    
    df_validos = df[df['status'] == 'success'].copy()
    
    if len(df_validos) == 0:
        return {}
    
    metricas = {}
    
    # 1. Por día
    if 'fecha' in df_validos.columns:
        metricas_por_dia = df_validos.groupby('fecha').agg({
            'thermal_crudo_ratio': ['mean', 'std', 'min', 'max'],
            'thermal_emulsion_ratio': ['mean', 'std', 'min', 'max'],
            'thermal_agua_ratio': ['mean', 'std', 'min', 'max'],
            'thermal_interface_confidence': 'mean',
            'delta_t_tank_ambient': 'mean',
            'Nivel TK %': 'mean',
            'Caudal': 'mean'
        }).round(3)
        
        metricas['por_dia'] = metricas_por_dia
        print(f"   ✓ Métricas por día: {len(metricas_por_dia)} días")
    
    # 2. Por estado operacional
    if 'estado_operacional' in df_validos.columns:
        metricas_por_estado = df_validos.groupby('estado_operacional').agg({
            'thermal_crudo_ratio': ['mean', 'std', 'count'],
            'thermal_emulsion_ratio': ['mean', 'std', 'count'],
            'thermal_agua_ratio': ['mean', 'std', 'count'],
            'thermal_interface_confidence': 'mean',
            'delta_t_tank_ambient': 'mean',
            'Nivel TK %': 'mean',
            'Caudal': 'mean'
        }).round(3)
        
        metricas['por_estado'] = metricas_por_estado
        print(f"   ✓ Métricas por estado: {len(metricas_por_estado)} estados")
    
    return metricas

# ============================================================================
# VISUALIZACIONES
# ============================================================================

def generar_visualizaciones(df, correlaciones, tendencias, metricas, config):
    """
    Genera visualizaciones comparativas.
    
    Args:
        df (pd.DataFrame): DataFrame con datos.
        correlaciones (dict): Resultados de correlaciones.
        tendencias (dict): Tendencias detectadas.
        metricas (dict): Métricas agregadas.
        config (dict): Configuración.
    """
    print("\n📊 Generando visualizaciones...")
    
    output_config = config.get('output', {})
    guardar = output_config.get('guardar_graficos', True)
    formato = output_config.get('formato_graficos', 'png')
    dpi = output_config.get('dpi_graficos', 150)
    
    if guardar:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    df_validos = df[df['status'] == 'success'].copy()
    
    if len(df_validos) == 0:
        print("   ⚠ No hay datos válidos para visualizar")
        return
    
    # 1. Series temporales de proporciones vs temperatura
    if 'Día' in df_validos.columns:
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Proporciones
        ax1 = axes[0]
        if 'thermal_emulsion_ratio' in df_validos.columns:
            ax1.plot(df_validos['Día'], df_validos['thermal_emulsion_ratio'], 
                    'o-', label='Emulsión', alpha=0.7)
        if 'thermal_agua_ratio' in df_validos.columns:
            ax1.plot(df_validos['Día'], df_validos['thermal_agua_ratio'], 
                    's-', label='Agua', alpha=0.7)
        ax1.set_ylabel('Proporción (ratio)', fontsize=12)
        ax1.set_title('Evolución Temporal de Proporciones de Emulsión y Agua', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Temperatura
        ax2 = axes[1]
        if 'T_TK' in df_validos.columns:
            ax2.plot(df_validos['Día'], df_validos['T_TK'], 
                    'r-', label='T Tanque', alpha=0.7)
        if 'T_amb' in df_validos.columns:
            ax2.plot(df_validos['Día'], df_validos['T_amb'], 
                    'b-', label='T Ambiente', alpha=0.7)
        if 'delta_t_tank_ambient' in df_validos.columns:
            ax2.plot(df_validos['Día'], df_validos['delta_t_tank_ambient'], 
                    'g--', label='ΔT (Tanque-Ambiente)', alpha=0.7)
        ax2.set_xlabel('Fecha', fontsize=12)
        ax2.set_ylabel('Temperatura (°C)', fontsize=12)
        ax2.set_title('Evolución Temporal de Temperaturas', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if guardar:
            plt.savefig(OUTPUT_DIR / f'series_temporales.{formato}', dpi=dpi, bbox_inches='tight')
            print(f"   ✓ Guardado: series_temporales.{formato}")
        plt.close()
    
    # 2. Correlación emulsion_ratio vs delta_t
    if 'thermal_emulsion_ratio' in df_validos.columns and 'delta_t_tank_ambient' in df_validos.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        mask = df_validos[['thermal_emulsion_ratio', 'delta_t_tank_ambient']].notna().all(axis=1)
        
        if mask.sum() > 0:
            ax.scatter(df_validos.loc[mask, 'delta_t_tank_ambient'],
                      df_validos.loc[mask, 'thermal_emulsion_ratio'],
                      alpha=0.6, s=50)
            
            # Línea de tendencia
            z = np.polyfit(df_validos.loc[mask, 'delta_t_tank_ambient'],
                          df_validos.loc[mask, 'thermal_emulsion_ratio'], 1)
            p = np.poly1d(z)
            ax.plot(df_validos.loc[mask, 'delta_t_tank_ambient'],
                   p(df_validos.loc[mask, 'delta_t_tank_ambient']),
                   "r--", alpha=0.8, linewidth=2, label='Tendencia')
            
            ax.set_xlabel('ΔT (Tanque - Ambiente) (°C)', fontsize=12)
            ax.set_ylabel('Proporción de Emulsión', fontsize=12)
            ax.set_title('Correlación: Proporción de Emulsión vs Diferencial Térmico', 
                        fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if guardar:
                plt.savefig(OUTPUT_DIR / f'correlacion_emulsion_deltaT.{formato}', dpi=dpi, bbox_inches='tight')
                print(f"   ✓ Guardado: correlacion_emulsion_deltaT.{formato}")
            plt.close()
    
    # 3. Distribución por estado operacional
    if 'estado_operacional' in df_validos.columns:
        estados = df_validos['estado_operacional'].unique()
        estados_validos = [e for e in estados if e != 'desconocido']
        
        if len(estados_validos) > 0:
            fig, axes = plt.subplots(1, 3, figsize=(16, 5))
            
            ratios = ['thermal_crudo_ratio', 'thermal_emulsion_ratio', 'thermal_agua_ratio']
            nombres = ['Crudo', 'Emulsión', 'Agua']
            
            for idx, (ratio, nombre) in enumerate(zip(ratios, nombres)):
                if ratio in df_validos.columns:
                    data_plot = [df_validos[df_validos['estado_operacional'] == estado][ratio].dropna().values 
                                for estado in estados_validos]
                    
                    axes[idx].boxplot(data_plot, labels=estados_validos)
                    axes[idx].set_ylabel('Proporción', fontsize=11)
                    axes[idx].set_title(f'Distribución de {nombre} por Estado', fontsize=12, fontweight='bold')
                    axes[idx].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if guardar:
                plt.savefig(OUTPUT_DIR / f'distribucion_por_estado.{formato}', dpi=dpi, bbox_inches='tight')
                print(f"   ✓ Guardado: distribucion_por_estado.{formato}")
            plt.close()
    
    print("   ✓ Visualizaciones generadas")

# ============================================================================
# RESUMEN INTERPRETATIVO
# ============================================================================

def generar_resumen_interpretativo(df, correlaciones, tendencias, metricas, config):
    """
    Genera un resumen interpretativo con conclusiones automáticas.
    
    Args:
        df (pd.DataFrame): DataFrame con datos.
        correlaciones (dict): Resultados de correlaciones.
        tendencias (dict): Tendencias detectadas.
        metricas (dict): Métricas agregadas.
        config (dict): Configuración.
    
    Returns:
        str: Resumen interpretativo en texto.
    """
    print("\n📝 Generando resumen interpretativo...")
    
    df_validos = df[df['status'] == 'success'].copy()
    
    resumen = []
    resumen.append("="*80)
    resumen.append("📊 RESUMEN INTERPRETATIVO - ANÁLISIS TÉRMICO")
    resumen.append("="*80)
    resumen.append("")
    
    # 1. Fiabilidad de las imágenes
    resumen.append("1. FIABILIDAD DE LAS IMÁGENES")
    resumen.append("-" * 80)
    
    if 'fiabilidad_termica' in df_validos.columns:
        fiabilidad_promedio = df_validos['fiabilidad_termica'].mean()
        fiabilidad_std = df_validos['fiabilidad_termica'].std()
        
        umbrales = config.get('fiabilidad_termica', {})
        alta = umbrales.get('alta', 0.7)
        
        resumen.append(f"   • Fiabilidad promedio: {fiabilidad_promedio:.3f} (±{fiabilidad_std:.3f})")
        
        if fiabilidad_promedio >= alta:
            resumen.append("   • CONCLUSIÓN: Alta fiabilidad en las detecciones térmicas.")
        else:
            resumen.append("   • CONCLUSIÓN: Fiabilidad moderada-baja. Revisar calibración.")
        
        if 'fiabilidad_categoria' in df_validos.columns:
            distrib = df_validos['fiabilidad_categoria'].value_counts()
            resumen.append(f"   • Distribución: {dict(distrib)}")
    else:
        resumen.append("   • No se pudo calcular la fiabilidad (falta thermal_interface_confidence)")
    
    resumen.append("")
    
    # 2. Análisis de correlaciones
    resumen.append("2. CORRELACIONES SIGNIFICATIVAS")
    resumen.append("-" * 80)
    
    if correlaciones:
        for var_termica, corrs in correlaciones.items():
            if corrs:
                resumen.append(f"   {var_termica}:")
                for var, info in corrs.items():
                    signo = "+" if info['correlacion'] > 0 else ""
                    resumen.append(f"      • {var}: {signo}{info['correlacion']:.3f} "
                                f"(p={info['p_value']:.4f})")
    else:
        resumen.append("   • No se encontraron correlaciones significativas")
    
    resumen.append("")
    
    # 3. Tendencias detectadas
    resumen.append("3. TENDENCIAS DETECTADAS")
    resumen.append("-" * 80)
    
    if tendencias:
        for ratio, info in tendencias.items():
            resumen.append(f"   {ratio}:")
            resumen.append(f"      • Tendencia: {info['tendencia']}")
            resumen.append(f"      • Cambio promedio: {info['cambio_promedio']:.4f}")
            resumen.append(f"      • Magnitud: {info['magnitud']}")
            
            if info['tendencia'] == 'aumento':
                if 'agua' in ratio:
                    resumen.append("      • ⚠ ADVERTENCIA: Acumulación de agua detectada")
                elif 'emulsion' in ratio:
                    resumen.append("      • ⚠ ADVERTENCIA: Aumento de emulsión detectado")
    else:
        resumen.append("   • No se detectaron tendencias significativas")
    
    resumen.append("")
    
    # 4. Impacto de condiciones meteorológicas
    resumen.append("4. IMPACTO DE CONDICIONES METEOROLÓGICAS")
    resumen.append("-" * 80)
    
    meteo_config = config.get('meteorologia', {})
    
    if 'Velocidad Viento' in df_validos.columns:
        viento_promedio = df_validos['Velocidad Viento'].mean()
        viento_alto = meteo_config.get('viento', {}).get('alto', 3.0)
        
        if viento_promedio > viento_alto:
            resumen.append(f"   • Viento alto detectado ({viento_promedio:.2f} m/s)")
            resumen.append("     → Puede afectar la separación térmica y crear turbulencia")
    
    if 'Radiación Solar' in df_validos.columns:
        radiacion_promedio = df_validos['Radiación Solar'].mean()
        radiacion_alta = meteo_config.get('radiacion_solar', {}).get('alta', 400.0)
        
        if radiacion_promedio > radiacion_alta:
            resumen.append(f"   • Radiación solar alta ({radiacion_promedio:.2f} W/m²)")
            resumen.append("     → Puede aumentar el diferencial térmico y mejorar separación")
    
    resumen.append("")
    
    # 5. Métricas por estado operacional
    resumen.append("5. MÉTRICAS POR ESTADO OPERACIONAL")
    resumen.append("-" * 80)
    
    if 'por_estado' in metricas:
        metricas_estado = metricas['por_estado']
        resumen.append(metricas_estado.to_string())
    else:
        resumen.append("   • No se calcularon métricas por estado")
    
    resumen.append("")
    
    # 6. Conclusiones y recomendaciones
    resumen.append("6. CONCLUSIONES Y RECOMENDACIONES")
    resumen.append("-" * 80)
    
    # Detectar problemas
    problemas = []
    
    if 'thermal_agua_ratio' in df_validos.columns:
        agua_promedio = df_validos['thermal_agua_ratio'].mean()
        umbral_agua = config.get('umbrales_proporciones', {}).get('agua', {}).get('maximo', 0.3)
        if agua_promedio > umbral_agua:
            problemas.append(f"Acumulación de agua alta ({agua_promedio:.2%} > {umbral_agua:.2%})")
    
    if 'thermal_emulsion_ratio' in df_validos.columns:
        emulsion_promedio = df_validos['thermal_emulsion_ratio'].mean()
        umbral_emulsion = config.get('umbrales_proporciones', {}).get('emulsion', {}).get('maximo', 0.6)
        if emulsion_promedio > umbral_emulsion:
            problemas.append(f"Emulsión alta ({emulsion_promedio:.2%} > {umbral_emulsion:.2%})")
    
    if problemas:
        resumen.append("   ⚠ PROBLEMAS DETECTADOS:")
        for problema in problemas:
            resumen.append(f"      • {problema}")
    else:
        resumen.append("   ✓ No se detectaron problemas críticos en las proporciones")
    
    resumen.append("")
    resumen.append("="*80)
    resumen.append(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    resumen.append("="*80)
    
    resumen_texto = "\n".join(resumen)
    
    print("   ✓ Resumen generado")
    
    return resumen_texto

# ============================================================================
# EXPORTACIÓN DE RESULTADOS
# ============================================================================

def exportar_resultados(df, correlaciones, tendencias, metricas, resumen, config):
    """
    Exporta todos los resultados a archivos.
    
    Args:
        df (pd.DataFrame): DataFrame con datos.
        correlaciones (dict): Resultados de correlaciones.
        tendencias (dict): Tendencias detectadas.
        metricas (dict): Métricas agregadas.
        resumen (str): Resumen interpretativo.
        config (dict): Configuración.
    """
    print("\n💾 Exportando resultados...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. DataFrame completo con métricas
    output_file = OUTPUT_DIR / 'analisis_completo.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"   ✓ Datos completos: {output_file}")
    
    # 2. Correlaciones
    if correlaciones:
        corr_df = pd.DataFrame([
            {
                'variable_termica': var_termica,
                'variable': var,
                'correlacion': info['correlacion'],
                'p_value': info['p_value'],
                'significativa': info['significativa']
            }
            for var_termica, corrs in correlaciones.items()
            for var, info in corrs.items()
        ])
        
        corr_file = OUTPUT_DIR / 'correlaciones.csv'
        corr_df.to_csv(corr_file, index=False, encoding='utf-8')
        print(f"   ✓ Correlaciones: {corr_file}")
    
    # 3. Tendencias
    if tendencias:
        tendencias_df = pd.DataFrame(tendencias).T
        tendencias_file = OUTPUT_DIR / 'tendencias.csv'
        tendencias_df.to_csv(tendencias_file, encoding='utf-8')
        print(f"   ✓ Tendencias: {tendencias_file}")
    
    # 4. Métricas agregadas
    if 'por_dia' in metricas:
        metricas_dia_file = OUTPUT_DIR / 'metricas_por_dia.csv'
        metricas['por_dia'].to_csv(metricas_dia_file, encoding='utf-8')
        print(f"   ✓ Métricas por día: {metricas_dia_file}")
    
    if 'por_estado' in metricas:
        metricas_estado_file = OUTPUT_DIR / 'metricas_por_estado.csv'
        metricas['por_estado'].to_csv(metricas_estado_file, encoding='utf-8')
        print(f"   ✓ Métricas por estado: {metricas_estado_file}")
    
    # 5. Resumen interpretativo
    resumen_file = OUTPUT_DIR / 'resumen_interpretativo.txt'
    with open(resumen_file, 'w', encoding='utf-8') as f:
        f.write(resumen)
    print(f"   ✓ Resumen interpretativo: {resumen_file}")
    
    print(f"\n   ✅ Todos los resultados exportados a: {OUTPUT_DIR}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Función principal que ejecuta todo el análisis.
    """
    print("="*80)
    print("📊 ANÁLISIS DE RESULTADOS TÉRMICOS - RETO3 PETRONOR")
    print("="*80)
    
    # 1. Cargar configuración
    config = cargar_config(CONFIG_FILE)
    
    # 2. Cargar datos
    df = cargar_datos_procesados(INPUT_CSV)
    if df is None:
        return
    
    # 3. Calcular métricas derivadas
    df = calcular_metricas_derivadas(df, config)
    
    # 4. Analizar correlaciones
    correlaciones = analizar_correlaciones(df, config)
    
    # 5. Detectar tendencias
    tendencias = detectar_tendencias(df, config)
    
    # 6. Calcular métricas agregadas
    metricas = calcular_metricas_agregadas(df, config)
    
    # 7. Generar visualizaciones
    generar_visualizaciones(df, correlaciones, tendencias, metricas, config)
    
    # 8. Generar resumen interpretativo
    resumen = generar_resumen_interpretativo(df, correlaciones, tendencias, metricas, config)
    
    # Mostrar resumen en consola
    print("\n" + resumen)
    
    # 9. Exportar resultados
    exportar_resultados(df, correlaciones, tendencias, metricas, resumen, config)
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)
    
    return df, correlaciones, tendencias, metricas, resumen

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    resultado = main()

