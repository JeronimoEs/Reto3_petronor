"""
Módulo de procesamiento de imágenes térmicas para análisis de tanques estratificados.

Este módulo contiene la clase ThermalAnalyzer que procesa imágenes infrarrojas
para detectar interfaces entre capas (crudo, emulsión, agua) y extraer métricas
térmicas relevantes.
"""

import os
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


class ThermalAnalyzer:
    """
    Procesador avanzado de imágenes térmicas de tanques estratificados.
    
    Detecta automáticamente interfaces entre capas (crudo, emulsión, agua),
    calcula espesores relativos y analiza gradientes térmicos.
    
    Attributes:
        img_height (int): Altura de la imagen procesada (default: 512).
        img_width (int): Ancho de la imagen procesada (default: 640).
        smoothing_sigma (float): Parámetro sigma para suavizado gaussiano (default: 3).
        normalize (bool): Si True, normaliza la imagen (default: True).
        TEMP_RANGES (dict): Rangos de temperatura calibrados por capa.
    
    Example:
        >>> analyzer = ThermalAnalyzer()
        >>> features = analyzer.process_image('./imagenes/Imagen1.jpg')
        >>> print(features['thermal_crudo_ratio'])
    """

    def __init__(self, img_height=512, img_width=640, smoothing_sigma=3, normalize=True):
        """
        Inicializa el analizador térmico.
        
        Args:
            img_height (int): Altura de la imagen procesada.
            img_width (int): Ancho de la imagen procesada.
            smoothing_sigma (float): Parámetro sigma para suavizado gaussiano del perfil térmico.
            normalize (bool): Si True, normaliza la imagen al rango [0, 255].
        """
        self.img_height = img_height
        self.img_width = img_width
        self.smoothing_sigma = smoothing_sigma
        self.normalize = normalize
        
        # Rango térmico calibrado a escala de pixel (0-255)
        # Mapeo: 0°C → 40, 60°C → 255
        self.TEMP_RANGES = {
            'aire':      (0, 70),      # Aire/atmósfera
            'agua':      (70, 130),    # Capa de agua
            'emulsion':  (130, 180),   # Capa de emulsión
            'crudo':     (180, 255)    # Capa de crudo
        }

    def process_image(self, img_path):
        """
        Procesa una imagen térmica y extrae features.
        
        Este es el método principal que orquesta todo el proceso:
        1. Carga la imagen (grayscale o RGB)
        2. Preprocesa (suavizado gaussiano, normalización)
        3. Detecta interfaces usando gradientes negativos
        4. Valida interfaces según rangos de temperatura
        5. Calcula espesores y métricas térmicas
        
        Args:
            img_path (str): Ruta a la imagen térmica.
        
        Returns:
            dict: Diccionario con features extraídas:
                - thermal_interface_top_px: Posición de la interfaz superior (px)
                - thermal_interface_bottom_px: Posición de la interfaz inferior (px)
                - thermal_interface_confidence: Confianza en la detección (0-1)
                - thermal_crudo_px: Espesor de crudo en píxeles
                - thermal_emulsion_px: Espesor de emulsión en píxeles
                - thermal_agua_px: Espesor de agua en píxeles
                - thermal_crudo_ratio: Ratio de crudo (0-1)
                - thermal_emulsion_ratio: Ratio de emulsión (0-1)
                - thermal_agua_ratio: Ratio de agua (0-1)
                - thermal_temp_crudo_mean: Temperatura media del crudo
                - thermal_temp_emulsion_mean: Temperatura media de la emulsión
                - thermal_temp_agua_mean: Temperatura media del agua
                - thermal_gradient_max: Gradiente máximo
                - thermal_gradient_std: Desviación estándar del gradiente
                - status: Estado del procesamiento
        """
        if not os.path.exists(img_path):
            return self._default_output("not_found")

        try:
            # Cargar y preprocesar imagen
            img = self._load_image(img_path)
            img = self._preprocess_image(img)
            
            # Calcular perfil térmico vertical (promedio horizontal por fila)
            temp_profile = np.mean(img, axis=1)
            temp_profile_smooth = gaussian_filter1d(temp_profile, sigma=self.smoothing_sigma)

            # Detectar posibles interfaces (donde la temperatura cae bruscamente)
            gradient = np.gradient(temp_profile_smooth)
            peaks_neg, props = find_peaks(
                -gradient, 
                prominence=np.std(gradient) * 0.4, 
                distance=15
            )

            if len(peaks_neg) < 2:
                return self._default_output("no_interfaces_detected")

            # Buscar interfaces válidas
            top, bottom, score = self._select_valid_interfaces(img, peaks_neg, props)

            # Calcular espesores
            layers = self._calculate_layers(img, top, bottom)

            # Extraer features completas
            features = self._extract_features(img, gradient, top, bottom, layers, score)

            return features

        except Exception as e:
            print(f"[ThermalAnalyzer] Error procesando {img_path}: {e}")
            return self._default_output("processing_error")

    def show_interfaces(self, img_path, save_path=None):
        """
        Visualiza la imagen con las interfaces detectadas.
        
        Opcional: Muestra o guarda una visualización de la imagen térmica
        con las interfaces detectadas marcadas como líneas horizontales.
        
        Args:
            img_path (str): Ruta a la imagen térmica.
            save_path (str, optional): Si se proporciona, guarda la imagen en lugar de mostrarla.
        
        Returns:
            None
        """
        try:
            import matplotlib.pyplot as plt
            
            # Procesar imagen
            features = self.process_image(img_path)
            
            if features.get('status') != 'success':
                print(f"No se pudieron detectar interfaces: {features.get('status')}")
                return
            
            # Cargar imagen original para visualización
            img = self._load_image(img_path)
            img_processed = self._preprocess_image(img)
            
            # Obtener posiciones de interfaces
            top = features['thermal_interface_top_px']
            bottom = features['thermal_interface_bottom_px']
            
            # Crear visualización
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            
            # Imagen original con interfaces
            axes[0].imshow(img_processed, cmap='hot', aspect='auto')
            axes[0].axhline(y=top, color='cyan', linewidth=2, label=f'Interfaz Superior (px={top})')
            axes[0].axhline(y=bottom, color='blue', linewidth=2, label=f'Interfaz Inferior (px={bottom})')
            axes[0].set_title('Imagen Térmica con Interfaces Detectadas')
            axes[0].set_xlabel('Ancho (px)')
            axes[0].set_ylabel('Altura (px)')
            axes[0].legend()
            axes[0].invert_yaxis()
            
            # Perfil térmico vertical
            temp_profile = np.mean(img_processed, axis=1)
            temp_profile_smooth = gaussian_filter1d(temp_profile, sigma=self.smoothing_sigma)
            y_coords = np.arange(len(temp_profile))
            
            axes[1].plot(temp_profile_smooth, y_coords, 'b-', linewidth=2, label='Perfil Suavizado')
            axes[1].axhline(y=top, color='cyan', linewidth=2, linestyle='--', label='Interfaz Superior')
            axes[1].axhline(y=bottom, color='blue', linewidth=2, linestyle='--', label='Interfaz Inferior')
            axes[1].set_xlabel('Temperatura (escala 0-255)')
            axes[1].set_ylabel('Altura (px)')
            axes[1].set_title('Perfil Térmico Vertical')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            axes[1].invert_yaxis()
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                print(f"Visualización guardada en: {save_path}")
            else:
                plt.show()
                
            plt.close()
            
        except ImportError:
            print("matplotlib no está instalado. Instala con: pip install matplotlib")
        except Exception as e:
            print(f"Error en visualización: {e}")

    # ---------------------------------------------------------
    # --------------- MÉTODOS PRIVADOS ------------------------
    # ---------------------------------------------------------

    def _load_image(self, path):
        """
        Carga una imagen y la convierte a escala de grises.
        
        Acepta imágenes en grayscale o RGB. Si es RGB, la convierte a grayscale.
        Redimensiona la imagen a las dimensiones especificadas.
        
        Args:
            path (str): Ruta a la imagen.
        
        Returns:
            np.ndarray: Imagen en escala de grises, redimensionada.
        """
        # Intentar cargar como grayscale primero
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        
        # Si falla, cargar como color y convertir
        if img is None:
            img = cv2.imread(path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if img is None:
            raise ValueError(f"No se pudo cargar la imagen: {path}")
        
        # Redimensionar
        img = cv2.resize(img, (self.img_width, self.img_height))
        
        return img

    def _preprocess_image(self, img):
        """
        Preprocesa la imagen: suavizado gaussiano y normalización.
        
        Aplica:
        1. Filtro gaussiano para reducir ruido
        2. Eliminación de bordes fríos (threshold)
        3. Normalización opcional al rango [0, 255]
        
        Args:
            img (np.ndarray): Imagen en escala de grises.
        
        Returns:
            np.ndarray: Imagen preprocesada.
        """
        # Suavizado gaussiano
        img = cv2.GaussianBlur(img, (3, 3), 0)
        img = np.clip(img, 0, 255).astype(np.uint8)
        
        # Eliminar fondo/bordes fríos (threshold)
        _, mask = cv2.threshold(img, 20, 255, cv2.THRESH_BINARY)
        img = cv2.bitwise_and(img, mask)

        # Normalización opcional
        if self.normalize:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

        return img

    def _select_valid_interfaces(self, img, peaks, props):
        """
        Evalúa combinaciones de interfaces y selecciona la más coherente.
        
        Prueba diferentes combinaciones de picos candidatos y selecciona
        la que mejor cumple con los rangos de temperatura esperados.
        
        Args:
            img (np.ndarray): Imagen preprocesada.
            peaks (np.ndarray): Array de picos candidatos.
            props (dict): Propiedades de los picos (prominencia, etc.).
        
        Returns:
            tuple: (top_interface, bottom_interface, confidence_score)
        """
        H = img.shape[0]
        best_score = -1
        best_pair = (H // 3, 2 * H // 3)  # Valores por defecto

        # Ordenar candidatos por prominencia (más prominentes primero)
        idx_sorted = np.argsort(props['prominences'])[::-1]
        top_peaks = peaks[idx_sorted[:min(6, len(peaks))]]

        # Probar todas las combinaciones de picos
        for i, t in enumerate(top_peaks):
            for b in top_peaks[i+1:]:
                if t >= b: 
                    continue  # La interfaz superior debe estar arriba
                
                # Obtener regiones y temperaturas medias
                regions = self._get_regions(img, t, b)
                temps = [np.mean(r) if r.size > 0 else 0 for r in regions]
                
                # Evaluar coherencia térmica
                score = self._score_temperature_sequence(*temps)

                if score > best_score:
                    best_score = score
                    best_pair = (t, b)

        return *best_pair, best_score

    def _get_regions(self, img, top, bottom):
        """
        Divide la imagen en 3 zonas según las interfaces detectadas.
        
        Args:
            img (np.ndarray): Imagen preprocesada.
            top (int): Posición de la interfaz superior (px).
            bottom (int): Posición de la interfaz inferior (px).
        
        Returns:
            tuple: (region_crudo, region_emulsion, region_agua)
        """
        return (
            img[:top, :],          # Crudo (parte superior)
            img[top:bottom, :],     # Emulsión (parte media)
            img[bottom:, :]         # Agua (parte inferior)
        )

    def _score_temperature_sequence(self, top, middle, bottom):
        """
        Evalúa la coherencia térmica entre capas.
        
        Valida que:
        1. Las temperaturas sigan el orden esperado: crudo > emulsión > agua
        2. Las temperaturas estén en los rangos esperados
        3. Los gradientes entre capas sean razonables
        
        Args:
            top (float): Temperatura media de la capa superior (crudo).
            middle (float): Temperatura media de la capa media (emulsión).
            bottom (float): Temperatura media de la capa inferior (agua).
        
        Returns:
            float: Score de coherencia (mayor es mejor).
        """
        # Validar orden térmico: crudo debe ser más caliente que emulsión, que debe ser más caliente que agua
        if not (top > middle > bottom):
            return -100  # Orden incorrecto

        score = 0
        
        # Validación por rango de temperatura
        score += self._check_range(top, 'crudo', weight=5)
        score += self._check_range(middle, 'emulsion', weight=5)
        score += self._check_range(bottom, 'agua', weight=5)
        
        # Bonus por gradientes razonables entre capas
        if (top - middle) > 10: 
            score += 3
        if (middle - bottom) > 10: 
            score += 3

        return score

    def _check_range(self, temp, layer, weight=5):
        """
        Verifica si una temperatura está en el rango esperado para una capa.
        
        Args:
            temp (float): Temperatura a verificar.
            layer (str): Nombre de la capa ('crudo', 'emulsion', 'agua').
            weight (int): Peso del score si está en rango.
        
        Returns:
            float: Score parcial (positivo si está en rango, negativo si no).
        """
        lo, hi = self.TEMP_RANGES[layer]
        
        if lo <= temp <= hi:
            return weight  # En rango óptimo
        elif temp > hi:
            return weight / 2  # Muy caliente pero aceptable
        else:
            return -weight / 2  # Fuera de rango

    def _calculate_layers(self, img, top, bottom):
        """
        Calcula espesores absolutos y relativos de cada capa.
        
        Args:
            img (np.ndarray): Imagen preprocesada.
            top (int): Posición de la interfaz superior (px).
            bottom (int): Posición de la interfaz inferior (px).
        
        Returns:
            dict: Diccionario con espesores en píxeles y ratios.
        """
        H = img.shape[0]
        
        return {
            'crudo_px': top,
            'emulsion_px': bottom - top,
            'agua_px': H - bottom,
            'crudo_ratio': top / H,
            'emulsion_ratio': (bottom - top) / H,
            'agua_ratio': (H - bottom) / H
        }

    def _extract_features(self, img, gradient, top, bottom, layers, score):
        """
        Extrae todas las features térmicas de la imagen.
        
        Args:
            img (np.ndarray): Imagen preprocesada.
            gradient (np.ndarray): Gradiente del perfil térmico.
            top (int): Posición de la interfaz superior.
            bottom (int): Posición de la interfaz inferior.
            layers (dict): Diccionario con espesores calculados.
            score (float): Score de confianza de las interfaces.
        
        Returns:
            dict: Diccionario completo con todas las features extraídas.
        """
        # Obtener regiones y temperaturas medias
        regions = self._get_regions(img, top, bottom)
        temps = [np.mean(r) if r.size > 0 else 0.0 for r in regions]
        temp_names = ['crudo', 'emulsion', 'agua']

        # Construir diccionario de features
        features = {f"thermal_{k}": float(v) for k, v in layers.items()}
        
        # Agregar temperaturas medias
        for name, temp in zip(temp_names, temps):
            features[f"thermal_temp_{name}_mean"] = float(temp)

        # Agregar métricas de interfaces y gradientes
        features.update({
            'thermal_interface_top_px': int(top),
            'thermal_interface_bottom_px': int(bottom),
            'thermal_interface_confidence': round(score / 25.0, 2) if score > 0 else 0.0,
            'thermal_gradient_max': float(np.max(np.abs(gradient))),
            'thermal_gradient_std': float(np.std(gradient)),
            'status': 'success'
        })

        return features

    def _default_output(self, status):
        """
        Devuelve un diccionario con valores por defecto cuando falla el procesamiento.
        
        Args:
            status (str): Estado del error ('not_found', 'no_interfaces_detected', 'processing_error').
        
        Returns:
            dict: Diccionario con todas las features en cero y el status correspondiente.
        """
        return {
            "status": status,
            "thermal_interface_top_px": 0,
            "thermal_interface_bottom_px": 0,
            "thermal_interface_confidence": 0.0,
            "thermal_crudo_px": 0,
            "thermal_emulsion_px": 0,
            "thermal_agua_px": 0,
            "thermal_crudo_ratio": 0.0,
            "thermal_emulsion_ratio": 0.0,
            "thermal_agua_ratio": 0.0,
            "thermal_temp_crudo_mean": 0.0,
            "thermal_temp_emulsion_mean": 0.0,
            "thermal_temp_agua_mean": 0.0,
            "thermal_gradient_max": 0.0,
            "thermal_gradient_std": 0.0
        }
