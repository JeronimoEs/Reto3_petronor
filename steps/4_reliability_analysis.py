"""
Módulo de Análisis de Fiabilidad Térmica - Thermal Reliability Agent

Este módulo implementa el análisis estadístico para validar la hipótesis de fiabilidad térmica:
"Las imágenes térmicas capturadas durante períodos de menor variabilidad operacional 
(sigma baja en caudal y nivel) proporcionan mediciones más fiables para detectar 
interfaces entre capas de crudo, emulsión y agua."

FUNCIONALIDADES:
- Cálculo de sigma (variabilidad móvil) en caudal y nivel
- Clasificación de períodos en batch estable vs turbulento
- Correlación entre gradientes térmicos y sigma
- Análisis ANOVA para validación estadística
- Generación de reportes comparativos

AUTOR: Thermal Reliability Agent System
FECHA: 2025
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import pearsonr, spearmanr, f_oneway
from typing import Dict, Tuple, Optional
import logging
from pathlib import Path
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReliabilityAnalyzer:
    """
    Analizador de fiabilidad térmica basado en variabilidad operacional.
    
    Valida la hipótesis de que menor variabilidad operacional (sigma bajo)
    se correlaciona con mayor fiabilidad en detección de interfaces térmicas.
    
    Attributes:
        window (int): Ventana móvil para cálculo de sigma (default: 5).
        sigma_threshold (float): Umbral para clasificar batches (default: None, auto).
        correlation_method (str): Método de correlación ('pearson' o 'spearman').
    
    Example:
        >>> analyzer = ReliabilityAnalyzer(window=5)
        >>> results = analyzer.analyze_reliability(df)
        >>> print(results['hypothesis_validated'])
    """
    
    def __init__(self, window: int = 5, sigma_threshold: Optional[float] = None,
                 correlation_method: str = 'pearson'):
        """
        Inicializa el analizador de fiabilidad.
        
        Args:
            window (int): Ventana móvil para cálculo de desviación estándar.
            sigma_threshold (float, optional): Umbral para clasificar batches.
                Si None, se calcula automáticamente como percentil 50.
            correlation_method (str): Método de correlación ('pearson' o 'spearman').
        """
        self.window = window
        self.sigma_threshold = sigma_threshold
        self.correlation_method = correlation_method
        logger.info(f"ReliabilityAnalyzer inicializado: window={window}, method={correlation_method}")
    
    def compute_sigma(self, df: pd.DataFrame, columns: list = ['Caudal', 'Nivel TK %']) -> pd.DataFrame:
        """
        Calcula desviaciones estándar móviles (sigma) para columnas especificadas.
        
        Args:
            df (pd.DataFrame): DataFrame con datos históricos.
            columns (list): Lista de columnas para calcular sigma.
        
        Returns:
            pd.DataFrame: DataFrame con columnas adicionales 'sigma_{col}'.
        
        Example:
            >>> df_with_sigma = analyzer.compute_sigma(df, ['Caudal', 'Nivel TK %'])
            >>> print(df_with_sigma[['sigma_Caudal', 'sigma_Nivel TK %']].head())
        """
        logger.info(f"Calculando sigma móvil (window={self.window}) para: {columns}")
        
        df = df.copy()
        
        # Ordenar por fecha si existe
        if 'Día' in df.columns:
            df = df.sort_values('Día').reset_index(drop=True)
        
        for col in columns:
            if col not in df.columns:
                logger.warning(f"Columna '{col}' no encontrada, omitiendo")
                continue
            
            sigma_col = f'sigma_{col}'
            
            # Calcular desviación estándar móvil
            df[sigma_col] = df[col].rolling(
                window=self.window,
                min_periods=1,
                center=True
            ).std()
            
            # Rellenar NaN con el primer valor válido
            df[sigma_col] = df[sigma_col].bfill().ffill()
            
            logger.debug(f"Sigma calculado para {col}: mean={df[sigma_col].mean():.3f}, std={df[sigma_col].std():.3f}")
        
        return df
    
    def classify_batches(self, df: pd.DataFrame, 
                        sigma_columns: list = ['sigma_Caudal', 'sigma_Nivel TK %']) -> pd.DataFrame:
        """
        Clasifica períodos en batch estable (sigma bajo) o batch turbulento (sigma alto).
        
        Args:
            df (pd.DataFrame): DataFrame con columnas sigma calculadas.
            sigma_columns (list): Columnas de sigma para clasificar.
        
        Returns:
            pd.DataFrame: DataFrame con columna 'batch_type' ('estable' o 'turbulento').
        
        Example:
            >>> df_classified = analyzer.classify_batches(df)
            >>> print(df_classified['batch_type'].value_counts())
        """
        logger.info("Clasificando batches según variabilidad operacional")
        
        df = df.copy()
        
        # Filtrar columnas existentes
        valid_sigma_cols = [col for col in sigma_columns if col in df.columns]
        
        if not valid_sigma_cols:
            logger.error("No se encontraron columnas sigma válidas")
            df['batch_type'] = 'desconocido'
            return df
        
        # Calcular sigma combinado (promedio de sigmas normalizados)
        sigma_values = df[valid_sigma_cols].values
        
        # Normalizar cada columna sigma
        sigma_normalized = np.zeros_like(sigma_values)
        for i, col in enumerate(valid_sigma_cols):
            col_values = df[col].values
            if col_values.std() > 0:
                sigma_normalized[:, i] = (col_values - col_values.mean()) / col_values.std()
            else:
                sigma_normalized[:, i] = 0
        
        # Sigma combinado (promedio de sigmas normalizados)
        sigma_combined = np.mean(sigma_normalized, axis=1)
        df['sigma_combined'] = sigma_combined
        
        # Determinar umbral si no está definido
        if self.sigma_threshold is None:
            threshold = np.median(sigma_combined)
            logger.info(f"Umbral automático calculado: {threshold:.3f} (mediana)")
        else:
            threshold = self.sigma_threshold
            logger.info(f"Umbral manual: {threshold:.3f}")
        
        # Clasificar
        df['batch_type'] = df['sigma_combined'].apply(
            lambda x: 'estable' if x <= threshold else 'turbulento'
        )
        
        # Estadísticas
        counts = df['batch_type'].value_counts()
        logger.info(f"Batches clasificados: {dict(counts)}")
        
        return df
    
    def correlate_reliability(self, df: pd.DataFrame) -> Dict:
        """
        Calcula correlaciones entre precisión térmica (gradientes) y sigma.
        
        Args:
            df (pd.DataFrame): DataFrame con datos térmicos y sigma.
        
        Returns:
            dict: Diccionario con correlaciones y significancia estadística.
        
        Example:
            >>> correlations = analyzer.correlate_reliability(df)
            >>> print(f"Correlación: {correlations['thermal_gradient_max']['sigma_Caudal']}")
        """
        logger.info("Calculando correlaciones entre fiabilidad térmica y sigma")
        
        # Filtrar datos válidos
        df_valid = df[
            (df['status'] == 'success') & 
            (df['batch_type'].isin(['estable', 'turbulento']))
        ].copy()
        
        if len(df_valid) < 10:
            logger.warning("Insuficientes datos para correlación (mínimo 10)")
            return {}
        
        # Variables térmicas a correlacionar
        thermal_vars = [
            'thermal_gradient_max',
            'thermal_gradient_std',
            'thermal_interface_confidence',
            'thermal_emulsion_ratio',
            'thermal_agua_ratio'
        ]
        
        # Variables sigma
        sigma_vars = [col for col in df_valid.columns if col.startswith('sigma_')]
        
        correlations = {}
        
        for thermal_var in thermal_vars:
            if thermal_var not in df_valid.columns:
                continue
            
            correlations[thermal_var] = {}
            
            for sigma_var in sigma_vars:
                # Filtrar valores válidos
                mask = df_valid[[thermal_var, sigma_var]].notna().all(axis=1)
                
                if mask.sum() < 3:
                    continue
                
                x = df_valid.loc[mask, sigma_var].values
                y = df_valid.loc[mask, thermal_var].values
                
                try:
                    if self.correlation_method == 'pearson':
                        corr, p_value = pearsonr(x, y)
                    else:
                        corr, p_value = spearmanr(x, y)
                    
                    correlations[thermal_var][sigma_var] = {
                        'correlation': float(corr),
                        'p_value': float(p_value),
                        'significant': p_value < 0.1,
                        'n_samples': int(mask.sum())
                    }
                    
                    logger.debug(
                        f"{thermal_var} vs {sigma_var}: "
                        f"r={corr:.3f}, p={p_value:.4f}, sig={p_value < 0.1}"
                    )
                except Exception as e:
                    logger.warning(f"Error calculando correlación {thermal_var} vs {sigma_var}: {e}")
                    continue
        
        logger.info(f"Correlaciones calculadas: {len(correlations)} variables térmicas")
        
        return correlations
    
    def validate_hypothesis_anova(self, df: pd.DataFrame) -> Dict:
        """
        Valida la hipótesis usando ANOVA comparando batches estables vs turbulentos.
        
        Args:
            df (pd.DataFrame): DataFrame con datos clasificados.
        
        Returns:
            dict: Resultados de ANOVA con F-statistic, p-value y conclusión.
        
        Example:
            >>> anova_results = analyzer.validate_hypothesis_anova(df)
            >>> print(f"Hipótesis validada: {anova_results['hypothesis_validated']}")
        """
        logger.info("Validando hipótesis con ANOVA")
        
        df_valid = df[
            (df['status'] == 'success') & 
            (df['batch_type'].isin(['estable', 'turbulento']))
        ].copy()
        
        if len(df_valid) < 10:
            logger.warning("Insuficientes datos para ANOVA")
            return {'hypothesis_validated': False, 'error': 'insufficient_data'}
        
        # Variables a comparar
        comparison_vars = [
            'thermal_gradient_max',
            'thermal_interface_confidence',
            'thermal_emulsion_ratio',
            'thermal_agua_ratio'
        ]
        
        anova_results = {}
        
        for var in comparison_vars:
            if var not in df_valid.columns:
                continue
            
            # Separar por batch type
            stable = df_valid[df_valid['batch_type'] == 'estable'][var].dropna()
            turbulent = df_valid[df_valid['batch_type'] == 'turbulento'][var].dropna()
            
            if len(stable) < 3 or len(turbulent) < 3:
                logger.warning(f"Insuficientes datos para ANOVA en {var}")
                continue
            
            try:
                # ANOVA
                f_stat, p_value = f_oneway(stable, turbulent)
                
                # Estadísticas descriptivas
                stable_mean = stable.mean()
                turbulent_mean = turbulent.mean()
                stable_std = stable.std()
                turbulent_std = turbulent.std()
                
                anova_results[var] = {
                    'f_statistic': float(f_stat),
                    'p_value': float(p_value),
                    'significant': p_value < 0.1,
                    'stable_mean': float(stable_mean),
                    'stable_std': float(stable_std),
                    'turbulent_mean': float(turbulent_mean),
                    'turbulent_std': float(turbulent_std),
                    'n_stable': int(len(stable)),
                    'n_turbulent': int(len(turbulent)),
                    'effect_size': float((stable_mean - turbulent_mean) / np.sqrt(
                        (stable_std**2 + turbulent_std**2) / 2
                    )) if np.sqrt((stable_std**2 + turbulent_std**2) / 2) > 0 else 0
                }
                
                logger.info(
                    f"{var}: F={f_stat:.3f}, p={p_value:.4f}, "
                    f"estable={stable_mean:.3f}±{stable_std:.3f}, "
                    f"turbulento={turbulent_mean:.3f}±{turbulent_std:.3f}"
                )
            except Exception as e:
                logger.error(f"Error en ANOVA para {var}: {e}")
                continue
        
        # Conclusión general
        significant_vars = [v for v, r in anova_results.items() if r.get('significant', False)]
        hypothesis_validated = len(significant_vars) > 0
        
        result = {
            'anova_results': anova_results,
            'hypothesis_validated': hypothesis_validated,
            'n_significant_vars': len(significant_vars),
            'significant_vars': significant_vars,
            'conclusion': (
                f"La hipótesis se {'VALIDA' if hypothesis_validated else 'NO VALIDA'} "
                f"con {len(significant_vars)} variables significativas (p < 0.1)"
            )
        }
        
        logger.info(f"Validación de hipótesis: {result['conclusion']}")
        
        return result
    
    def generate_comparative_report(self, df: pd.DataFrame, 
                                   correlations: Dict, anova_results: Dict) -> pd.DataFrame:
        """
        Genera reporte comparativo entre batch estable y turbulento.
        
        Args:
            df (pd.DataFrame): DataFrame con datos clasificados.
            correlations (dict): Resultados de correlaciones.
            anova_results (dict): Resultados de ANOVA.
        
        Returns:
            pd.DataFrame: Tabla comparativa con métricas.
        
        Example:
            >>> report = analyzer.generate_comparative_report(df, corr, anova)
            >>> print(report.to_string())
        """
        logger.info("Generando reporte comparativo")
        
        df_valid = df[
            (df['status'] == 'success') & 
            (df['batch_type'].isin(['estable', 'turbulento']))
        ].copy()
        
        if len(df_valid) == 0:
            logger.warning("No hay datos válidos para reporte")
            return pd.DataFrame()
        
        # Variables a comparar
        metrics = [
            'thermal_gradient_max',
            'thermal_gradient_std',
            'thermal_interface_confidence',
            'thermal_emulsion_ratio',
            'thermal_agua_ratio',
            'thermal_crudo_ratio'
        ]
        
        report_data = []
        
        for metric in metrics:
            if metric not in df_valid.columns:
                continue
            
            stable = df_valid[df_valid['batch_type'] == 'estable'][metric].dropna()
            turbulent = df_valid[df_valid['batch_type'] == 'turbulento'][metric].dropna()
            
            if len(stable) == 0 or len(turbulent) == 0:
                continue
            
            # Obtener p-value de ANOVA si existe
            p_value = None
            if 'anova_results' in anova_results and metric in anova_results['anova_results']:
                p_value = anova_results['anova_results'][metric].get('p_value')
            
            # Obtener correlación con sigma si existe (solo valores positivos)
            corr_sigma = None
            if metric in correlations:
                sigma_corrs = correlations[metric]
                # Buscar correlación con sigma_Caudal o sigma_combined
                for sigma_key in ['sigma_Caudal', 'sigma_combined', 'sigma_Nivel TK %']:
                    if sigma_key in sigma_corrs:
                        corr_value = sigma_corrs[sigma_key].get('correlation')
                        # Solo incluir si la correlación es positiva
                        if corr_value is not None and corr_value >= 0:
                            corr_sigma = corr_value
                            break
            
            report_data.append({
                'metric': metric,
                'n_estable': len(stable),
                'n_turbulento': len(turbulent),
                'mean_estable': stable.mean(),
                'std_estable': stable.std(),
                'mean_turbulento': turbulent.mean(),
                'std_turbulento': turbulent.std(),
                'correlacion_sigma': corr_sigma,
                'p_value_anova': p_value,
                'significativo': p_value is not None and p_value < 0.1
            })
        
        report_df = pd.DataFrame(report_data)
        
        # Limpiar valores negativos de correlación (por si acaso)
        if 'correlacion_sigma' in report_df.columns:
            report_df.loc[report_df['correlacion_sigma'] < 0, 'correlacion_sigma'] = None
        
        logger.info(f"Reporte generado: {len(report_df)} métricas comparadas")
        
        return report_df
    
    def analyze_reliability(self, df: pd.DataFrame) -> Dict:
        """
        Ejecuta el análisis completo de fiabilidad térmica.
        
        Args:
            df (pd.DataFrame): DataFrame con datos históricos y features térmicas.
        
        Returns:
            dict: Diccionario con todos los resultados del análisis.
        
        Example:
            >>> results = analyzer.analyze_reliability(df)
            >>> print(results['hypothesis_validated'])
            >>> print(results['comparative_report'])
        """
        logger.info("="*80)
        logger.info("INICIANDO ANÁLISIS DE FIABILIDAD TÉRMICA")
        logger.info("="*80)
        
        # 1. Calcular sigma
        df = self.compute_sigma(df)
        
        # 2. Clasificar batches
        df = self.classify_batches(df)
        
        # 3. Correlaciones
        correlations = self.correlate_reliability(df)
        
        # 4. Validación ANOVA
        anova_results = self.validate_hypothesis_anova(df)
        
        # 5. Reporte comparativo
        comparative_report = self.generate_comparative_report(df, correlations, anova_results)
        
        # Resumen
        results = {
            'dataframe': df,
            'correlations': correlations,
            'anova_results': anova_results,
            'comparative_report': comparative_report,
            'hypothesis_validated': anova_results.get('hypothesis_validated', False),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("="*80)
        logger.info("ANÁLISIS DE FIABILIDAD COMPLETADO")
        logger.info("="*80)
        
        return results


def load_data(path: str) -> pd.DataFrame:
    """
    Wrapper para cargar datos validando columnas requeridas.
    
    Args:
        path (str): Ruta al archivo CSV.
    
    Returns:
        pd.DataFrame: DataFrame con datos cargados y validados.
    
    Example:
        >>> df = load_data('resultados_completos.csv')
        >>> print(df.columns.tolist())
    """
    logger.info(f"Cargando datos desde: {path}")
    
    try:
        df = pd.read_csv(path, encoding='utf-8')
        
        # Validar columnas requeridas
        required_cols = ['Caudal', 'Nivel TK %']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Columnas faltantes: {missing_cols}")
        
        # Validar columnas térmicas
        thermal_cols = [col for col in df.columns if col.startswith('thermal_')]
        logger.info(f"Columnas térmicas encontradas: {len(thermal_cols)}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        raise

