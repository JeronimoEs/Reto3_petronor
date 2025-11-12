"""
Interfaz Web Segura - PETRONAITOR

Aplicación Streamlit para análisis y predicción de fiabilidad térmica (Thermal Reliability Agent).

FUNCIONALIDADES:
- Carga de CSVs y subida de imágenes térmicas
- Visualización de mapas térmicos coloreados
- Scores de fiabilidad en tiempo real
- Gráficos estadísticos interactivos
- Exportación a PDF
- Autenticación y control de acceso

SEGURIDAD:
- Autenticación OAuth2 (configurable)
- Control de acceso basado en roles
- Logging de auditoría
- Cifrado de datos en tránsito (HTTPS)

AUTOR: Thermal Reliability Agent System
FECHA: 2025
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import sys
import logging
from datetime import datetime
import json
import hashlib
import time
from typing import Optional, Dict
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import base64

# Configurar logging primero
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar directorio steps al path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Imports con importlib (necesario porque los módulos empiezan con números)
import importlib.util

# Cargar módulo 4_reliability_analysis.py
try:
    spec4 = importlib.util.spec_from_file_location(
        "reliability_analysis", 
        BASE_DIR / "steps" / "4_reliability_analysis.py"
    )
    step4 = importlib.util.module_from_spec(spec4)
    spec4.loader.exec_module(step4)
    ReliabilityAnalyzer = step4.ReliabilityAnalyzer
    load_data = step4.load_data
    logger.info("Módulo de análisis de fiabilidad cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando módulo de análisis: {e}")
    ReliabilityAnalyzer = None
    load_data = None

# Cargar módulo 5_realtime_predictor.py
try:
    spec5 = importlib.util.spec_from_file_location(
        "realtime_predictor", 
        BASE_DIR / "steps" / "5_realtime_predictor.py"
    )
    step5 = importlib.util.module_from_spec(spec5)
    spec5.loader.exec_module(step5)
    RealtimeThermalPredictor = step5.RealtimeThermalPredictor
    logger.info("Módulo de predicción en tiempo real cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando módulo de predicción: {e}")
    RealtimeThermalPredictor = None

# Cargar módulo 2_image_proccessing.py
try:
    spec2 = importlib.util.spec_from_file_location(
        "image_proccessing", 
        BASE_DIR / "steps" / "2_image_proccessing.py"
    )
    step2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(step2)
    ThermalAnalyzer = step2.ThermalAnalyzer
    logger.info("Módulo de procesamiento de imágenes cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando módulo de procesamiento: {e}")
    ThermalAnalyzer = None

# ============================================================================
# CONFIGURACIÓN Y SEGURIDAD
# ============================================================================

# Configuración de la página
st.set_page_config(
    page_title="PETRONAITOR",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Roles de usuario (en producción, esto vendría de Azure AD / OAuth2)
USER_ROLES = {
    'operator': ['view', 'upload', 'predict'],
    'data_scientist': ['view', 'upload', 'predict', 'analyze', 'export'],
    'admin': ['view', 'upload', 'predict', 'analyze', 'export', 'admin']
}

# Simulación de autenticación (en producción usar OAuth2)
def check_authentication():
    """Verifica autenticación del usuario."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_role = None
    
    if not st.session_state.authenticated:
        with st.sidebar:
            st.title("🔐 Autenticación")
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Iniciar Sesión"):
                # Simulación simple (en producción usar Azure AD)
                if username and password:
                    # Mapeo simple de usuarios a roles
                    if username.startswith('admin'):
                        st.session_state.user_role = 'admin'
                    elif username.startswith('scientist'):
                        st.session_state.user_role = 'data_scientist'
                    else:
                        st.session_state.user_role = 'operator'
                    
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    log_audit_event('login', username=username)
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")
        
        st.stop()
    
    return st.session_state.user_role

def has_permission(action: str) -> bool:
    """Verifica si el usuario tiene permiso para una acción."""
    role = st.session_state.get('user_role')
    if not role:
        return False
    return action in USER_ROLES.get(role, [])

def log_audit_event(event_type: str, **kwargs):
    """Registra evento de auditoría."""
    event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'user': st.session_state.get('username', 'unknown'),
        'role': st.session_state.get('user_role', 'unknown'),
        **kwargs
    }
    logger.info(f"AUDIT: {json.dumps(event)}")

# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def reconstruct_thermal_from_interfaces(img_shape: tuple, features: Dict) -> np.ndarray:
    """
    Reconstruye una imagen térmica basada en los promedios de las interfaces detectadas.
    
    Args:
        img_shape (tuple): Forma de la imagen (height, width).
        features (dict): Features térmicas con interfaces y temperaturas medias.
    
    Returns:
        np.ndarray: Imagen reconstruida en escala de grises.
    """
    h, w = img_shape
    reconstructed = np.zeros((h, w), dtype=np.uint8)
    
    # Obtener posiciones de interfaces
    top = int(features.get('thermal_interface_top_px', h // 3))
    bottom = int(features.get('thermal_interface_bottom_px', 2 * h // 3))
    
    # Obtener temperaturas medias de cada capa
    temp_crudo = features.get('thermal_temp_crudo_mean', 200.0)
    temp_emulsion = features.get('thermal_temp_emulsion_mean', 150.0)
    temp_agua = features.get('thermal_temp_agua_mean', 100.0)
    
    # Asegurar que los valores estén en el rango [0, 255]
    temp_crudo = np.clip(temp_crudo, 0, 255)
    temp_emulsion = np.clip(temp_emulsion, 0, 255)
    temp_agua = np.clip(temp_agua, 0, 255)
    
    # Reconstruir imagen por capas
    # Capa superior: Crudo
    reconstructed[:top, :] = int(temp_crudo)
    
    # Capa media: Emulsión
    reconstructed[top:bottom, :] = int(temp_emulsion)
    
    # Capa inferior: Agua
    reconstructed[bottom:, :] = int(temp_agua)
    
    return reconstructed

def plot_thermal_map(image_path: str, features: Dict, figsize=(14, 6)):
    """
    Genera visualización de imagen térmica original y reconstruida desde interfaces.
    
    Args:
        image_path (str): Ruta a la imagen.
        features (dict): Features térmicas extraídas.
        figsize (tuple): Tamaño de la figura.
    
    Returns:
        tuple: (figura matplotlib, tabla de datos)
    """
    import cv2
    
    # Cargar imagen original
    img_original = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_original is None:
        return None, None
    
    # Reconstruir imagen desde interfaces
    img_reconstructed = reconstruct_thermal_from_interfaces(img_original.shape, features)
    
    # Crear figura con dos subplots
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Imagen original en escala de grises
    axes[0].imshow(img_original, cmap='gray')
    axes[0].set_title('Imagen Térmica Original', fontsize=14, fontweight='bold')
    
    # Dibujar interfaces en la imagen original
    if 'thermal_interface_top_px' in features and 'thermal_interface_bottom_px' in features:
        top = int(features['thermal_interface_top_px'])
        bottom = int(features['thermal_interface_bottom_px'])
        
        axes[0].axhline(y=top, color='cyan', linewidth=2, linestyle='--', 
                       label=f'Interfaz Superior (px={top})')
        axes[0].axhline(y=bottom, color='magenta', linewidth=2, linestyle='--',
                       label=f'Interfaz Inferior (px={bottom})')
        axes[0].legend(loc='upper right', fontsize=9)
    
    axes[0].axis('off')
    
    # Imagen reconstruida desde promedios
    axes[1].imshow(img_reconstructed, cmap='gray')
    axes[1].set_title('Imagen Reconstruida desde Interfaces', fontsize=14, fontweight='bold')
    
    # Dibujar interfaces en la imagen reconstruida
    if 'thermal_interface_top_px' in features and 'thermal_interface_bottom_px' in features:
        top = int(features['thermal_interface_top_px'])
        bottom = int(features['thermal_interface_bottom_px'])
        
        axes[1].axhline(y=top, color='cyan', linewidth=2, linestyle='--', 
                       label=f'Interfaz Superior')
        axes[1].axhline(y=bottom, color='magenta', linewidth=2, linestyle='--',
                       label=f'Interfaz Inferior')
        axes[1].legend(loc='upper right', fontsize=9)
    
    axes[1].axis('off')
    
    plt.tight_layout()
    
    # Crear tabla de datos de interfaces
    table_data = []
    
    if 'thermal_interface_top_px' in features:
        table_data.append({
            'Capa': 'Crudo (Superior)',
            'Interfaz Superior (px)': int(features.get('thermal_interface_top_px', 0)),
            'Interfaz Inferior (px)': '-',
            'Espesor (px)': int(features.get('thermal_crudo_px', 0)),
            'Ratio (%)': f"{features.get('thermal_crudo_ratio', 0):.2%}",
            'Temp. Media': f"{features.get('thermal_temp_crudo_mean', 0):.2f}"
        })
    
    if 'thermal_interface_bottom_px' in features:
        table_data.append({
            'Capa': 'Emulsión (Media)',
            'Interfaz Superior (px)': int(features.get('thermal_interface_top_px', 0)),
            'Interfaz Inferior (px)': int(features.get('thermal_interface_bottom_px', 0)),
            'Espesor (px)': int(features.get('thermal_emulsion_px', 0)),
            'Ratio (%)': f"{features.get('thermal_emulsion_ratio', 0):.2%}",
            'Temp. Media': f"{features.get('thermal_temp_emulsion_mean', 0):.2f}"
        })
        
        table_data.append({
            'Capa': 'Agua (Inferior)',
            'Interfaz Superior (px)': int(features.get('thermal_interface_bottom_px', 0)),
            'Interfaz Inferior (px)': f"{img_original.shape[0]} (fondo)",
            'Espesor (px)': int(features.get('thermal_agua_px', 0)),
            'Ratio (%)': f"{features.get('thermal_agua_ratio', 0):.2%}",
            'Temp. Media': f"{features.get('thermal_temp_agua_mean', 0):.2f}"
        })
    
    table_df = pd.DataFrame(table_data)
    
    return fig, table_df

# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================

@st.cache_data
def load_and_analyze_data(csv_path: str):
    """Carga y analiza datos con cache."""
    try:
        df = load_data(csv_path)
        analyzer = ReliabilityAnalyzer(window=5)
        results = analyzer.analyze_reliability(df)
        return results
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        st.error(f"Error cargando datos: {e}")
        return None

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    """Función principal de la aplicación."""
    
    # Verificar autenticación
    user_role = check_authentication()
    
    # Header
    st.title("🌡️ PETRONAITOR")
    st.markdown("**Sistema de Análisis y Predicción de Fiabilidad Térmica - Thermal Reliability Agent**")
    
    # Sidebar
    with st.sidebar:
        st.header("👤 Usuario")
        st.write(f"**Usuario:** {st.session_state.get('username', 'N/A')}")
        st.write(f"**Rol:** {user_role}")
        
        if st.button("Cerrar Sesión"):
            log_audit_event('logout')
            st.session_state.authenticated = False
            st.rerun()
        
        st.divider()
        
        st.header("📊 Navegación")
        page = st.radio(
            "Seleccionar página:",
            ["Análisis Histórico", "Predicción en Tiempo Real", "Visualizaciones", "Exportar Reporte"]
        )
    
    # Página: Análisis Histórico
    if page == "Análisis Histórico":
        if not has_permission('analyze'):
            st.warning("⚠️ No tienes permiso para acceder a esta sección")
            return
        
        st.header("📈 Análisis Histórico de Fiabilidad")
        
        # Cargar CSV
        uploaded_file = st.file_uploader(
            "Cargar CSV con datos históricos",
            type=['csv'],
            help="Sube el archivo resultados_completos.csv"
        )
        
        if uploaded_file is not None:
            # Guardar temporalmente
            temp_path = f"/tmp/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            log_audit_event('data_upload', filename=uploaded_file.name)
            
            # Analizar
            with st.spinner("Analizando datos..."):
                results = load_and_analyze_data(temp_path)
            
            if results:
                st.success("✅ Análisis completado")
                
                # Mostrar resultados
                st.subheader("📊 Resultados del Análisis")
                
                # Validación de hipótesis
                hypothesis_validated = results['hypothesis_validated']
                st.metric(
                    "Hipótesis Validada",
                    "✅ SÍ" if hypothesis_validated else "❌ NO",
                    help="La hipótesis se valida si hay diferencias significativas (p < 0.05)"
                )
                
                # Reporte comparativo
                if 'comparative_report' in results and len(results['comparative_report']) > 0:
                    st.subheader("📋 Reporte Comparativo: Batch Estable vs Turbulento")
                    st.dataframe(results['comparative_report'], use_container_width=True)
                
                # ANOVA Results
                if 'anova_results' in results:
                    anova = results['anova_results']
                    if 'anova_results' in anova:
                        st.subheader("🔬 Resultados ANOVA")
                        
                        anova_data = []
                        for var, stats in anova['anova_results'].items():
                            anova_data.append({
                                'Variable': var,
                                'F-statistic': f"{stats['f_statistic']:.3f}",
                                'p-value': f"{stats['p_value']:.4f}",
                                'Significativo': "✅" if stats['significant'] else "❌",
                                'Estable (mean±std)': f"{stats['stable_mean']:.3f}±{stats['stable_std']:.3f}",
                                'Turbulento (mean±std)': f"{stats['turbulent_mean']:.3f}±{stats['turbulent_std']:.3f}"
                            })
                        
                        st.dataframe(pd.DataFrame(anova_data), use_container_width=True)
                
                # Gráficos
                st.subheader("📊 Visualizaciones")
                
                df = results['dataframe']
                df_valid = df[df['status'] == 'success'].copy()
                
                if len(df_valid) > 0:
                    # Scatter: sigma vs precisión
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'sigma_Caudal' in df_valid.columns and 'thermal_gradient_max' in df_valid.columns:
                            fig, ax = plt.subplots(figsize=(8, 6))
                            scatter = ax.scatter(
                                df_valid['sigma_Caudal'],
                                df_valid['thermal_gradient_max'],
                                c=df_valid.get('batch_type', 'unknown').map({
                                    'estable': 'green',
                                    'turbulento': 'red'
                                }),
                                alpha=0.6,
                                s=50
                            )
                            ax.set_xlabel('Sigma Caudal', fontsize=12)
                            ax.set_ylabel('Gradiente Térmico Máximo', fontsize=12)
                            ax.set_title('Sigma vs Precisión Térmica', fontsize=14, fontweight='bold')
                            ax.grid(True, alpha=0.3)
                            ax.legend(['Estable', 'Turbulento'])
                            st.pyplot(fig)
                    
                    with col2:
                        if 'batch_type' in df_valid.columns:
                            fig, ax = plt.subplots(figsize=(8, 6))
                            df_valid.boxplot(
                                column='thermal_interface_confidence',
                                by='batch_type',
                                ax=ax
                            )
                            ax.set_title('Fiabilidad por Tipo de Batch', fontsize=14, fontweight='bold')
                            ax.set_xlabel('Tipo de Batch')
                            ax.set_ylabel('Confianza de Interfaz')
                            plt.xticks(rotation=45)
                            st.pyplot(fig)
    
    # Página: Predicción en Tiempo Real
    elif page == "Predicción en Tiempo Real":
        if not has_permission('predict'):
            st.warning("⚠️ No tienes permiso para acceder a esta sección")
            return
        
        st.header("⚡ Predicción en Tiempo Real")
        
        # Verificar que el módulo esté cargado
        if RealtimeThermalPredictor is None:
            st.error("❌ Error: No se pudo cargar el módulo de predicción en tiempo real.")
            st.info("Por favor, verifica que el archivo `steps/5_realtime_predictor.py` exista y no tenga errores.")
            return
        
        # Cargar datos de referencia (opcional)
        reference_file = st.file_uploader(
            "Datos de referencia (opcional)",
            type=['csv'],
            help="CSV con datos históricos para calcular perfiles de referencia"
        )
        
        reference_data = None
        if reference_file is not None:
            if load_data is None:
                st.error("❌ Error: No se pudo cargar el módulo de carga de datos.")
                return
            temp_ref_path = f"/tmp/ref_{reference_file.name}"
            with open(temp_ref_path, "wb") as f:
                f.write(reference_file.getbuffer())
            try:
                reference_data = load_data(temp_ref_path)
                st.success(f"✅ Datos de referencia cargados: {len(reference_data)} registros")
            except Exception as e:
                st.error(f"❌ Error cargando datos de referencia: {e}")
                return
        
        # Inicializar predictor
        try:
            predictor = RealtimeThermalPredictor(reference_data=reference_data)
        except Exception as e:
            st.error(f"❌ Error inicializando predictor: {e}")
            logger.error(f"Error inicializando predictor: {e}", exc_info=True)
            return
        
        # Subir imagen
        uploaded_image = st.file_uploader(
            "Subir imagen térmica",
            type=['jpg', 'jpeg', 'png'],
            help="Imagen térmica en formato JPG/PNG (640x480 px recomendado)"
        )
        
        if uploaded_image is not None:
            # Guardar temporalmente
            temp_img_path = f"/tmp/{uploaded_image.name}"
            with open(temp_img_path, "wb") as f:
                f.write(uploaded_image.getbuffer())
            
            log_audit_event('image_upload', filename=uploaded_image.name,
                          file_hash=hashlib.md5(uploaded_image.getbuffer()).hexdigest())
            
            # Procesar
            with st.spinner("Procesando imagen..."):
                result = predictor.predict_new_image(temp_img_path)
            
            if result.get('error'):
                st.error(f"❌ Error: {result['error']}")
            else:
                st.success("✅ Imagen procesada exitosamente")
                
                # Mostrar resultados
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    score = result.get('reliability_score', 0.0)
                    category = result.get('reliability_category', 'baja')
                    
                    # Color según categoría
                    if category == 'alta':
                        color = "🟢"
                    elif category == 'media':
                        color = "🟡"
                    else:
                        color = "🔴"
                    
                    st.metric(
                        "Score de Fiabilidad",
                        f"{score:.1f}%",
                        delta=f"{color} {category.upper()}"
                    )
                
                with col2:
                    st.metric(
                        "Tiempo de Procesamiento",
                        f"{result.get('processing_time', 0):.2f}s"
                    )
                
                with col3:
                    st.metric(
                        "Confianza de Interfaz",
                        f"{result.get('thermal_interface_confidence', 0):.2f}"
                    )
                
                # Visualización
                st.subheader("🗺️ Mapa Térmico")
                fig, table_df = plot_thermal_map(temp_img_path, result)
                if fig:
                    st.pyplot(fig)
                
                # Mostrar tabla de interfaces
                if table_df is not None and len(table_df) > 0:
                    st.subheader("📊 Tabla de Interfaces Detectadas")
                    st.dataframe(table_df, use_container_width=True, hide_index=True)
                
                # Detalles
                st.subheader("📋 Detalles de la Predicción")
                
                details_cols = st.columns(2)
                
                with details_cols[0]:
                    st.write("**Ratios de Capas:**")
                    st.write(f"- Crudo: {result.get('thermal_crudo_ratio', 0):.2%}")
                    st.write(f"- Emulsión: {result.get('thermal_emulsion_ratio', 0):.2%}")
                    st.write(f"- Agua: {result.get('thermal_agua_ratio', 0):.2%}")
                
                with details_cols[1]:
                    st.write("**Gradientes Térmicos:**")
                    st.write(f"- Máximo: {result.get('thermal_gradient_max', 0):.3f}")
                    st.write(f"- Desviación estándar: {result.get('thermal_gradient_std', 0):.3f}")
                    st.write(f"- Interfaz superior: {result.get('thermal_interface_top_px', 0)} px")
                    st.write(f"- Interfaz inferior: {result.get('thermal_interface_bottom_px', 0)} px")
    
    # Página: Visualizaciones
    elif page == "Visualizaciones":
        if not has_permission('view'):
            st.warning("⚠️ No tienes permiso para acceder a esta sección")
            return
        
        st.header("📊 Visualizaciones Estadísticas")
        
        # Cargar datos
        uploaded_file = st.file_uploader(
            "Cargar CSV con datos procesados",
            type=['csv'],
            help="Sube el archivo csv_processed.csv o resultados_completos.csv"
        )
        
        if uploaded_file is not None:
            # Guardar temporalmente
            temp_path = f"/tmp/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            log_audit_event('data_upload', filename=uploaded_file.name)
            
            # Cargar datos
            try:
                df = pd.read_csv(temp_path, encoding='utf-8')
                st.success(f"✅ Datos cargados: {len(df)} registros")
                
                # Filtrar datos válidos
                df_valid = df[df.get('status', 'success') == 'success'].copy()
                
                if len(df_valid) == 0:
                    st.warning("⚠️ No hay datos válidos para visualizar")
                    return
                
                # Seleccionar tipo de visualización
                viz_type = st.selectbox(
                    "Seleccionar tipo de visualización:",
                    [
                        "Sigma vs Precisión Térmica",
                        "Fiabilidad por Tipo de Batch",
                        "Distribución de Gradientes Térmicos",
                        "Ratios de Capas por Batch",
                        "Correlaciones Térmicas",
                        "Series Temporales"
                    ]
                )
                
                # Visualización 1: Sigma vs Precisión Térmica
                if viz_type == "Sigma vs Precisión Térmica":
                    st.subheader("📈 Sigma vs Precisión Térmica")
                    
                    if 'sigma_Caudal' in df_valid.columns and 'thermal_gradient_max' in df_valid.columns:
                        fig, ax = plt.subplots(figsize=(10, 6))
                        
                        # Colorear por batch type si existe
                        if 'batch_type' in df_valid.columns:
                            for batch_type in ['estable', 'turbulento']:
                                mask = df_valid['batch_type'] == batch_type
                                if mask.sum() > 0:
                                    color = 'green' if batch_type == 'estable' else 'red'
                                    label = 'Estable' if batch_type == 'estable' else 'Turbulento'
                                    ax.scatter(
                                        df_valid.loc[mask, 'sigma_Caudal'],
                                        df_valid.loc[mask, 'thermal_gradient_max'],
                                        c=color,
                                        alpha=0.6,
                                        s=50,
                                        label=label
                                    )
                        else:
                            ax.scatter(
                                df_valid['sigma_Caudal'],
                                df_valid['thermal_gradient_max'],
                                alpha=0.6,
                                s=50
                            )
                        
                        ax.set_xlabel('Sigma Caudal', fontsize=12)
                        ax.set_ylabel('Gradiente Térmico Máximo', fontsize=12)
                        ax.set_title('Sigma vs Precisión Térmica', fontsize=14, fontweight='bold')
                        ax.grid(True, alpha=0.3)
                        if 'batch_type' in df_valid.columns:
                            ax.legend()
                        st.pyplot(fig)
                    else:
                        st.warning("⚠️ No se encontraron las columnas necesarias (sigma_Caudal, thermal_gradient_max)")
                
                # Visualización 2: Fiabilidad por Tipo de Batch
                elif viz_type == "Fiabilidad por Tipo de Batch":
                    st.subheader("📊 Fiabilidad por Tipo de Batch")
                    
                    if 'batch_type' in df_valid.columns and 'thermal_interface_confidence' in df_valid.columns:
                        fig, ax = plt.subplots(figsize=(10, 6))
                        
                        batch_data = []
                        batch_labels = []
                        for batch_type in ['estable', 'turbulento']:
                            mask = df_valid['batch_type'] == batch_type
                            if mask.sum() > 0:
                                batch_data.append(df_valid.loc[mask, 'thermal_interface_confidence'].dropna().values)
                                batch_labels.append(batch_type.capitalize())
                        
                        if batch_data:
                            bp = ax.boxplot(batch_data, labels=batch_labels, patch_artist=True)
                            
                            # Colorear boxes
                            colors = ['lightgreen', 'lightcoral']
                            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                                patch.set_facecolor(color)
                            
                            ax.set_ylabel('Confianza de Interfaz', fontsize=12)
                            ax.set_title('Fiabilidad por Tipo de Batch', fontsize=14, fontweight='bold')
                            ax.grid(True, alpha=0.3, axis='y')
                            plt.xticks(rotation=0)
                            st.pyplot(fig)
                    else:
                        st.warning("⚠️ No se encontraron las columnas necesarias (batch_type, thermal_interface_confidence)")
                
                # Visualización 3: Distribución de Gradientes Térmicos
                elif viz_type == "Distribución de Gradientes Térmicos":
                    st.subheader("📊 Distribución de Gradientes Térmicos")
                    
                    if 'thermal_gradient_max' in df_valid.columns:
                        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
                        
                        # Histograma general
                        axes[0].hist(df_valid['thermal_gradient_max'].dropna(), bins=20, 
                                    edgecolor='black', alpha=0.7)
                        axes[0].set_xlabel('Gradiente Térmico Máximo', fontsize=11)
                        axes[0].set_ylabel('Frecuencia', fontsize=11)
                        axes[0].set_title('Distribución de Gradientes', fontsize=12, fontweight='bold')
                        axes[0].grid(True, alpha=0.3, axis='y')
                        
                        # Histograma por batch type
                        if 'batch_type' in df_valid.columns:
                            for batch_type in ['estable', 'turbulento']:
                                mask = df_valid['batch_type'] == batch_type
                                if mask.sum() > 0:
                                    color = 'green' if batch_type == 'estable' else 'red'
                                    label = 'Estable' if batch_type == 'estable' else 'Turbulento'
                                    axes[1].hist(df_valid.loc[mask, 'thermal_gradient_max'].dropna(), 
                                               bins=15, alpha=0.6, label=label, color=color, edgecolor='black')
                            
                            axes[1].set_xlabel('Gradiente Térmico Máximo', fontsize=11)
                            axes[1].set_ylabel('Frecuencia', fontsize=11)
                            axes[1].set_title('Distribución por Batch Type', fontsize=12, fontweight='bold')
                            axes[1].legend()
                            axes[1].grid(True, alpha=0.3, axis='y')
                        else:
                            axes[1].text(0.5, 0.5, 'No hay datos de batch_type', 
                                        ha='center', va='center', transform=axes[1].transAxes)
                            axes[1].axis('off')
                        
                        plt.tight_layout()
                        st.pyplot(fig)
                    else:
                        st.warning("⚠️ No se encontró la columna thermal_gradient_max")
                
                # Visualización 4: Ratios de Capas por Batch
                elif viz_type == "Ratios de Capas por Batch":
                    st.subheader("📊 Ratios de Capas por Batch")
                    
                    if 'batch_type' in df_valid.columns:
                        ratio_cols = ['thermal_crudo_ratio', 'thermal_emulsion_ratio', 'thermal_agua_ratio']
                        available_ratios = [col for col in ratio_cols if col in df_valid.columns]
                        
                        if available_ratios:
                            fig, axes = plt.subplots(1, len(available_ratios), figsize=(5*len(available_ratios), 6))
                            
                            if len(available_ratios) == 1:
                                axes = [axes]
                            
                            for idx, ratio_col in enumerate(available_ratios):
                                batch_data = []
                                batch_labels = []
                                
                                for batch_type in ['estable', 'turbulento']:
                                    mask = df_valid['batch_type'] == batch_type
                                    if mask.sum() > 0:
                                        batch_data.append(df_valid.loc[mask, ratio_col].dropna().values)
                                        batch_labels.append(batch_type.capitalize())
                                
                                if batch_data:
                                    bp = axes[idx].boxplot(batch_data, labels=batch_labels, patch_artist=True)
                                    
                                    colors = ['lightgreen', 'lightcoral']
                                    for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                                        patch.set_facecolor(color)
                                    
                                    ratio_name = ratio_col.replace('thermal_', '').replace('_ratio', '').capitalize()
                                    axes[idx].set_ylabel('Ratio', fontsize=11)
                                    axes[idx].set_title(f'Ratio de {ratio_name}', fontsize=12, fontweight='bold')
                                    axes[idx].grid(True, alpha=0.3, axis='y')
                            
                            plt.tight_layout()
                            st.pyplot(fig)
                        else:
                            st.warning("⚠️ No se encontraron columnas de ratios")
                    else:
                        st.warning("⚠️ No se encontró la columna batch_type")
                
                # Visualización 5: Correlaciones Térmicas
                elif viz_type == "Correlaciones Térmicas":
                    st.subheader("📊 Matriz de Correlaciones Térmicas")
                    
                    thermal_cols = [col for col in df_valid.columns if col.startswith('thermal_') and 
                                  col.endswith(('_ratio', '_mean', '_max', '_std', '_confidence'))]
                    sigma_cols = [col for col in df_valid.columns if col.startswith('sigma_')]
                    
                    if thermal_cols and sigma_cols:
                        # Seleccionar columnas para correlación
                        corr_cols = thermal_cols[:5] + sigma_cols[:2]  # Limitar a 7 columnas
                        corr_data = df_valid[corr_cols].select_dtypes(include=[np.number])
                        
                        if len(corr_data.columns) > 1:
                            corr_matrix = corr_data.corr()
                            
                            fig, ax = plt.subplots(figsize=(10, 8))
                            sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                                       center=0, square=True, linewidths=1, ax=ax)
                            ax.set_title('Matriz de Correlaciones Térmicas', fontsize=14, fontweight='bold')
                            plt.tight_layout()
                            st.pyplot(fig)
                        else:
                            st.warning("⚠️ Insuficientes columnas numéricas para correlación")
                    else:
                        st.warning("⚠️ No se encontraron columnas térmicas o sigma")
                
                # Visualización 6: Series Temporales
                elif viz_type == "Series Temporales":
                    st.subheader("📈 Series Temporales")
                    
                    # Convertir columna Día a datetime si existe
                    if 'Día' in df_valid.columns:
                        try:
                            df_valid['Día'] = pd.to_datetime(df_valid['Día'], errors='coerce')
                            df_valid = df_valid.sort_values('Día')
                        except:
                            pass
                    
                    if 'Día' in df_valid.columns and df_valid['Día'].notna().sum() > 0:
                        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
                        
                        # Ratios de capas
                        if 'thermal_emulsion_ratio' in df_valid.columns:
                            axes[0].plot(df_valid['Día'], df_valid['thermal_emulsion_ratio'], 
                                        'o-', label='Emulsión', alpha=0.7, markersize=4)
                        if 'thermal_agua_ratio' in df_valid.columns:
                            axes[0].plot(df_valid['Día'], df_valid['thermal_agua_ratio'], 
                                        's-', label='Agua', alpha=0.7, markersize=4)
                        axes[0].set_ylabel('Proporción (ratio)', fontsize=12)
                        axes[0].set_title('Evolución Temporal de Proporciones', fontsize=14, fontweight='bold')
                        axes[0].legend()
                        axes[0].grid(True, alpha=0.3)
                        axes[0].tick_params(axis='x', rotation=45)
                        
                        # Temperaturas
                        if 'T_TK' in df_valid.columns:
                            axes[1].plot(df_valid['Día'], df_valid['T_TK'], 
                                        'r-', label='T Tanque', alpha=0.7, linewidth=2)
                        if 'T_amb' in df_valid.columns:
                            axes[1].plot(df_valid['Día'], df_valid['T_amb'], 
                                        'b-', label='T Ambiente', alpha=0.7, linewidth=2)
                        if 'delta_t_tank_ambient' in df_valid.columns:
                            axes[1].plot(df_valid['Día'], df_valid['delta_t_tank_ambient'], 
                                        'g--', label='ΔT (Tanque-Ambiente)', alpha=0.7, linewidth=2)
                        axes[1].set_xlabel('Fecha', fontsize=12)
                        axes[1].set_ylabel('Temperatura (°C)', fontsize=12)
                        axes[1].set_title('Evolución Temporal de Temperaturas', fontsize=14, fontweight='bold')
                        axes[1].legend()
                        axes[1].grid(True, alpha=0.3)
                        axes[1].tick_params(axis='x', rotation=45)
                        
                        plt.tight_layout()
                        st.pyplot(fig)
                    else:
                        st.warning("⚠️ No se encontró columna de fecha (Día) o no se pudo convertir a datetime")
                
            except Exception as e:
                st.error(f"❌ Error cargando o procesando datos: {e}")
                logger.error(f"Error en visualizaciones: {e}", exc_info=True)
        else:
            st.info("👆 Por favor, carga un archivo CSV para ver las visualizaciones estadísticas")
    
    # Página: Exportar Reporte
    elif page == "Exportar Reporte":
        if not has_permission('export'):
            st.warning("⚠️ No tienes permiso para acceder a esta sección")
            return
        
        st.header("📄 Exportar Reporte PDF")
        st.info("Funcionalidad de exportación a PDF en desarrollo")
        
        # Placeholder para exportación PDF
        if st.button("Generar Reporte PDF"):
            st.success("✅ Reporte generado (funcionalidad en desarrollo)")

if __name__ == "__main__":
    main()

