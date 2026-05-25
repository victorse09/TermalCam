"""
ThermalCam Analyzer — Widget de Histograma
Histograma de intensidad embebido en PyQt6 usando Matplotlib.
Permite alternar entre escala lineal/logarítmica/raíz cuadrada y mostrar marcas de puntos de temperatura.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt


class HistogramWidget(QWidget):
    """Widget que muestra el histograma de intensidad de la imagen térmica."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_marked_points = True
        self.show_point_labels = True
        self.y_scale_mode = "linear"  # "linear", "log" o "sqrt"
        self._last_image_rgb = None
        self._last_points = None
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

    def update_histogram(self, image_rgb: np.ndarray, points: list = None):
        """
        Actualiza el histograma con los datos de la imagen.

        Args:
            image_rgb: Imagen RGB (numpy array HxWx3).
            points: Lista opcional de objetos ThermalPoint o valores numéricos.
        """
        self._last_image_rgb = image_rgb
        self._last_points = points

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
        if self.show_marked_points and points:
            for pt in points:
                # Comprobar si es un objeto ThermalPoint o un valor numérico
                if hasattr(pt, 'rgb'):
                    val = np.mean(pt.rgb)
                    label_text = f"P{pt.index}"
                else:
                    val = pt
                    label_text = ""

                # Dibujar línea vertical
                self.ax.axvline(x=val, color='#FFD700', linewidth=1,
                                linestyle='--', alpha=0.7)

                # Dibujar etiqueta si está habilitado y tiene nombre
                if self.show_point_labels and label_text:
                    # Obtener los límites del eje Y para posicionar el texto en la parte superior
                    ylim = self.ax.get_ylim()
                    
                    # Calcular posición en función de la escala
                    if self.y_scale_mode == "log":
                        # En escala log, la posición visual de 80% se calcula usando logaritmos
                        y_min_log = np.log10(max(ylim[0], 1e-1))
                        y_max_log = np.log10(max(ylim[1], 1e0))
                        y_pos = 10 ** (y_min_log + 0.8 * (y_max_log - y_min_log))
                    elif self.y_scale_mode == "sqrt":
                        # En escala de raíz cuadrada, la posición visual de 80%
                        y_min_sqrt = np.sqrt(max(ylim[0], 0))
                        y_max_sqrt = np.sqrt(max(ylim[1], 0))
                        y_pos = (y_min_sqrt + 0.8 * (y_max_sqrt - y_min_sqrt)) ** 2
                    else:
                        y_pos = ylim[1] * 0.8  # 80% de la altura en lineal

                    self.ax.text(val + 2, y_pos, label_text,
                                 color='#FFD700', fontsize=8, fontweight='bold',
                                 bbox=dict(facecolor='#1a1a2e', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

        # Aplicar la escala de frecuencia en el eje Y
        from matplotlib.ticker import ScalarFormatter
        
        if self.y_scale_mode == "log":
            self.ax.set_yscale('log', nonpositive='clip')
            self.ax.set_ylabel('Frecuencia (Logarítmica)', color='#8888a0', fontsize=9)
            
            # Formatear etiquetas para mostrar enteros en lugar de potencias de 10
            formatter = ScalarFormatter()
            formatter.set_scientific(False)
            self.ax.yaxis.set_major_formatter(formatter)
            
        elif self.y_scale_mode == "sqrt":
            # Escala de Raíz Cuadrada (stretches lower ranges and compresses higher ranges)
            # Ideal para ver detalles finos sin colapsar las etiquetas numéricas
            self.ax.set_yscale('function', functions=(lambda x: np.sqrt(np.maximum(x, 0)), lambda x: x**2))
            self.ax.set_ylabel('Frecuencia (Raíz Cuadrada)', color='#8888a0', fontsize=9)
            
            # Asegurar etiquetas con formato numérico decimal claro
            formatter = ScalarFormatter()
            formatter.set_scientific(False)
            self.ax.yaxis.set_major_formatter(formatter)
            
        else:
            self.ax.set_yscale('linear')
            self.ax.set_ylabel('Frecuencia (Lineal)', color='#8888a0', fontsize=9)

        self.ax.legend(fontsize=7, loc='upper right',
                       facecolor='#1a1a2e', edgecolor='#2a2a45',
                       labelcolor='#8888a0')
        
        # Determinar etiqueta de la escala actual
        if self.y_scale_mode == "linear":
            scale_label = "Lineal"
        elif self.y_scale_mode == "log":
            scale_label = "Logarítmica"
        else:
            scale_label = "Raíz Cuadrada (Estirada)"
            
        self.ax.set_title(f"Histograma de Intensidad ({scale_label})", color='#ff6b35',
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

    def save_histogram_for_data(self, filepath: str, image_rgb: np.ndarray, points: list = None, dpi: int = 150):
        """Genera y guarda un histograma para datos específicos sin alterar permanentemente el estado visual del widget."""
        # Respaldar datos actuales
        old_img = self._last_image_rgb
        old_pts = self._last_points
        
        # Generar histograma para los nuevos datos
        self.update_histogram(image_rgb, points)
        
        # Guardar a archivo
        self.save_histogram(filepath, dpi)
        
        # Restaurar estado original
        if old_img is not None:
            self.update_histogram(old_img, old_pts)
        else:
            self.clear_histogram()

    # ── Menú Contextual e Interacciones ────────────────────

    def contextMenuEvent(self, event):
        """Implementa menú contextual interactivo para cambiar escalas y visualización."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
                color: #e8e8f0;
                border: 1px solid #2a2a45;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ff6b35;
                color: white;
            }
            QMenu::item:disabled {
                color: #555570;
            }
        """)

        # Título del menú contextual
        title_action = menu.addAction("Ajustes del Histograma")
        title_action.setEnabled(False)
        menu.addSeparator()

        # Acción: Mostrar marcas de puntos
        act_show_points = QAction("Mostrar Puntos en Histograma", self)
        act_show_points.setCheckable(True)
        act_show_points.setChecked(self.show_marked_points)
        act_show_points.triggered.connect(self._toggle_show_marked_points)
        menu.addAction(act_show_points)

        # Acción: Mostrar etiquetas de marcas
        act_show_labels = QAction("Mostrar Etiquetas de Puntos (P1, P2...)", self)
        act_show_labels.setCheckable(True)
        act_show_labels.setChecked(self.show_point_labels)
        act_show_labels.setEnabled(self.show_marked_points)
        act_show_labels.triggered.connect(self._toggle_show_point_labels)
        menu.addAction(act_show_labels)

        menu.addSeparator()

        # Grupo: Escala de Y
        act_linear = QAction("Escala de Frecuencia: Lineal", self)
        act_linear.setCheckable(True)
        act_linear.setChecked(self.y_scale_mode == "linear")
        act_linear.triggered.connect(lambda: self._set_scale_mode("linear"))
        menu.addAction(act_linear)

        act_sqrt = QAction("Escala: Raíz Cuadrada (Estirada / Compacta)", self)
        act_sqrt.setCheckable(True)
        act_sqrt.setChecked(self.y_scale_mode == "sqrt")
        act_sqrt.triggered.connect(lambda: self._set_scale_mode("sqrt"))
        menu.addAction(act_sqrt)

        act_log = QAction("Escala: Logarítmica pura (10, 100, 1000...)", self)
        act_log.setCheckable(True)
        act_log.setChecked(self.y_scale_mode == "log")
        act_log.triggered.connect(lambda: self._set_scale_mode("log"))
        menu.addAction(act_log)

        menu.exec(event.globalPos())

    def _toggle_show_marked_points(self, checked):
        self.show_marked_points = checked
        self._redraw()

    def _toggle_show_point_labels(self, checked):
        self.show_point_labels = checked
        self._redraw()

    def _set_scale_mode(self, mode):
        self.y_scale_mode = mode
        self._redraw()

    def _redraw(self):
        """Redibuja de forma interna usando los últimos datos guardados."""
        if self._last_image_rgb is not None:
            self.update_histogram(self._last_image_rgb, self._last_points)
