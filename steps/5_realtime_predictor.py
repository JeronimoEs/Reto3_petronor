"""
Pipeline de Predicción en Tiempo Real - Thermal Reliability Agent

Este módulo procesa nuevas imágenes térmicas y genera scores de fiabilidad
en tiempo real (< 5 segundos por imagen).

FUNCIONALIDADES:
- Procesamiento rápido de imágenes térmicas (640x480 px)
- Segmentación por rangos térmicos
- Cálculo de gradientes térmicos verticales
- Identificación de interfaces (agua/emulsión/crudo)
- Cálculo de ratios de capa (%)
- Evaluación de fiabilidad mediante correlación con patrones históricos
- Score de fiabilidad (0-100)

AUTOR: Thermal Reliability Agent System
FECHA: 2025
"""

import os
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import logging
from typing import Dict, Optional, Tuple
import time
import sys
import importlib.util

# Configurar logging primero
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar ThermalAnalyzer usando importlib (porque el módulo empieza con número)
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    spec = importlib.util.spec_from_file_location(
        "image_proccessing",
        BASE_DIR / "steps" / "2_image_proccessing.py"
    )
    image_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(image_module)
    ThermalAnalyzer = image_module.ThermalAnalyzer
    logger.info("ThermalAnalyzer cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando ThermalAnalyzer: {e}")
    ThermalAnalyzer = None


