"""
ThermalCam Analyzer — Motor de Upscaling
Escalado clásico (OpenCV) y opcionalmente IA (dnn_superres).
"""

import cv2
import numpy as np
import os
import urllib.request
from typing import Optional, Callable

# URLs de descarga de modelos preentrenados
MODEL_URLS = {
    "FSRCNN_x2": "https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x2.pb",
    "FSRCNN_x3": "https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x3.pb",
    "FSRCNN_x4": "https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x4.pb",
    "ESPCN_x2": "https://raw.githubusercontent.com/fannymonori/TF-ESPCN/master/export/ESPCN_x2.pb",
    "ESPCN_x3": "https://raw.githubusercontent.com/fannymonori/TF-ESPCN/master/export/ESPCN_x3.pb",
    "ESPCN_x4": "https://raw.githubusercontent.com/fannymonori/TF-ESPCN/master/export/ESPCN_x4.pb",
}

# Métodos de interpolación clásica
CLASSIC_METHODS = {
    "Cúbico (INTER_CUBIC)": cv2.INTER_CUBIC,
    "Lanczos (INTER_LANCZOS4)": cv2.INTER_LANCZOS4,
    "Lineal (INTER_LINEAR)": cv2.INTER_LINEAR,
    "Nearest (INTER_NEAREST)": cv2.INTER_NEAREST,
}


class ImageUpscaler:
    """Motor de upscaling para imágenes térmicas."""

    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self._sr = None
        self._has_dnn_superres = self._check_dnn_superres()

    def _check_dnn_superres(self) -> bool:
        """Verifica si dnn_superres está disponible."""
        try:
            from cv2 import dnn_superres
            return True
        except ImportError:
            return False

    @property
    def has_ai_upscaling(self) -> bool:
        return self._has_dnn_superres

    def get_available_methods(self) -> list:
        """Retorna lista de métodos disponibles."""
        methods = list(CLASSIC_METHODS.keys())
        if self._has_dnn_superres:
            methods.extend(["FSRCNN (IA)", "ESPCN (IA)"])
        return methods

    def get_available_factors(self, method: str) -> list:
        """Retorna factores de escala disponibles para un método."""
        if "IA" in method:
            return [2, 3, 4]
        else:
            return [2, 3, 4, 5, 6, 8]

    def upscale_classic(self, image: np.ndarray, factor: int,
                        method: str = "Cúbico (INTER_CUBIC)") -> np.ndarray:
        """
        Upscale clásico con interpolación OpenCV.

        Args:
            image: Imagen de entrada (numpy array).
            factor: Factor de escala.
            method: Nombre del método de interpolación.

        Returns:
            Imagen escalada.
        """
        interpolation = CLASSIC_METHODS.get(method, cv2.INTER_CUBIC)
        h, w = image.shape[:2]
        new_w, new_h = w * factor, h * factor
        return cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    def upscale_ai(self, image: np.ndarray, model_name: str, factor: int,
                   progress_callback: Optional[Callable] = None) -> Optional[np.ndarray]:
        """
        Upscale con IA usando dnn_superres.

        Args:
            image: Imagen de entrada BGR (numpy array).
            model_name: "FSRCNN" o "ESPCN".
            factor: Factor de escala (2, 3 o 4).
            progress_callback: Función opcional para reportar progreso.

        Returns:
            Imagen escalada o None si falla.
        """
        if not self._has_dnn_superres:
            return None

        from cv2 import dnn_superres

        model_key = f"{model_name}_x{factor}"
        model_path = os.path.join(self.models_dir, f"{model_key}.pb")

        # Verificar si el modelo existe
        if not os.path.exists(model_path):
            if progress_callback:
                progress_callback(f"Descargando modelo {model_key}...")
            success = self.download_model(model_key)
            if not success:
                return None

        if progress_callback:
            progress_callback(f"Cargando modelo {model_key}...")

        try:
            sr = dnn_superres.DnnSuperResImpl_create()
            sr.readModel(model_path)
            sr.setModel(model_name.lower(), factor)

            if progress_callback:
                progress_callback("Procesando upscale IA...")

            result = sr.upsample(image)

            # --- POST-PROCESAMIENTO AVANZADO PARA TERMOGRAFÍA ---
            # Las redes neuronales de súper-resolución estándar (FSRCNN/ESPCN) están entrenadas para
            # imágenes fotográficas, lo que introduce ruido de rejilla y artefactos de "anillo" en los
            # degradados térmicos suaves. Solucionamos esto con un pipeline híbrido premium:

            # 1. Filtro Bilateral: Suaviza el ruido y "escalonado" cromático en los degradados
            #    manteniendo los límites de los bordes físicos perfectamente nítidos.
            smooth = cv2.bilateralFilter(result, d=7, sigmaColor=35, sigmaSpace=35)

            # 2. Mezcla Híbrida con Interpolación Lanczos:
            #    Generamos un redimensionamiento Lanczos de alta calidad matemática a la misma resolución.
            h, w = result.shape[:2]
            classic_lanczos = cv2.resize(image, (w, h), interpolation=cv2.INTER_LANCZOS4)

            # 3. addWeighted: Fusionamos 65% del modelo de IA suavizado (aporta definición física de siluetas)
            #    con 35% de Lanczos (aporta gradación térmica analógica y perfecta, sin bandas).
            blended = cv2.addWeighted(smooth, 0.65, classic_lanczos, 0.35, 0)

            return blended
        except Exception as e:
            print(f"Error en upscale IA: {e}")
            return None

    def upscale(self, image: np.ndarray, method: str, factor: int,
                progress_callback: Optional[Callable] = None) -> np.ndarray:
        """
        Método principal de upscale que despacha al método apropiado.

        Args:
            image: Imagen de entrada (numpy array BGR).
            method: Nombre del método.
            factor: Factor de escala.
            progress_callback: Callback de progreso.

        Returns:
            Imagen escalada.
        """
        if "FSRCNN" in method:
            result = self.upscale_ai(image, "FSRCNN", factor, progress_callback)
            if result is not None:
                return result
            # Fallback a cúbico
            if progress_callback:
                progress_callback("IA no disponible, usando interpolación cúbica...")
            return self.upscale_classic(image, factor)
        elif "ESPCN" in method:
            result = self.upscale_ai(image, "ESPCN", factor, progress_callback)
            if result is not None:
                return result
            if progress_callback:
                progress_callback("IA no disponible, usando interpolación cúbica...")
            return self.upscale_classic(image, factor)
        else:
            return self.upscale_classic(image, factor, method)

    def download_model(self, model_key: str) -> bool:
        """
        Descarga un modelo preentrenado desde GitHub.

        Args:
            model_key: Clave del modelo (ej: "FSRCNN_x2").

        Returns:
            True si la descarga fue exitosa.
        """
        url = MODEL_URLS.get(model_key)
        if not url:
            return False

        dest = os.path.join(self.models_dir, f"{model_key}.pb")
        try:
            urllib.request.urlretrieve(url, dest)
            return os.path.exists(dest)
        except Exception as e:
            print(f"Error descargando modelo {model_key}: {e}")
            if os.path.exists(dest):
                os.remove(dest)
            return False

    def list_downloaded_models(self) -> list:
        """Lista modelos ya descargados."""
        models = []
        if os.path.exists(self.models_dir):
            for f in os.listdir(self.models_dir):
                if f.endswith('.pb'):
                    models.append(f.replace('.pb', ''))
        return models
