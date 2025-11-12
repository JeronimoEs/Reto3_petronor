"""
Módulo de Tracking MLOps - Thermal Reliability Agent

Sistema de logging y tracking para reproducibilidad y observabilidad.

FUNCIONALIDADES:
- Tracking con MLFlow
- Logging estructurado
- Versionado de datos e imágenes
- Métricas de performance
- Trazabilidad completa (input → output → modelo → timestamp)

AUTOR: Thermal Reliability Agent System
FECHA: 2025
"""

import os
import logging
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLFlow no disponible. Instalar con: pip install mlflow")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLFlowTracker:
    """
    Tracker para MLFlow con funcionalidades de versionado y tracking.
    
    Attributes:
        experiment_name (str): Nombre del experimento.
        tracking_uri (str): URI del servidor MLFlow.
        active_run (mlflow.ActiveRun): Run activo actual.
    
    Example:
        >>> tracker = MLFlowTracker(experiment_name="thermal_reliability")
        >>> tracker.start_run()
        >>> tracker.log_metrics({'reliability_score': 85.5})
        >>> tracker.end_run()
    """
    
    def __init__(self, experiment_name: str = "thermal_reliability",
                 tracking_uri: Optional[str] = None):
        """
        Inicializa el tracker MLFlow.
        
        Args:
            experiment_name (str): Nombre del experimento.
            tracking_uri (str, optional): URI del servidor MLFlow.
                Si None, usa almacenamiento local.
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLFlow no disponible, usando logging básico")
            self.mlflow_available = False
            return
        
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri or "file:./mlruns"
        mlflow.set_tracking_uri(self.tracking_uri)
        
        # Crear o obtener experimento
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info(f"Experimento creado: {experiment_name} (ID: {experiment_id})")
            else:
                logger.info(f"Experimento existente: {experiment_name} (ID: {experiment.experiment_id})")
        except Exception as e:
            logger.error(f"Error configurando experimento: {e}")
        
        mlflow.set_experiment(experiment_name)
        self.mlflow_available = True
        self.active_run = None
    
    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict] = None):
        """
        Inicia un nuevo run de MLFlow.
        
        Args:
            run_name (str, optional): Nombre del run.
            tags (dict, optional): Tags adicionales.
        """
        if not self.mlflow_available:
            logger.info("MLFlow no disponible, iniciando run simulado")
            return
        
        try:
            self.active_run = mlflow.start_run(run_name=run_name)
            
            if tags:
                mlflow.set_tags(tags)
            
            logger.info(f"Run iniciado: {self.active_run.info.run_id}")
        except Exception as e:
            logger.error(f"Error iniciando run: {e}")
    
    def end_run(self):
        """Termina el run activo."""
        if not self.mlflow_available or self.active_run is None:
            return
        
        try:
            mlflow.end_run()
            logger.info("Run finalizado")
        except Exception as e:
            logger.error(f"Error finalizando run: {e}")
    
    def log_params(self, params: Dict[str, Any]):
        """
        Registra parámetros del modelo/experimento.
        
        Args:
            params (dict): Diccionario de parámetros.
        
        Example:
            >>> tracker.log_params({'window': 5, 'sigma_threshold': 0.5})
        """
        if not self.mlflow_available:
            logger.info(f"Parámetros (simulado): {params}")
            return
        
        try:
            mlflow.log_params(params)
            logger.debug(f"Parámetros registrados: {list(params.keys())}")
        except Exception as e:
            logger.error(f"Error registrando parámetros: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Registra métricas.
        
        Args:
            metrics (dict): Diccionario de métricas.
            step (int, optional): Paso/iteración.
        
        Example:
            >>> tracker.log_metrics({'reliability_score': 85.5, 'p_value': 0.03})
        """
        if not self.mlflow_available:
            logger.info(f"Métricas (simulado): {metrics}")
            return
        
        try:
            mlflow.log_metrics(metrics, step=step)
            logger.debug(f"Métricas registradas: {list(metrics.keys())}")
        except Exception as e:
            logger.error(f"Error registrando métricas: {e}")
    
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """
        Registra un artefacto (archivo).
        
        Args:
            local_path (str): Ruta local del archivo.
            artifact_path (str, optional): Ruta dentro del run.
        
        Example:
            >>> tracker.log_artifact('results.csv', 'outputs/results.csv')
        """
        if not self.mlflow_available:
            logger.info(f"Artefacto (simulado): {local_path}")
            return
        
        try:
            mlflow.log_artifact(local_path, artifact_path)
            logger.debug(f"Artefacto registrado: {local_path}")
        except Exception as e:
            logger.error(f"Error registrando artefacto: {e}")
    
    def log_model(self, model, artifact_path: str = "model"):
        """
        Registra un modelo.
        
        Args:
            model: Modelo a registrar.
            artifact_path (str): Ruta del modelo.
        """
        if not self.mlflow_available:
            logger.info(f"Modelo (simulado): {artifact_path}")
            return
        
        try:
            mlflow.sklearn.log_model(model, artifact_path)
            logger.info(f"Modelo registrado: {artifact_path}")
        except Exception as e:
            logger.error(f"Error registrando modelo: {e}")


