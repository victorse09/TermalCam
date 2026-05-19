"""
ThermalCam Analyzer — Widget de Histograma
Histograma de intensidad embebido en PyQt6 usando Matplotlib.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class HistogramWidget(QWidget):
    """Widget que muestra el histograma de intensidad de la imagen térmica."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Crear figura matplotlib con fondo oscuro
        self.figure = Figure(figsize=(6, 2), dpi=100, facecolor='#0f0f1a')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #0f0f1a;")
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self._style_axes()

    def _style_axes(self):
        """Aplica estilo oscuro a los ejes."""
        self.ax.set_facecolor('#0f0f1a')
        self.ax.tick_params(colors='#8888a0', labelsize=8)
        self.ax.spines['bottom'].set_color('#2a2a45')
        self.ax.spines['left'].set_color('#2a2a45')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_xlabel('Intensidad', color='#8888a0', fontsize=9)
        self.ax.set_ylabel('Frecuencia', color='#8888a0', fontsize=9)

    def update_histogram(self, image_rgb: np.ndarray, point_values: list = None):
        """
        Actualiza el histograma con los datos de la imagen.

        Args:
            image_rgb: Imagen RGB (numpy array HxWx3).
            point_values: Lista opcional de valores de intensidad de puntos marcados.
        """
        self.ax.clear()
        self._style_axes()

        if image_rgb is None:
            self.canvas.draw()
            return

        # Calcular histogramas por canal
        colors_rgb = ['#e63946', '#06d6a0', '#4cc9f0']
        labels = ['R', 'G', 'B']

        for i, (color, label) in enumerate(zip(colors_rgb, labels)):
            channel = image_rgb[:, :, i].ravel()
            self.ax.hist(channel, bins=256, range=(0, 256),
                         color=color, alpha=0.4, label=label,
                         histtype='stepfilled', linewidth=0.5)

        # Histograma de luminancia (promedio de canales)
        gray = np.mean(image_rgb, axis=2).ravel()
        self.ax.hist(gray, bins=256, range=(0, 256),
                     color='#8888a0', alpha=0.3, label='Lum',
                     histtype='step', linewidth=1)

        # Marcar valores de puntos medidos
        if point_values:
            for val in point_values:
                self.ax.axvline(x=val, color='#FFD700', linewidth=1,
                                linestyle='--', alpha=0.7)

        self.ax.legend(fontsize=7, loc='upper right',
                       facecolor='#1a1a2e', edgecolor='#2a2a45',
                       labelcolor='#8888a0')
        self.ax.set_title('Histograma de Intensidad', color='#ff6b35',
                          fontsize=10, fontweight='bold', pad=4)
        self.figure.tight_layout(pad=1.0)
        self.canvas.draw()

    def clear_histogram(self):
        """Limpia el histograma."""
        self.ax.clear()
        self._style_axes()
        self.canvas.draw()

    def save_histogram(self, filepath: str, dpi: int = 150):
        """Guarda el histograma como imagen."""
        self.figure.savefig(filepath, dpi=dpi, facecolor='#0f0f1a',
                            bbox_inches='tight')