class RealtimeThermalPredictor:
    """
    Predictor en tiempo real para imágenes térmicas.
    
    Procesa nuevas imágenes y genera scores de fiabilidad basados en
    patrones históricos de batch estable.
    
    Attributes:
        analyzer (ThermalAnalyzer): Analizador térmico base.
        reference_profiles (dict): Perfiles de referencia de batch estable.
        processing_time_limit (float): Límite de tiempo de procesamiento (segundos).
    
    Example:
        >>> predictor = RealtimeThermalPredictor(reference_data=df)
        >>> result = predictor.predict_new_image('tanque_20250101_120000.jpg')
        >>> print(f"Score de fiabilidad: {result['reliability_score']}")
    """
    
    def __init__(self, reference_data: Optional[pd.DataFrame] = None,
                 processing_time_limit: float = 5.0):
        """
        Inicializa el predictor en tiempo real.
        
        Args:
            reference_data (pd.DataFrame, optional): Datos históricos de referencia
                para calcular perfiles de batch estable.
            processing_time_limit (float): Límite máximo de tiempo de procesamiento.
        
        Raises:
            ImportError: Si ThermalAnalyzer no está disponible.
        """
        if ThermalAnalyzer is None:
            raise ImportError(
                "ThermalAnalyzer no está disponible. "
                "Verifica que el módulo steps/2_image_proccessing.py exista y no tenga errores."
            )
        
        self.analyzer = ThermalAnalyzer(img_height=480, img_width=640)
        self.processing_time_limit = processing_time_limit
        self.reference_profiles = {}
        
        if reference_data is not None:
            self._build_reference_profiles(reference_data)
        
        logger.info("RealtimeThermalPredictor inicializado")
    
    def _build_reference_profiles(self, df: pd.DataFrame):
        """
        Construye perfiles de referencia a partir de datos históricos de batch estable.
        
        Args:
            df (pd.DataFrame): DataFrame con datos históricos clasificados.
        """
        logger.info("Construyendo perfiles de referencia de batch estable")
        
        # Filtrar batch estable
        df_stable = df[
            (df['status'] == 'success') & 
            (df.get('batch_type', pd.Series()) == 'estable')
        ].copy()
        
        if len(df_stable) == 0:
            logger.warning("No hay datos de batch estable para referencia")
            return
        
        # Calcular perfiles promedio
        thermal_vars = [
            'thermal_gradient_max',
            'thermal_gradient_std',
            'thermal_emulsion_ratio',
            'thermal_agua_ratio',
            'thermal_crudo_ratio',
            'thermal_interface_confidence'
        ]
        
        for var in thermal_vars:
            if var in df_stable.columns:
                values = df_stable[var].dropna()
                if len(values) > 0:
                    self.reference_profiles[var] = {
                        'mean': float(values.mean()),
                        'std': float(values.std()),
                        'median': float(values.median()),
                        'q25': float(values.quantile(0.25)),
                        'q75': float(values.quantile(0.75))
                    }
        
        logger.info(f"Perfiles de referencia construidos: {len(self.reference_profiles)} variables")
    
    def extract_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """
        Extrae timestamp del nombre de archivo: tanque_YYYYMMDD_HHMMSS.jpg
        
        Args:
            filename (str): Nombre del archivo.
        
        Returns:
            datetime: Timestamp extraído o None si no se puede parsear.
        
        Example:
            >>> ts = predictor.extract_timestamp_from_filename('tanque_20250101_120000.jpg')
            >>> print(ts)
        """
        # Patrón: tanque_YYYYMMDD_HHMMSS.jpg
        pattern = r'tanque_(\d{8})_(\d{6})\.(jpg|jpeg|png)'
        match = re.search(pattern, filename, re.IGNORECASE)
        
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            
            try:
                timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                return timestamp
            except ValueError:
                logger.warning(f"No se pudo parsear timestamp de: {filename}")
                return None
        
        return None
    
    def process_image_fast(self, image_path: str) -> Dict:
        """
        Procesa imagen térmica de forma rápida (< 5 segundos).
        
        Args:
            image_path (str): Ruta a la imagen térmica.
        
        Returns:
            dict: Diccionario con features térmicas extraídas.
        
        Example:
            >>> features = predictor.process_image_fast('imagen.jpg')
            >>> print(features['thermal_gradient_max'])
        """
        start_time = time.time()
        
        logger.info(f"Procesando imagen: {os.path.basename(image_path)}")
        
        # Usar el analizador base
        features = self.analyzer.process_image(image_path)
        
        processing_time = time.time() - start_time
        
        if processing_time > self.processing_time_limit:
            logger.warning(
                f"Tiempo de procesamiento excedido: {processing_time:.2f}s > {self.processing_time_limit}s"
            )
        
        features['processing_time'] = processing_time
        features['image_path'] = image_path
        features['image_filename'] = os.path.basename(image_path)
        
        logger.info(f"Imagen procesada en {processing_time:.2f}s")
        
        return features
    
    def calculate_reliability_score(self, features: Dict) -> float:
        """
        Calcula score de fiabilidad (0-100) comparando con perfiles de referencia.
        
        Args:
            features (dict): Features térmicas extraídas de la imagen.
        
        Returns:
            float: Score de fiabilidad entre 0 y 100.
        
        Example:
            >>> score = predictor.calculate_reliability_score(features)
            >>> print(f"Fiabilidad: {score:.1f}%")
        """
        if not self.reference_profiles:
            logger.warning("No hay perfiles de referencia, retornando score por defecto")
            return 50.0  # Score neutro
        
        scores = []
        weights = []
        
        # Variables clave para fiabilidad
        key_vars = [
            ('thermal_gradient_max', 0.25),
            ('thermal_interface_confidence', 0.30),
            ('thermal_emulsion_ratio', 0.20),
            ('thermal_agua_ratio', 0.15),
            ('thermal_crudo_ratio', 0.10)
        ]
        
        for var, weight in key_vars:
            if var not in features or var not in self.reference_profiles:
                continue
            
            value = features[var]
            if pd.isna(value):
                continue
            
            ref = self.reference_profiles[var]
            ref_mean = ref['mean']
            ref_std = ref['std']
            
            if ref_std == 0:
                # Si no hay variabilidad, comparar directamente
                score = 100.0 if abs(value - ref_mean) < 0.01 else 50.0
            else:
                # Calcular z-score y convertir a score (0-100)
                z_score = abs((value - ref_mean) / ref_std)
                
                # Score basado en distancia: más cerca = mayor score
                # Usar función exponencial para suavizar
                score = 100.0 * np.exp(-z_score / 2.0)
                score = max(0.0, min(100.0, score))  # Clamp entre 0-100
            
            scores.append(score)
            weights.append(weight)
        
        if not scores:
            logger.warning("No se pudieron calcular scores parciales")
            return 50.0
        
        # Score ponderado
        reliability_score = np.average(scores, weights=weights)
        
        logger.debug(f"Score de fiabilidad calculado: {reliability_score:.2f}")
        
        return float(reliability_score)
    
    def classify_reliability_category(self, score: float) -> str:
        """
        Clasifica el score de fiabilidad en categoría.
        
        Args:
            score (float): Score de fiabilidad (0-100).
        
        Returns:
            str: Categoría ('alta', 'media', 'baja').
        
        Example:
            >>> category = predictor.classify_reliability_category(85.0)
            >>> print(category)  # 'alta'
        """
        if score >= 80:
            return 'alta'
        elif score >= 60:
            return 'media'
        else:
            return 'baja'
    
    def predict_new_image(self, image_path: str, 
                         extract_timestamp: bool = True) -> Dict:
        """
        Procesa nueva imagen y genera predicción completa con score de fiabilidad.
        
        Args:
            image_path (str): Ruta a la imagen térmica.
            extract_timestamp (bool): Si True, intenta extraer timestamp del nombre.
        
        Returns:
            dict: Diccionario completo con features, score y metadatos.
        
        Example:
            >>> result = predictor.predict_new_image('tanque_20250101_120000.jpg')
            >>> print(f"Score: {result['reliability_score']}, "
            >>>       f"Categoría: {result['reliability_category']}")
        """
        start_time = time.time()
        
        logger.info(f"Prediciendo fiabilidad para: {os.path.basename(image_path)}")
        
        # Validar archivo
        if not os.path.exists(image_path):
            logger.error(f"Imagen no encontrada: {image_path}")
            return {
                'error': 'image_not_found',
                'reliability_score': 0.0,
                'reliability_category': 'baja'
            }
        
        # Extraer timestamp si es posible
        timestamp = None
        if extract_timestamp:
            filename = os.path.basename(image_path)
            timestamp = self.extract_timestamp_from_filename(filename)
        
        # Procesar imagen
        features = self.process_image_fast(image_path)
        
        if features.get('status') != 'success':
            logger.warning(f"Procesamiento falló: {features.get('status')}")
            return {
                **features,
                'reliability_score': 0.0,
                'reliability_category': 'baja',
                'timestamp': timestamp.isoformat() if timestamp else None
            }
        
        # Calcular score de fiabilidad
        reliability_score = self.calculate_reliability_score(features)
        reliability_category = self.classify_reliability_category(reliability_score)
        
        # Resultado completo
        result = {
            **features,
            'reliability_score': reliability_score,
            'reliability_category': reliability_category,
            'timestamp': timestamp.isoformat() if timestamp else None,
            'total_processing_time': time.time() - start_time
        }
        
        logger.info(
            f"Predicción completada: score={reliability_score:.2f}, "
            f"categoría={reliability_category}, tiempo={result['total_processing_time']:.2f}s"
        )
        
        return result
    
    def batch_predict(self, image_paths: list) -> pd.DataFrame:
        """
        Procesa múltiples imágenes en batch.
        
        Args:
            image_paths (list): Lista de rutas a imágenes.
        
        Returns:
            pd.DataFrame: DataFrame con resultados de todas las predicciones.
        
        Example:
            >>> results_df = predictor.batch_predict(['img1.jpg', 'img2.jpg'])
            >>> print(results_df[['image_filename', 'reliability_score']])
        """
        logger.info(f"Procesando batch de {len(image_paths)} imágenes")
        
        results = []
        
        for img_path in image_paths:
            try:
                result = self.predict_new_image(img_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error procesando {img_path}: {e}")
                results.append({
                    'image_path': img_path,
                    'error': str(e),
                    'reliability_score': 0.0
                })
        
        df_results = pd.DataFrame(results)
        
        logger.info(f"Batch procesado: {len(df_results)} resultados")
        
        return df_results


def predict_new_image(image_path: str, reference_data: Optional[pd.DataFrame] = None) -> Dict:
    """
    Función wrapper para predecir fiabilidad de una nueva imagen.
    
    Args:
        image_path (str): Ruta a la imagen térmica.
        reference_data (pd.DataFrame, optional): Datos de referencia históricos.
    
    Returns:
        dict: Resultado de la predicción con score de fiabilidad.
    
    Example:
        >>> result = predict_new_image('tanque_20250101_120000.jpg', df_reference)
        >>> print(f"Score: {result['reliability_score']}")
    """
    predictor = RealtimeThermalPredictor(reference_data=reference_data)
    return predictor.predict_new_image(image_path)

