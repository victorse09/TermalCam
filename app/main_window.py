"""
ThermalCam Analyzer — Ventana Principal
Integra todos los componentes: visor, histograma, panel lateral.
"""

import os
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QKeySequence, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QStatusBar,
    QLabel, QApplication, QProgressBar, QToolBar,
    QToolButton, QMenu
)

from .thermal_analyzer import ThermalAnalyzer, ThermalPoint, load_mastfuyi_bmp
from .upscaler import ImageUpscaler
from .image_viewer import ThermalImageViewer
from .histogram_widget import HistogramWidget
from .sidebar_panel import SidebarPanel
from .report_dialog import ReportDialog
from .styles import DARK_THEME


class MainWindow(QMainWindow):
    """Ventana principal de ThermalCam Analyzer."""

    def __init__(self):
        super().__init__()
        
        # Asegurar copia del logotipo en recursos en la primera ejecución
        src_logo = "/home/vitokin/.gemini/antigravity/brain/13dd2d72-76c8-4eae-a574-1f7f402d06cd/logo_1779170526965.png"
        dst_logo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "logo.png")
        if os.path.exists(src_logo) and not os.path.exists(dst_logo):
            try:
                os.makedirs(os.path.dirname(dst_logo), exist_ok=True)
                import shutil
                shutil.copy(src_logo, dst_logo)
            except Exception as e:
                print(f"Error al copiar logo: {e}")

        # Establecer icono de la ventana principal
        if os.path.exists(dst_logo):
            self.setWindowIcon(QIcon(dst_logo))

        self.setWindowTitle("ThermalCam Analyzer — Análisis de Imágenes Térmicas")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # Componentes de lógica
        self.analyzer = ThermalAnalyzer()
        self.upscaler = ImageUpscaler()

        # Estado
        self._current_file: str = ""
        self._current_dir: str = ""
        self._file_list: list = []
        self._file_index: int = -1
        self._original_image: np.ndarray = None
        self._current_image: np.ndarray = None
        self._upscaled_image: np.ndarray = None

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

        # Aplicar estilo
        self.setStyleSheet(DARK_THEME)

    def _setup_ui(self):
        """Configura el layout principal."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Splitter principal vertical (contenido | histograma)
        v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Splitter horizontal (visor | panel lateral)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Visor de imagen
        self.viewer = ThermalImageViewer()
        self.viewer.analyzer = self.analyzer

        # Panel lateral
        methods = self.upscaler.get_available_methods()
        self.sidebar = SidebarPanel(available_methods=methods)
        self.sidebar.setMinimumWidth(280)
        self.sidebar.setMaximumWidth(400)

        h_splitter.addWidget(self.viewer)
        h_splitter.addWidget(self.sidebar)
        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 1)

        # Histograma
        self.histogram = HistogramWidget()
        self.histogram.setMinimumHeight(120)
        self.histogram.setMaximumHeight(200)

        v_splitter.addWidget(h_splitter)
        v_splitter.addWidget(self.histogram)
        v_splitter.setStretchFactor(0, 4)
        v_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(v_splitter)

    def _setup_menu(self):
        """Configura la barra de menú."""
        menubar = self.menuBar()

        # ── Archivo ────────────────────────────────────
        file_menu = menubar.addMenu("&Archivo")

        act_open = QAction(QIcon("resources/icons/folder.svg"), "Abrir Imagen...", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._open_file)
        file_menu.addAction(act_open)

        act_open_dir = QAction(QIcon("resources/icons/open.svg"), "Abrir Carpeta...", self)
        act_open_dir.setShortcut(QKeySequence("Ctrl+Shift+O"))
        act_open_dir.triggered.connect(self._open_directory)
        file_menu.addAction(act_open_dir)

        file_menu.addSeparator()

        act_export = QAction(QIcon("resources/icons/save.svg"), "Exportar Imagen Escalada...", self)
        act_export.setShortcut(QKeySequence("Ctrl+S"))
        act_export.triggered.connect(self._export_image)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # ── Ver ───────────────────────────────────────
        view_menu = menubar.addMenu("&Ver")

        act_fit = QAction(QIcon("resources/icons/zoom.svg"), "Ajustar a Ventana", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.triggered.connect(lambda: self.viewer.fitInView(
            self.viewer.scene().sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio))
        view_menu.addAction(act_fit)

        act_original = QAction(QIcon("resources/icons/undo.svg"), "Restaurar Original", self)
        act_original.setShortcut(QKeySequence("Ctrl+R"))
        act_original.triggered.connect(self._restore_original)
        view_menu.addAction(act_original)

        # ── Herramientas ───────────────────────────────
        tools_menu = menubar.addMenu("&Herramientas")

        act_colorbar = QAction(QIcon("resources/icons/target.svg"), "Seleccionar Barra de Colores", self)
        act_colorbar.triggered.connect(self._start_colorbar_selection)
        tools_menu.addAction(act_colorbar)

        act_auto_cal = QAction(QIcon("resources/icons/lightning.svg"), "Auto-Calibrar (Región por Defecto)", self)
        act_auto_cal.triggered.connect(self._auto_calibrate)
        tools_menu.addAction(act_auto_cal)

        tools_menu.addSeparator()

        act_clear = QAction(QIcon("resources/icons/trash.svg"), "Limpiar Puntos", self)
        act_clear.triggered.connect(self._clear_points)
        tools_menu.addAction(act_clear)

        # ── Informe ─────────────────────────────────────
        report_menu = menubar.addMenu("&Informe")

        act_report = QAction(QIcon("resources/icons/report.svg"), "Generar Informe PDF...", self)
        act_report.setShortcut(QKeySequence("Ctrl+P"))
        act_report.triggered.connect(self._generate_report)
        report_menu.addAction(act_report)

        # ── Ayuda ───────────────────────────────────────
        help_menu = menubar.addMenu("&Ayuda")

        act_instructions = QAction(QIcon("resources/icons/info.svg"), "Instrucciones de Uso", self)
        act_instructions.triggered.connect(self._show_instructions)
        help_menu.addAction(act_instructions)

        act_about = QAction(QIcon("resources/icons/info.svg"), "Acerca de...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _setup_toolbar(self):
        """Configura la barra de herramientas principal y de anotación."""
        toolbar = QToolBar("Herramientas")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(QIcon("resources/icons/folder.svg"), "Abrir", self._open_file)
        toolbar.addSeparator()

        act_prev = toolbar.addAction(QIcon("resources/icons/prev.svg"), "Anterior")
        act_prev.triggered.connect(self._prev_image)
        act_prev.setShortcut(QKeySequence("Left"))

        act_next = toolbar.addAction(QIcon("resources/icons/next.svg"), "Siguiente")
        act_next.triggered.connect(self._next_image)
        act_next.setShortcut(QKeySequence("Right"))

        toolbar.addSeparator()
        toolbar.addAction(QIcon("resources/icons/target.svg"), "Calibrar", self._start_colorbar_selection)
        toolbar.addAction(QIcon("resources/icons/lightning.svg"), "Auto-Cal", self._auto_calibrate)
        toolbar.addSeparator()

        # --- SECCIÓN DE ANOTACIÓN Y DIBUJO ---
        from PyQt6.QtGui import QActionGroup
        self.tool_group = QActionGroup(self)

        self.act_tool_point = QAction(QIcon("resources/icons/target.svg"), "Puntos", self)
        self.act_tool_point.setToolTip("Modo Marcador de Temperatura")
        self.act_tool_point.setCheckable(True)
        self.act_tool_point.setChecked(True)
        self.act_tool_point.triggered.connect(lambda: self.viewer.set_draw_mode("point"))
        self.tool_group.addAction(self.act_tool_point)
        toolbar.addAction(self.act_tool_point)

        self.act_tool_rect = QAction(QIcon("resources/icons/rect.svg"), "Rectángulo", self)
        self.act_tool_rect.setToolTip("Dibujar Recuadro")
        self.act_tool_rect.setCheckable(True)
        self.act_tool_rect.triggered.connect(lambda: self.viewer.set_draw_mode("rect"))
        self.tool_group.addAction(self.act_tool_rect)
        toolbar.addAction(self.act_tool_rect)

        self.act_tool_circle = QAction(QIcon("resources/icons/circle.svg"), "Círculo", self)
        self.act_tool_circle.setToolTip("Dibujar Círculo")
        self.act_tool_circle.setCheckable(True)
        self.act_tool_circle.triggered.connect(lambda: self.viewer.set_draw_mode("circle"))
        self.tool_group.addAction(self.act_tool_circle)
        toolbar.addAction(self.act_tool_circle)

        self.act_tool_text = QAction(QIcon("resources/icons/text.svg"), "Texto", self)
        self.act_tool_text.setToolTip("Añadir Anotación de Texto")
        self.act_tool_text.setCheckable(True)
        self.act_tool_text.triggered.connect(lambda: self.viewer.set_draw_mode("text"))
        self.tool_group.addAction(self.act_tool_text)
        toolbar.addAction(self.act_tool_text)

        # Dropdown menú para cambiar el color de anotación
        color_menu = QMenu(self)
        color_menu.setStyleSheet("""
            QMenu { background-color: #1a1a2e; border: 1px solid #2a2a45; }
            QMenu::item { padding: 6px 20px; color: #e8e8f0; }
            QMenu::item:selected { background-color: #ff6b35; }
        """)

        colors = [
            ("Amarillo", "#FFD700"),
            ("Naranja", "#FF6B35"),
            ("Rojo", "#E63946"),
            ("Verde", "#4C9F70"),
            ("Azul", "#4CC9F0"),
            ("Blanco", "#FFFFFF"),
            ("Negro", "#000000")
        ]

        for name, hex_val in colors:
            color_act = QAction(name, self)
            # Dibujar un pequeño cuadrado de color en la opción del menú
            from PyQt6.QtGui import QPixmap, QPainter
            pix = QPixmap(14, 14)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.fillRect(pix.rect(), QColor(hex_val))
            painter.end()
            color_act.setIcon(QIcon(pix))
            color_act.triggered.connect(lambda checked, h=hex_val: self._change_annotation_color(h))
            color_menu.addAction(color_act)

        custom_act = QAction("Personalizado...", self)
        custom_act.triggered.connect(self._choose_custom_color)
        color_menu.addAction(custom_act)

        btn_color = QToolButton(self)
        btn_color.setIcon(QIcon("resources/icons/color.svg"))
        btn_color.setToolTip("Color de Anotación")
        btn_color.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn_color.setMenu(color_menu)
        toolbar.addWidget(btn_color)

        act_clear_ann = QAction(QIcon("resources/icons/trash.svg"), "Borrar Dibujos", self)
        act_clear_ann.setToolTip("Eliminar todos los dibujos y anotaciones")
        act_clear_ann.triggered.connect(self._clear_annotations)
        toolbar.addAction(act_clear_ann)

        toolbar.addSeparator()
        toolbar.addAction(QIcon("resources/icons/report.svg"), "Informe", self._generate_report)

    def _setup_statusbar(self):
        """Configura la barra de estado."""
        status = QStatusBar()
        self.setStatusBar(status)

        self.status_file = QLabel("Sin imagen")
        self.status_resolution = QLabel("---")
        self.status_temp = QLabel("T: ---")
        self.status_cursor = QLabel("Cursor: ---")
        self.status_points = QLabel("Puntos: 0")

        for label in [self.status_file, self.status_resolution,
                       self.status_temp, self.status_cursor,
                       self.status_points]:
            status.addPermanentWidget(label)

    def _connect_signals(self):
        """Conecta todas las señales entre componentes."""
        # Viewer
        self.viewer.point_added.connect(self._on_point_added)
        self.viewer.point_removed.connect(self._on_point_removed)
        self.viewer.colorbar_selected.connect(self._on_colorbar_selected)
        self.viewer.mouse_moved.connect(self._on_mouse_moved)
        self.viewer.image_loaded.connect(self._on_image_loaded)

        # Sidebar
        self.sidebar.temperature_changed.connect(self._on_temperature_changed)
        self.sidebar.colorbar_select_requested.connect(
            self._start_colorbar_selection)
        self.sidebar.upscale_requested.connect(self._on_upscale_requested)
        self.sidebar.report_requested.connect(self._generate_report)
        self.sidebar.clear_points_requested.connect(self._clear_points)

    # ── Acciones de archivo ──────────────────────────────────

    def _open_file(self):
        """Abre un archivo de imagen."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Imagen Térmica", "",
            "Imágenes BMP (*.bmp);;Todas las imágenes (*.bmp *.png *.jpg *.jpeg);;Todos (*)")

        if filepath:
            self._load_image(filepath)
            # Poblar lista de archivos del directorio
            dir_path = os.path.dirname(filepath)
            self._populate_file_list(dir_path)
            # Encontrar índice actual
            basename = os.path.basename(filepath)
            for i, f in enumerate(self._file_list):
                if f == basename:
                    self._file_index = i
                    break

    def _open_directory(self):
        """Abre un directorio y carga la primera imagen."""
        dirpath = QFileDialog.getExistingDirectory(
            self, "Abrir Carpeta de Imágenes", "")

        if dirpath:
            self._populate_file_list(dirpath)
            if self._file_list:
                self._file_index = 0
                self._load_image(
                    os.path.join(self._current_dir, self._file_list[0]))

    def _populate_file_list(self, dirpath: str):
        """Llena la lista de archivos de imagen del directorio."""
        self._current_dir = dirpath
        extensions = {'.bmp', '.png', '.jpg', '.jpeg'}
        self._file_list = sorted([
            f for f in os.listdir(dirpath)
            if os.path.splitext(f)[1].lower() in extensions
        ])

    def _prev_image(self):
        """Carga la imagen anterior."""
        if self._file_list and self._file_index > 0:
            self._file_index -= 1
            self._load_image(
                os.path.join(self._current_dir,
                             self._file_list[self._file_index]))

    def _next_image(self):
        """Carga la imagen siguiente."""
        if self._file_list and self._file_index < len(self._file_list) - 1:
            self._file_index += 1
            self._load_image(
                os.path.join(self._current_dir,
                             self._file_list[self._file_index]))

    def _load_image(self, filepath: str):
        """Carga una imagen desde disco."""
        # Intentar primero con el loader Mastfuyi (para BMP RGB565)
        image_rgb = None
        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.bmp':
            image_rgb = load_mastfuyi_bmp(filepath)

        # Fallback a OpenCV para otros formatos o si falla el loader
        if image_rgb is None:
            img_bgr = cv2.imread(filepath, cv2.IMREAD_COLOR)
            if img_bgr is not None:
                image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        if image_rgb is None:
            QMessageBox.warning(
                self, "Error",
                f"No se pudo cargar la imagen:\n{filepath}")
            return

        self._current_file = filepath
        self._original_image = image_rgb.copy()
        self._current_image = image_rgb.copy()
        self._upscaled_image = None

        # Cargar en visor
        self.viewer.clear_points()
        self.viewer.load_image(image_rgb, is_original=True)

        # Actualizar sidebar
        h, w = image_rgb.shape[:2]
        self.sidebar.update_image_info(
            os.path.basename(filepath), (w, h))
        self.sidebar.clear_points_table()

        # Actualizar histograma
        self.histogram.update_histogram(image_rgb)

        # Actualizar status bar
        self.status_file.setText(f"{os.path.basename(filepath)}")
        self.status_resolution.setText(f"{w}×{h}")
        idx_str = ""
        if self._file_list:
            idx_str = f" [{self._file_index + 1}/{len(self._file_list)}]"
        self.status_file.setText(
            f"{os.path.basename(filepath)}{idx_str}")
        self.status_points.setText("Puntos: 0")

    def _export_image(self):
        """Exporta la imagen actual (original o escalada) como PNG."""
        if self._current_image is None:
            QMessageBox.warning(self, "Aviso", "No hay imagen cargada.")
            return

        # Desactivar modo calibración si estaba activo
        self.viewer.set_colorbar_selection_mode(False)

        # Preguntar si desea incluir los marcadores en la exportación
        has_points = len(self.viewer.get_points()) > 0
        include_markers = False
        if has_points:
            reply = QMessageBox.question(
                self, "Exportar Imagen",
                "¿Desea incluir los puntos de medición y etiquetas de temperatura en la imagen exportada?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            include_markers = (reply == QMessageBox.StandardButton.Yes)

        default_suffix = "_analizada.png" if include_markers else "_export.png"
        default_name = os.path.splitext(
            os.path.basename(self._current_file))[0] + default_suffix

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Exportar Imagen", default_name,
            "Imágenes PNG (*.png);;Imágenes JPEG (*.jpg);;Imágenes BMP (*.bmp)")

        if not filepath:
            return

        if include_markers:
            # Renderizar la escena con los marcadores a resolución completa de la imagen actual
            scene = self.viewer.scene()
            scene_rect = scene.sceneRect()
            w = int(scene_rect.width())
            h = int(scene_rect.height())

            from PyQt6.QtGui import QImage, QPainter
            qimage = QImage(w, h, QImage.Format.Format_ARGB32)
            qimage.fill(Qt.GlobalColor.transparent)

            painter = QPainter(qimage)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            scene.render(painter)
            painter.end()

            success = qimage.save(filepath)
            if success:
                self.statusBar().showMessage(f"Imagen exportada con marcadores: {filepath}", 5000)
            else:
                QMessageBox.warning(self, "Error", "No se pudo guardar la imagen con marcadores.")
        else:
            # Exportar la imagen limpia sin marcadores
            img_to_save = (self._upscaled_image
                           if self._upscaled_image is not None
                           else self._current_image)
            img_bgr = cv2.cvtColor(img_to_save, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filepath, img_bgr)
            self.statusBar().showMessage(f"Imagen exportada limpia: {filepath}", 5000)

    # ── Acciones de calibración ─────────────────────────────

    def _start_colorbar_selection(self):
        """Activa el modo de selección de barra de colores."""
        if self._original_image is None:
            QMessageBox.warning(self, "Aviso", "Primero carga una imagen.")
            return

        self.viewer.set_colorbar_selection_mode(True)
        self.statusBar().showMessage(
            "🎯 Haz click y arrastra sobre la barra de colores. "
            "Selecciona la zona del gradiente de colores.", 0)
        self.sidebar.btn_select_colorbar.setText("🎯 Seleccionando...")
        self.sidebar.btn_select_colorbar.setEnabled(False)

    def _on_colorbar_selected(self, region: tuple):
        """Callback cuando el usuario selecciona la región de la barra."""
        image = self._original_image
        if image is None:
            return

        t_min = self.sidebar.spin_tmin.value()
        t_max = self.sidebar.spin_tmax.value()
        self.analyzer.set_temperature_range(t_min, t_max)

        success = self.analyzer.extract_colorbar(image, region)

        if success:
            self.sidebar.set_calibration_status(True, region)
            self.statusBar().showMessage(
                f"✅ Barra de colores calibrada: {region[2]}×{region[3]}px, "
                f"T: {t_min:.1f}°C — {t_max:.1f}°C", 5000)
            self.status_temp.setText(
                f"T: {t_min:.1f}°C — {t_max:.1f}°C")
            # Recalcular temperaturas de puntos existentes
            self.viewer.recalculate_temperatures()
            self.sidebar.refresh_points_table(self.viewer.get_points())
        else:
            self.sidebar.set_calibration_status(False)
            QMessageBox.warning(
                self, "Error",
                "No se pudo extraer la barra de colores. "
                "La región seleccionada podría ser demasiado pequeña.")

        self.sidebar.btn_select_colorbar.setText(
            "🎯 Seleccionar Barra de Colores")
        self.sidebar.btn_select_colorbar.setEnabled(True)

    def _auto_calibrate(self):
        """Auto-calibra usando la región por defecto de Mastfuyi."""
        if self._original_image is None:
            QMessageBox.warning(self, "Aviso", "Primero carga una imagen.")
            return

        t_min = self.sidebar.spin_tmin.value()
        t_max = self.sidebar.spin_tmax.value()
        self.analyzer.set_temperature_range(t_min, t_max)

        region = ThermalAnalyzer.DEFAULT_COLORBAR_REGION
        success = self.analyzer.extract_colorbar(self._original_image, region)

        if success:
            self.sidebar.set_calibration_status(True, region)
            self.statusBar().showMessage(
                f"⚡ Auto-calibración exitosa: T {t_min:.1f}°C — {t_max:.1f}°C",
                5000)
            self.status_temp.setText(f"T: {t_min:.1f}°C — {t_max:.1f}°C")
            self.viewer.recalculate_temperatures()
            self.sidebar.refresh_points_table(self.viewer.get_points())
        else:
            QMessageBox.warning(
                self, "Error",
                "La auto-calibración falló. Usa selección manual.")

    def _on_temperature_changed(self, t_min: float, t_max: float):
        """Cuando el usuario cambia el rango de temperatura."""
        self.analyzer.set_temperature_range(t_min, t_max)
        self.status_temp.setText(f"T: {t_min:.1f}°C — {t_max:.1f}°C")

        if self.analyzer.is_calibrated():
            self.viewer.recalculate_temperatures()
            self.sidebar.refresh_points_table(self.viewer.get_points())

    # ── Acciones de upscaling ──────────────────────────────

    def _on_upscale_requested(self, method: str, factor: int):
        """Ejecuta el upscaling de la imagen."""
        if method == "restore":
            self._restore_original()
            return

        if self._original_image is None:
            QMessageBox.warning(self, "Aviso", "No hay imagen cargada.")
            return

        self.statusBar().showMessage(
            f"⬆ Aplicando upscale {method} ×{factor}...", 0)
        QApplication.processEvents()

        # Convertir a BGR para OpenCV
        img_bgr = cv2.cvtColor(self._original_image, cv2.COLOR_RGB2BGR)

        def progress_cb(msg):
            self.statusBar().showMessage(f"⬆ {msg}", 0)
            QApplication.processEvents()

        result_bgr = self.upscaler.upscale(img_bgr, method, factor, progress_cb)

        # Convertir de vuelta a RGB
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)

        self._upscaled_image = result_rgb.copy()
        self._current_image = result_rgb.copy()

        # Mostrar en visor (no reemplazar original)
        self.viewer.load_image(result_rgb, is_original=False)

        # Actualizar info
        h, w = result_rgb.shape[:2]
        oh, ow = self._original_image.shape[:2]
        self.sidebar.update_image_info(
            os.path.basename(self._current_file), (ow, oh), (w, h))
        self.status_resolution.setText(f"{w}×{h} (×{factor})")

        # Actualizar histograma
        self.histogram.update_histogram(result_rgb)

        self.statusBar().showMessage(
            f"✅ Upscale completado: {ow}×{oh} → {w}×{h}", 5000)

    def _restore_original(self):
        """Restaura la imagen original."""
        if self._original_image is None:
            return

        self._current_image = self._original_image.copy()
        self._upscaled_image = None
        self.viewer.load_image(self._original_image, is_original=True)

        h, w = self._original_image.shape[:2]
        self.sidebar.update_image_info(
            os.path.basename(self._current_file), (w, h))
        self.status_resolution.setText(f"{w}×{h}")
        self.histogram.update_histogram(self._original_image)
        self.statusBar().showMessage("↩ Imagen original restaurada", 3000)

    # ── Acciones de puntos ─────────────────────────────────

    def _on_point_added(self, point: ThermalPoint):
        """Callback cuando se añade un punto."""
        self.sidebar.add_point_to_table(point)
        count = len(self.viewer.get_points())
        self.status_points.setText(f"Puntos: {count}")

        # Actualizar histograma con marcas de puntos
        points = self.viewer.get_points()
        point_lums = [np.mean(pt.rgb) for pt in points]
        self.histogram.update_histogram(self._current_image, point_lums)

    def _on_point_removed(self, index: int):
        """Callback cuando se elimina un punto."""
        self.sidebar.refresh_points_table(self.viewer.get_points())
        count = len(self.viewer.get_points())
        self.status_points.setText(f"Puntos: {count}")

    def _clear_points(self):
        """Limpia todos los puntos."""
        self.viewer.clear_points()
        self.sidebar.clear_points_table()
        self.status_points.setText("Puntos: 0")
        if self._current_image is not None:
            self.histogram.update_histogram(self._current_image)

    def _on_mouse_moved(self, x: int, y: int, rgb: tuple):
        """Actualiza la barra de estado con la posición del cursor."""
        temp_str = ""
        if self.analyzer.is_calibrated():
            temp = self.analyzer.get_temperature(rgb)
            if temp is not None:
                temp_str = f" | T≈{temp:.1f}°C"
        self.status_cursor.setText(
            f"({x},{y}) RGB({rgb[0]},{rgb[1]},{rgb[2]}){temp_str}")

    def _on_image_loaded(self):
        """Callback cuando se carga una imagen en el visor."""
        pass

    # ── Informe ───────────────────────────────────────────

    def _generate_report(self):
        """Abre el diálogo de generación de informe."""
        if self._original_image is None:
            QMessageBox.warning(self, "Aviso", "No hay imagen cargada.")
            return

        dialog = ReportDialog(
            image_rgb=self._original_image,
            upscaled_rgb=self._upscaled_image,
            points=self.viewer.get_points(),
            t_min=self.sidebar.spin_tmin.value(),
            t_max=self.sidebar.spin_tmax.value(),
            histogram_widget=self.histogram,
            filename=os.path.basename(self._current_file),
            current_size=self.viewer.get_current_image().shape[:2] if self.viewer.get_current_image() is not None else None,
            annotations=self.viewer.get_annotations(),
            parent=self
        )
        dialog.exec()

    def _show_instructions(self):
        """Muestra las instrucciones de uso del programa."""
        instructions_text = (
            "<h3>Guía de Uso de ThermalCam Analyzer</h3>"
            "<ol>"
            "<li><b>Cargar Imagen:</b> Use el botón 📂 o presione <code>Ctrl+O</code> para abrir una imagen térmica BMP original (RGB565 de 240x240px).</li>"
            "<li><b>Auto-Calibración:</b> Introduzca los valores límite de temperatura (T Min y T Max) impresos en los bordes de la imagen en el panel lateral, y presione <b>⚡ Auto-Cal</b>. El software mapeará el gradiente de la barra lateral automáticamente.</li>"
            "<li><b>Calibración Manual:</b> Si los colores no coinciden bien, presione <b>🎯 Calibrar</b> y arrastre el cursor sobre la fina barra de colores del borde derecho de la imagen para extraer los colores manualmente.</li>"
            "<li><b>Medición de Puntos:</b> Haga clic izquierdo en cualquier parte de la imagen térmica para colocar un marcador. Su temperatura se estimará al instante basándose en la calibración y se listará en el panel lateral.</li>"
            "<li><b>Upscaling (Super-resolución):</b> Seleccione un método (por ejemplo, Lanczos o IA FSRCNN) y un factor de escala (x2, x3, x4) y haga clic en <b>Aplicar Upscale</b> para mejorar significativamente la nitidez de la imagen sin perder la precisión de la temperatura.</li>"
            "<li><b>Generar Informe:</b> Presione <code>Ctrl+P</code> o el botón de <b>Informe</b> para abrir el configurador. Agregue observaciones, el logo de su empresa, equipo analizado o una fotografía óptica (real) y exporte todo en un PDF estructurado profesionalmente.</li>"
            "</ol>"
        )
        QMessageBox.about(self, "Instrucciones de Uso", instructions_text)

    def _show_about(self):
        """Muestra el diálogo 'Acerca de' de forma estilizada con el logotipo de la aplicación."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtGui import QPixmap
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Acerca de ThermalCam Analyzer")
        dialog.setMinimumSize(420, 240)
        
        layout = QHBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Contenedor del logotipo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("🔥\nThermalCam")
            logo_label.setStyleSheet("font-size: 24px; color: #ff6b35; font-weight: bold; text-align: center;")
            
        layout.addWidget(logo_label)
        
        # 2. Información de texto
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        
        title_label = QLabel("ThermalCam Analyzer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b35; font-family: 'Outfit', 'Inter';")
        text_layout.addWidget(title_label)
        
        version_label = QLabel("Versión 1.0")
        version_label.setStyleSheet("font-size: 11px; color: #a0a0b0; font-family: 'Inter';")
        text_layout.addWidget(version_label)
        
        desc_label = QLabel(
            "Software profesional para decodificación,\n"
            "escalado inteligente (IA) y análisis\n"
            "térmico cuantitativo de imágenes\n"
            "capturadas con cámaras térmicas."
        )
        desc_label.setStyleSheet("font-size: 11px; color: #e0e0e8; line-height: 1.4; font-family: 'Inter';")
        text_layout.addWidget(desc_label)
        
        tech_label = QLabel("Desarrollado con Python 3 y PyQt6.")
        tech_label.setStyleSheet("font-size: 10px; color: #707080; font-family: 'Inter';")
        text_layout.addWidget(tech_label)
        
        community_label = QLabel("Desarrollado por Vito para la comunidad Naseriana.")
        community_label.setStyleSheet("font-size: 10px; font-weight: bold; color: #4CC9F0; font-family: 'Inter';")
        text_layout.addWidget(community_label)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #2e2e42;
                color: #e0e0e8;
                border: 1px solid #3e3e56;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3e3e56;
                border-color: #ff6b35;
            }
        """)
        btn_close.clicked.connect(dialog.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        text_layout.addLayout(btn_layout)
        
        layout.addLayout(text_layout)
        
        # Aplicar el tema oscuro global de la ventana principal
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def _change_annotation_color(self, hex_val: str):
        """Cambia el color de anotación del visor."""
        self.viewer.set_annotation_color(QColor(hex_val))
        self.statusBar().showMessage(f"🎨 Color de anotación cambiado: {hex_val}", 3000)

    def _choose_custom_color(self):
        """Abre un QColorDialog para seleccionar un color personalizado."""
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(Qt.GlobalColor.yellow, self, "Seleccionar Color")
        if color.isValid():
            self.viewer.set_annotation_color(color)
            self.statusBar().showMessage(f"🎨 Color de anotación personalizado: {color.name()}", 3000)

    def _clear_annotations(self):
        """Limpia todas las anotaciones de dibujo de la pantalla."""
        self.viewer.clear_annotations()
        self.statusBar().showMessage("🗑 Dibujos y anotaciones eliminados", 3000)