class DataVersioning:
    """
    Sistema de versionado de datos e imágenes.
    
    Calcula hashes para trazabilidad y versionado.
    """
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calcula hash SHA-256 de un archivo.
        
        Args:
            file_path (str): Ruta al archivo.
        
        Returns:
            str: Hash hexadecimal del archivo.
        
        Example:
            >>> hash_val = DataVersioning.calculate_file_hash('data.csv')
            >>> print(hash_val)
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash de {file_path}: {e}")
            return ""
    
    @staticmethod
    def calculate_dataframe_hash(df: pd.DataFrame) -> str:
        """
        Calcula hash de un DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame a hashear.
        
        Returns:
            str: Hash hexadecimal del DataFrame.
        """
        try:
            # Convertir a string y hashear
            df_str = df.to_string()
            return hashlib.sha256(df_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash de DataFrame: {e}")
            return ""
    
    @staticmethod
    def create_version_metadata(file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Crea metadatos de versión para un archivo.
        
        Args:
            file_path (str): Ruta al archivo.
            metadata (dict, optional): Metadatos adicionales.
        
        Returns:
            dict: Diccionario con metadatos de versión.
        """
        file_hash = DataVersioning.calculate_file_hash(file_path)
        file_stat = os.stat(file_path)
        
        version_metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': file_stat.st_size,
            'file_hash': file_hash,
            'timestamp': datetime.now().isoformat(),
            'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }
        
        if metadata:
            version_metadata.update(metadata)
        
        return version_metadata


class StructuredLogger:
    """
    Logger estructurado para trazabilidad completa.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Inicializa el logger estructurado.
        
        Args:
            log_file (str, optional): Archivo de log (si None, solo consola).
        """
        self.log_file = log_file
        self.logger = logging.getLogger("structured")
        
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)
    
    def log_analysis(self, analysis_type: str, input_data: Dict, output_data: Dict,
                    processing_time: float, **kwargs):
        """
        Registra un análisis completo.
        
        Args:
            analysis_type (str): Tipo de análisis.
            input_data (dict): Datos de entrada.
            output_data (dict): Datos de salida.
            processing_time (float): Tiempo de procesamiento.
            **kwargs: Metadatos adicionales.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': analysis_type,
            'input': input_data,
            'output': output_data,
            'processing_time': processing_time,
            **kwargs
        }
        
        self.logger.info(f"ANALYSIS: {json.dumps(log_entry)}")
    
    def log_prediction(self, image_path: str, features: Dict, reliability_score: float,
                     processing_time: float, **kwargs):
        """
        Registra una predicción.
        
        Args:
            image_path (str): Ruta a la imagen.
            features (dict): Features extraídas.
            reliability_score (float): Score de fiabilidad.
            processing_time (float): Tiempo de procesamiento.
            **kwargs: Metadatos adicionales.
        """
        # Calcular hash de imagen
        image_hash = DataVersioning.calculate_file_hash(image_path) if os.path.exists(image_path) else None
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'prediction',
            'image_path': image_path,
            'image_hash': image_hash,
            'features': features,
            'reliability_score': reliability_score,
            'processing_time': processing_time,
            **kwargs
        }
        
        self.logger.info(f"PREDICTION: {json.dumps(log_entry)}")
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """
        Registra un error.
        
        Args:
            error_type (str): Tipo de error.
            error_message (str): Mensaje de error.
            context (dict, optional): Contexto adicional.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        
        self.logger.error(f"ERROR: {json.dumps(log_entry)}")


# Instancia global de logger estructurado
structured_logger = StructuredLogger()

