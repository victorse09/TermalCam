"""
ThermalCam Analyzer — Motor de Análisis Térmico
Maneja BMP RGB565 de cámara Mastfuyi (240×240, 16-bit, BI_BITFIELDS).
Extrae temperaturas a partir de la barra de colores de la imagen.
"""

import struct
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class ThermalPoint:
    """Representa un punto marcado con datos de temperatura."""
    index: int
    x: int
    y: int
    rgb: tuple
    temperature: Optional[float] = None
    label: str = ""


def load_mastfuyi_bmp(filepath: str) -> Optional[np.ndarray]:
    """
    Carga un BMP RGB565 de la cámara Mastfuyi.
    Estas cámaras generan BMP con header tipo 56 (BITMAPV3INFOHEADER),
    16-bit por píxel con compresión BI_BITFIELDS (tipo 3) y máscaras RGB565.

    Args:
        filepath: Ruta al archivo BMP.

    Returns:
        Imagen como array numpy RGB (H×W×3, uint8), o None si falla.
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        # Validar magic number BMP
        if data[0:2] != b'BM':
            return None

        # Leer header
        data_offset = struct.unpack_from('<I', data, 10)[0]
        dib_size = struct.unpack_from('<I', data, 14)[0]
        width = struct.unpack_from('<i', data, 18)[0]
        height = struct.unpack_from('<i', data, 22)[0]
        bpp = struct.unpack_from('<H', data, 28)[0]
        compression = struct.unpack_from('<I', data, 30)[0]

        # Soportar 16-bit RGB565 con BI_BITFIELDS
        if bpp == 16 and compression == 3:
            r_mask = struct.unpack_from('<I', data, 54)[0]
            g_mask = struct.unpack_from('<I', data, 58)[0]
            b_mask = struct.unpack_from('<I', data, 62)[0]

            pixels_raw = np.frombuffer(data[data_offset:], dtype=np.uint16)
            abs_height = abs(height)
            pixels_raw = pixels_raw[:width * abs_height].reshape(abs_height, width)

            # BMP bottom-up si height > 0
            if height > 0:
                pixels_raw = np.flipud(pixels_raw)

            p32 = pixels_raw.astype(np.uint32)

            # Decodificar según máscaras
            def decode_channel(mask):
                shift = 0
                m = mask
                while m and not (m & 1):
                    shift += 1
                    m >>= 1
                bits = bin(mask >> shift).count('1')
                max_val = (1 << bits) - 1
                return ((p32 & mask) >> shift) * 255 // max_val if max_val > 0 else np.zeros_like(p32)

            r_ch = decode_channel(r_mask)
            g_ch = decode_channel(g_mask)
            b_ch = decode_channel(b_mask)

            return np.stack([r_ch, g_ch, b_ch], axis=2).astype(np.uint8)

        # Soportar 24-bit BMP estándar
        elif bpp == 24:
            row_size = ((width * 3 + 3) // 4) * 4
            abs_height = abs(height)
            pixels_raw = np.frombuffer(data[data_offset:data_offset + row_size * abs_height],
                                       dtype=np.uint8).reshape(abs_height, row_size)
            # Recortar padding
            pixels_bgr = pixels_raw[:, :width * 3].reshape(abs_height, width, 3)
            if height > 0:
                pixels_bgr = np.flipud(pixels_bgr)
            # BGR → RGB
            return pixels_bgr[:, :, ::-1].copy()

        # Soportar 32-bit BMP
        elif bpp == 32:
            abs_height = abs(height)
            pixels_raw = np.frombuffer(data[data_offset:], dtype=np.uint8)
            pixels_raw = pixels_raw[:width * abs_height * 4].reshape(abs_height, width, 4)
            if height > 0:
                pixels_raw = np.flipud(pixels_raw)
            return pixels_raw[:, :, 2::-1].copy()  # BGRA → RGB

        return None

    except Exception as e:
        print(f"Error cargando BMP: {e}")
        return None


class ThermalAnalyzer:
    """
    Motor de análisis térmico.
    Construye una Lookup Table (LUT) a partir de la barra de colores
    de la imagen térmica y mapea colores RGB a temperaturas.
    """

    # Valores por defecto para cámara Mastfuyi (240×240)
    DEFAULT_COLORBAR_REGION = (221, 27, 2, 166)  # (x, y, w, h) (y=27 a y=193)

    def __init__(self):
        self.t_min: float = 20.0
        self.t_max: float = 50.0
        self.colorbar_lut: list = []
        self.colorbar_region: Optional[tuple] = None  # (x, y, w, h)
        self._lut_array: Optional[np.ndarray] = None
        self._lut_temps: Optional[np.ndarray] = None

    def set_temperature_range(self, t_min: float, t_max: float):
        """Establece el rango de temperatura (°C)."""
        self.t_min = t_min
        self.t_max = t_max
        if self.colorbar_lut:
            self._rebuild_temp_mapping()

    def _rebuild_temp_mapping(self):
        """Recalcula la asignación de temperaturas en la LUT existente."""
        if not self.colorbar_lut:
            return
        n = len(self.colorbar_lut)
        for i, entry in enumerate(self.colorbar_lut):
            frac = i / max(n - 1, 1)
            temp = self.t_max - frac * (self.t_max - self.t_min)
            entry['temperature'] = temp
        self._update_cache()

    def _update_cache(self):
        """Actualiza arrays numpy para búsqueda vectorizada rápida."""
        if not self.colorbar_lut:
            self._lut_array = None
            self._lut_temps = None
            return
        self._lut_array = np.array(
            [e['rgb'] for e in self.colorbar_lut], dtype=np.float32
        )
        self._lut_temps = np.array(
            [e['temperature'] for e in self.colorbar_lut], dtype=np.float32
        )

    def extract_colorbar(self, image: np.ndarray, region: tuple) -> bool:
        """
        Extrae la barra de colores de la imagen y construye la LUT.

        Args:
            image: Imagen en formato RGB (numpy array HxWx3).
            region: Tupla (x, y, w, h) definiendo la región de la barra.

        Returns:
            True si la extracción fue exitosa.
        """
        x, y, w, h = region
        ih, iw = image.shape[:2]

        # Validar región
        if x < 0 or y < 0 or x + w > iw or y + h > ih or w < 1 or h < 5:
            return False

        self.colorbar_region = region
        colorbar = image[y:y + h, x:x + w]

        # Promediar horizontalmente si hay más de una columna
        if w > 1:
            colorbar_avg = np.mean(colorbar, axis=1)
        else:
            colorbar_avg = colorbar[:, 0, :]

        # ── AUTO-RECORTE DE BORDES OSCUROS (MEJORA DE PRECISIÓN DE LA ESCALA) ──
        # Calcula la luminancia para cada fila de la selección: L = 0.299*R + 0.587*G + 0.114*B
        lums = 0.299 * colorbar_avg[:, 0] + 0.587 * colorbar_avg[:, 1] + 0.114 * colorbar_avg[:, 2]

        # Encontrar dónde inicia el gradiente térmico real (luminancia > 35)
        start_idx = 0
        for i in range(len(lums)):
            if lums[i] > 35:
                start_idx = i
                break

        # Encontrar dónde termina el gradiente térmico real (desde abajo hacia arriba)
        end_idx = len(lums) - 1
        for i in range(len(lums) - 1, -1, -1):
            if lums[i] > 35:
                end_idx = i
                break

        # Aplicar el recorte al gradiente si el área recortada es representativa
        if end_idx > start_idx + 5:
            colorbar_avg = colorbar_avg[start_idx:end_idx + 1]
            self.colorbar_region = (x, y + start_idx, w, len(colorbar_avg))

        self.colorbar_lut = []
        for row in range(len(colorbar_avg)):
            rgb = tuple(int(c) for c in colorbar_avg[row])
            frac = row / max(len(colorbar_avg) - 1, 1)
            temp = self.t_max - frac * (self.t_max - self.t_min)
            self.colorbar_lut.append({
                'rgb': rgb,
                'temperature': temp,
                'position': row
            })

        self._update_cache()
        return True

    def get_temperature(self, rgb: tuple) -> Optional[float]:
        """
        Obtiene la temperatura estimada para un color RGB.
        Usa distancia euclidiana para encontrar el color más cercano en la LUT.

        Args:
            rgb: Tupla (R, G, B) del píxel.

        Returns:
            Temperatura estimada en °C, o None si no hay LUT.
        """
        if self._lut_array is None or len(self._lut_array) == 0:
            return None

        rgb_arr = np.array(rgb, dtype=np.float32)
        distances = np.linalg.norm(self._lut_array - rgb_arr, axis=1)
        min_idx = np.argmin(distances)
        min_dist = distances[min_idx]

        # Coincidencia exacta o casi exacta
        if min_dist < 1.0:
            return float(self._lut_temps[min_idx])

        # Interpolación ponderada entre los 2 más cercanos
        if len(distances) > 1:
            sorted_idx = np.argsort(distances)[:2]
            idx1, idx2 = sorted_idx
            d1, d2 = distances[idx1], distances[idx2]
            total = d1 + d2
            if total > 0:
                t1 = self._lut_temps[idx1]
                t2 = self._lut_temps[idx2]
                temp = (t1 * d2 + t2 * d1) / total
                return float(temp)

        return float(self._lut_temps[min_idx])

    def get_temperature_at_pixel(self, image: np.ndarray, x: int, y: int) -> Optional[float]:
        """Obtiene la temperatura en una posición específica de la imagen."""
        h, w = image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            rgb = tuple(int(c) for c in image[y, x])
            return self.get_temperature(rgb)
        return None

    def is_calibrated(self) -> bool:
        """Retorna True si la LUT está configurada."""
        return len(self.colorbar_lut) > 0
