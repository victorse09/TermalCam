"""
ThermalCam Analyzer — Ventana Principal
Integra todos los componentes: visor, histograma, panel lateral.
"""

import os
import cv2
import numpy as np
import zipfile
import json
import tempfile
import shutil
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QKeySequence, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QStatusBar,
    QLabel, QApplication, QProgressBar, QToolBar,
    QToolButton, QMenu, QDialog
)

from .thermal_analyzer import ThermalAnalyzer, ThermalPoint, load_mastfuyi_bmp
from .upscaler import ImageUpscaler
from .image_viewer import ThermalImageViewer, AnnotationItem
from .project_dialogs import ProjectInfoDialog, InstrumentInfoDialog
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
        self._current_project_file: str = ""

        # Proyecto Multi-Medición
        self._project_info = {
            "title": "Informe de Análisis Térmico",
            "author": "",
            "project_name": "",
            "location": "",
            "client": "",
            "date": "",
            "time": "",
            "ambient_temp": 20.0,
            "logo_path": "",
            "equipment_image_path": ""
        }
        self._instrument_info = {
            "brand": "Mastfuyi",
            "model": "",
            "serial_number": ""
        }
        self._measurements = []
        self._current_measurement_index = -1

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

        # Acciones de Proyecto
        act_new_proj = QAction("Nuevo Proyecto", self)
        act_new_proj.setShortcut(QKeySequence("Ctrl+N"))
        act_new_proj.triggered.connect(self._new_project)
        file_menu.addAction(act_new_proj)

        act_open_proj = QAction("Abrir Proyecto...", self)
        act_open_proj.setShortcut(QKeySequence("Ctrl+Shift+P"))
        act_open_proj.triggered.connect(self._open_project)
        file_menu.addAction(act_open_proj)

        act_save_proj = QAction("Guardar Proyecto", self)
        act_save_proj.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_proj.triggered.connect(self._save_project)
        file_menu.addAction(act_save_proj)

        act_save_proj_as = QAction("Guardar Proyecto Como...", self)
        act_save_proj_as.setShortcut(QKeySequence("Ctrl+Alt+S"))
        act_save_proj_as.triggered.connect(self._save_project_as)
        file_menu.addAction(act_save_proj_as)

        file_menu.addSeparator()

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

        # ── Proyecto ──────────────────────────────────
        project_menu = menubar.addMenu("&Proyecto")

        act_proj_info = QAction("Información del Proyecto...", self)
        act_proj_info.triggered.connect(self._show_project_info_dialog)
        project_menu.addAction(act_proj_info)

        act_proj_inst = QAction("Instrumento de Medición...", self)
        act_proj_inst.triggered.connect(self._show_instrument_info_dialog)
        project_menu.addAction(act_proj_inst)

        # ── Medición ──────────────────────────────────
        meas_menu = menubar.addMenu("&Medición")

        act_new_meas = QAction("Nueva Medición...", self)
        act_new_meas.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_new_meas.triggered.connect(self._add_measurement)
        meas_menu.addAction(act_new_meas)

        act_del_meas = QAction("Eliminar Medición Activa", self)
        act_del_meas.triggered.connect(self._delete_measurement)
        meas_menu.addAction(act_del_meas)

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

        # Sidebar — Nuevas señales multi-medición
        self.sidebar.measurement_changed.connect(self._change_active_measurement)
        self.sidebar.measurement_name_changed.connect(self._on_measurement_name_changed)
        self.sidebar.measurement_distance_changed.connect(self._on_measurement_distance_changed)
        self.sidebar.measurement_emissivity_changed.connect(self._on_measurement_emissivity_changed)
        self.sidebar.observations_changed.connect(self._on_observations_changed)
        self.sidebar.real_image_loaded.connect(self._on_real_image_loaded)
        self.sidebar.real_image_removed.connect(self._on_real_image_removed)

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

        # Si no hay mediciones activas, inicializamos la primera
        if not self._measurements:
            self._add_measurement_from_image(filepath, image_rgb)
        else:
            # Reemplazar la medición activa si está vacía (sin original_image)
            if len(self._measurements) == 1 and self._measurements[0]["original_image"] is None:
                m = self._measurements[0]
                m["original_image"] = image_rgb
                m["current_image"] = image_rgb.copy()
                m["thermal_file_path"] = filepath
                m["name"] = os.path.basename(filepath)
                self._current_measurement_index = 0
                self._change_active_measurement(0)
            else:
                # Agregar como nueva medición
                self._add_measurement_from_image(filepath, image_rgb)

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
        self.histogram.update_histogram(self._current_image, points)

    def _on_point_removed(self, index: int):
        """Callback cuando se elimina un punto."""
        self.sidebar.refresh_points_table(self.viewer.get_points())
        count = len(self.viewer.get_points())
        self.status_points.setText(f"Puntos: {count}")

        # Actualizar histograma con marcas de puntos actuales
        points = self.viewer.get_points()
        self.histogram.update_histogram(self._current_image, points)

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
        if not self._measurements or all(m["original_image"] is None for m in self._measurements):
            QMessageBox.warning(self, "Aviso", "No hay mediciones con imágenes térmicas en el proyecto para generar el informe.")
            return

        # Guardar estado de la actual antes de abrir el diálogo
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._save_measurement_state(self._current_measurement_index)

        dialog = ReportDialog(
            project_info=self._project_info,
            instrument_info=self._instrument_info,
            measurements=self._measurements,
            histogram_widget=self.histogram,
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
        
        version_label = QLabel("Versión 2.0")
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

    # ── Métodos de Proyecto e Instrumento ──────────────────

    def _show_project_info_dialog(self):
        """Muestra el diálogo para editar la información del proyecto."""
        dialog = ProjectInfoDialog(self._project_info, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._project_info = dialog.info
            self.statusBar().showMessage("✅ Información de proyecto actualizada", 3000)

    def _show_instrument_info_dialog(self):
        """Muestra el diálogo para editar el instrumento de medición."""
        dialog = InstrumentInfoDialog(self._instrument_info, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._instrument_info = dialog.info
            self.statusBar().showMessage("✅ Información de instrumento actualizada", 3000)

    # ── Métodos Multi-Medición ─────────────────────────────

    def _add_measurement(self):
        """Añade una nueva medición solicitando un archivo BMP al usuario."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Cargar Imagen Térmica para Nueva Medición", "",
            "Imágenes BMP (*.bmp);;Todas (*)"
        )
        if filepath:
            # Intentar cargar la imagen
            image_rgb = load_mastfuyi_bmp(filepath)
            if image_rgb is None:
                img_bgr = cv2.imread(filepath)
                if img_bgr is not None:
                    image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
            if image_rgb is None:
                QMessageBox.warning(self, "Error", f"No se pudo cargar la imagen térmica:\n{filepath}")
                return
            
            self._add_measurement_from_image(filepath, image_rgb)
            self.statusBar().showMessage(f"➕ Nueva medición agregada: {os.path.basename(filepath)}", 4000)

    def _add_measurement_from_image(self, filepath: str, image_rgb: np.ndarray):
        """Crea y añade una nueva medición a partir de una imagen térmica cargada."""
        # Si ya hay una medición activa, guardar su estado antes de cambiar
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._save_measurement_state(self._current_measurement_index)

        name = os.path.basename(filepath)
        new_m = {
            "name": name,
            "distance": 1.0,
            "emissivity": 0.95,
            "observations": "",
            "real_image_path": "",
            "thermal_file_path": filepath,
            "points": [],
            "annotations": [],
            "calibration": {
                "is_calibrated": False,
                "t_min": 20.0,
                "t_max": 50.0,
                "colorbar_region": None
            },
            "settings": {
                "upscale_method": "Cúbico (INTER_CUBIC)",
                "upscale_factor": "×2"
            },
            "original_image": image_rgb,
            "current_image": image_rgb.copy(),
            "upscaled_image": None
        }

        self._measurements.append(new_m)
        self._current_measurement_index = len(self._measurements) - 1

        # Actualizar ComboBox de la barra lateral
        names = [m["name"] for m in self._measurements]
        self.sidebar.update_measurement_list(names, self._current_measurement_index)

        # Cargar la nueva medición activa en la interfaz
        self._load_measurement_state(self._current_measurement_index)

    def _delete_measurement(self):
        """Elimina la medición seleccionada."""
        if not self._measurements:
            QMessageBox.warning(self, "Aviso", "No hay mediciones para eliminar.")
            return

        if len(self._measurements) == 1:
            QMessageBox.warning(self, "Aviso", "No se puede eliminar la única medición del proyecto.")
            return

        reply = QMessageBox.question(
            self, "Eliminar Medición",
            f"¿Estás seguro de que deseas eliminar la medición '{self._measurements[self._current_measurement_index]['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return

        # Si el archivo era temporal de descompresión, intentar borrarlo
        m_to_delete = self._measurements[self._current_measurement_index]
        if "temp" in m_to_delete.get("thermal_file_path", ""):
            try:
                os.remove(m_to_delete["thermal_file_path"])
            except:
                pass
        if m_to_delete.get("real_image_path", "") and "temp" in m_to_delete["real_image_path"]:
            try:
                os.remove(m_to_delete["real_image_path"])
            except:
                pass

        del self._measurements[self._current_measurement_index]
        
        # Ajustar índice activo
        if self._current_measurement_index >= len(self._measurements):
            self._current_measurement_index = len(self._measurements) - 1

        # Actualizar ComboBox
        names = [m["name"] for m in self._measurements]
        self.sidebar.update_measurement_list(names, self._current_measurement_index)

        # Cargar estado de la nueva medición seleccionada
        self._load_measurement_state(self._current_measurement_index)
        self.statusBar().showMessage("🗑 Medición eliminada con éxito", 4000)

    def _change_active_measurement(self, new_index: int):
        """Alterna a otra medición de la lista guardando la anterior."""
        if not (0 <= new_index < len(self._measurements)):
            return
        
        # Guardar estado de la actual
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._save_measurement_state(self._current_measurement_index)

        self._current_measurement_index = new_index
        self._load_measurement_state(new_index)

    def _save_measurement_state(self, index: int):
        """Guarda el estado actual del visor y la barra lateral en la medición especificada."""
        if not (0 <= index < len(self._measurements)):
            return
        
        m = self._measurements[index]
        m["points"] = list(self.viewer.get_points())
        m["annotations"] = list(self.viewer.get_annotations())
        m["calibration"] = {
            "is_calibrated": self.analyzer.is_calibrated(),
            "t_min": self.sidebar.spin_tmin.value(),
            "t_max": self.sidebar.spin_tmax.value(),
            "colorbar_region": self.analyzer.colorbar_region if hasattr(self.analyzer, 'colorbar_region') else None
        }
        m["settings"] = {
            "upscale_method": self.sidebar.combo_method.currentText(),
            "upscale_factor": self.sidebar.combo_factor.currentText()
        }
        m["original_image"] = self._original_image
        m["current_image"] = self._current_image
        m["upscaled_image"] = self._upscaled_image
        m["thermal_file_path"] = self._current_file

    def _load_measurement_state(self, index: int):
        """Carga el estado de la medición especificada en el visor y barra lateral."""
        if not (0 <= index < len(self._measurements)):
            return
        
        m = self._measurements[index]
        self._original_image = m["original_image"]
        self._current_image = m["current_image"]
        self._upscaled_image = m["upscaled_image"]
        self._current_file = m["thermal_file_path"]

        # Cargar en el visor
        self.viewer.clear_points()
        self.viewer.clear_annotations()

        is_orig = (self._upscaled_image is None)
        img_to_load = self._original_image if is_orig else self._upscaled_image
        if img_to_load is not None:
            self.viewer.load_image(img_to_load, is_original=is_orig)
            self.viewer.load_project_data(m["points"], m["annotations"])
            self.histogram.update_histogram(self._current_image, self.viewer.get_points())
        else:
            self.viewer.load_image(None)
            self.histogram.clear_histogram()

        # Restaurar calibración
        cal = m["calibration"]
        t_min = cal["t_min"]
        t_max = cal["t_max"]
        
        self.sidebar.spin_tmin.blockSignals(True)
        self.sidebar.spin_tmin.setValue(t_min)
        self.sidebar.spin_tmin.blockSignals(False)
        
        self.sidebar.spin_tmax.blockSignals(True)
        self.sidebar.spin_tmax.setValue(t_max)
        self.sidebar.spin_tmax.blockSignals(False)

        self.analyzer = ThermalAnalyzer()
        self.viewer.analyzer = self.analyzer
        self.analyzer.set_temperature_range(t_min, t_max)
        
        if cal["is_calibrated"] and cal["colorbar_region"] and self._original_image is not None:
            self.analyzer.extract_colorbar(self._original_image, tuple(cal["colorbar_region"]))
            self.sidebar.set_calibration_status(True, tuple(cal["colorbar_region"]))
        else:
            self.sidebar.set_calibration_status(False)

        # Cargar campos en barra lateral
        self.sidebar.update_measurement_fields(
            name=m["name"],
            distance=m["distance"],
            emissivity=m["emissivity"],
            observations=m["observations"],
            real_image_path=m["real_image_path"]
        )

        # Cargar configuraciones de upscale
        self.sidebar.combo_method.blockSignals(True)
        idx_method = self.sidebar.combo_method.findText(m["settings"]["upscale_method"])
        if idx_method >= 0:
            self.sidebar.combo_method.setCurrentIndex(idx_method)
        self.sidebar.combo_method.blockSignals(False)

        self.sidebar.combo_factor.blockSignals(True)
        idx_factor = self.sidebar.combo_factor.findText(m["settings"]["upscale_factor"])
        if idx_factor >= 0:
            self.sidebar.combo_factor.setCurrentIndex(idx_factor)
        self.sidebar.combo_factor.blockSignals(False)

        # Actualizar barra de estado e información de imagen en la barra lateral
        if self._original_image is not None:
            h, w = self._current_image.shape[:2]
            oh, ow = self._original_image.shape[:2]
            self.sidebar.update_image_info(os.path.basename(self._current_file) if self._current_file else "imagen.bmp", (ow, oh), (w, h))
            self.sidebar.refresh_points_table(self.viewer.get_points())
            
            idx_str = f" [{index + 1}/{len(self._measurements)}]"
            self.status_file.setText(f"{os.path.basename(self._current_file)}{idx_str}")
            self.status_resolution.setText(f"{w}×{h}")
            self.status_points.setText(f"Puntos: {len(m['points'])}")
        else:
            self.sidebar.update_image_info("Sin imagen cargada", (0, 0))
            self.sidebar.clear_points_table()
            self.status_file.setText("Sin imagen")
            self.status_resolution.setText("---")
            self.status_points.setText("Puntos: 0")

    def _on_measurement_name_changed(self, name: str):
        """Callback cuando cambia el nombre de la medición."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["name"] = name
            # Actualizar la lista en el ComboBox sin disparar señales recursivas
            names = [m["name"] for m in self._measurements]
            self.sidebar.update_measurement_list(names, self._current_measurement_index)

    def _on_measurement_distance_changed(self, distance: float):
        """Callback cuando cambia la distancia."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["distance"] = distance

    def _on_measurement_emissivity_changed(self, emissivity: float):
        """Callback cuando cambia la emisividad."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["emissivity"] = emissivity

    def _on_observations_changed(self, observations: str):
        """Callback cuando cambian las observaciones."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["observations"] = observations

    def _on_real_image_loaded(self, filepath: str):
        """Callback cuando se carga la foto óptica real."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["real_image_path"] = filepath
            # Refrescar los campos de la barra lateral
            m = self._measurements[self._current_measurement_index]
            self.sidebar.update_measurement_fields(
                name=m["name"],
                distance=m["distance"],
                emissivity=m["emissivity"],
                observations=m["observations"],
                real_image_path=filepath
            )

    def _on_real_image_removed(self):
        """Callback cuando se remueve la foto real."""
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._measurements[self._current_measurement_index]["real_image_path"] = ""
            # Refrescar barra lateral
            m = self._measurements[self._current_measurement_index]
            self.sidebar.update_measurement_fields(
                name=m["name"],
                distance=m["distance"],
                emissivity=m["emissivity"],
                observations=m["observations"],
                real_image_path=""
            )

    # ── Métodos de Proyecto (.tcp) ────────────────────────

    def _new_project(self):
        """Inicializa un nuevo proyecto vacío."""
        if self._original_image is not None or len(self._measurements) > 1:
            reply = QMessageBox.question(
                self, "Nuevo Proyecto",
                "¿Estás seguro de que deseas iniciar un nuevo proyecto? Se perderán todos los cambios no guardados.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self._current_project_file = ""
        self._current_file = ""
        self._original_image = None
        self._current_image = None
        self._upscaled_image = None

        self._project_info = {
            "title": "Informe de Análisis Térmico",
            "author": "",
            "project_name": "",
            "location": "",
            "client": "",
            "date": "",
            "time": "",
            "ambient_temp": 20.0,
            "logo_path": "",
            "equipment_image_path": ""
        }
        self._instrument_info = {
            "brand": "Mastfuyi",
            "model": "",
            "serial_number": ""
        }
        self._measurements = [{
            "name": "Medición 1",
            "distance": 1.0,
            "emissivity": 0.95,
            "observations": "",
            "real_image_path": "",
            "thermal_file_path": "",
            "points": [],
            "annotations": [],
            "calibration": {
                "is_calibrated": False,
                "t_min": 20.0,
                "t_max": 50.0,
                "colorbar_region": None
            },
            "settings": {
                "upscale_method": "Cúbico (INTER_CUBIC)",
                "upscale_factor": "×2"
            },
            "original_image": None,
            "current_image": None,
            "upscaled_image": None
        }]
        self._current_measurement_index = 0

        self.viewer.clear_points()
        self.viewer.clear_annotations()
        self.viewer.load_image(None)

        self.sidebar.clear_points_table()
        self.sidebar.update_image_info("Sin imagen cargada", (0, 0))
        self.sidebar.set_calibration_status(False)
        self.sidebar.update_measurement_list(["Medición 1"], 0)
        self.sidebar.update_measurement_fields("Medición 1", 1.0, 0.95, "", "")

        self.histogram.clear_histogram()
        self.status_file.setText("Listo")
        self.status_resolution.setText("---")
        self.status_points.setText("Puntos: 0")

        self.analyzer = ThermalAnalyzer()
        self.viewer.analyzer = self.analyzer

        self.setWindowTitle("ThermalCam Analyzer — Análisis de Imágenes Térmicas")
        self.statusBar().showMessage("🆕 Nuevo proyecto inicializado", 3000)

    def _save_project(self):
        """Guarda el proyecto actual en su archivo .tcp."""
        if not self._current_project_file:
            self._save_project_as()
            return

        self._perform_save_project(self._current_project_file)

    def _save_project_as(self):
        """Guarda el proyecto actual pidiendo ruta al usuario."""
        if self._original_image is None:
            QMessageBox.warning(self, "Aviso", "No hay ninguna imagen cargada en el proyecto para guardar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Guardar Proyecto",
            self._current_dir or os.path.expanduser("~"),
            "ThermalCam Project (*.tcp)"
        )

        if not filepath:
            return

        if not filepath.endswith(".tcp"):
            filepath += ".tcp"

        self._current_project_file = filepath
        self._current_dir = os.path.dirname(filepath)
        self._perform_save_project(filepath)

    def _perform_save_project(self, filepath):
        """Realiza la escritura del archivo comprimido del proyecto."""
        # Guardar estado de la medición activa actual en memoria antes de guardar en disco
        if 0 <= self._current_measurement_index < len(self._measurements):
            self._save_measurement_state(self._current_measurement_index)

        try:
            # 1. Preparar metadata.json
            saved_project_info = self._project_info.copy()
            # Si hay logotipo o imagen del equipo, los guardaremos en la raíz del ZIP y cambiaremos sus rutas a nombres relativos
            logo_name = ""
            if saved_project_info.get("logo_path") and os.path.exists(saved_project_info["logo_path"]):
                logo_name = "project_logo.png"
                saved_project_info["logo_path"] = logo_name

            equip_name = ""
            if saved_project_info.get("equipment_image_path") and os.path.exists(saved_project_info["equipment_image_path"]):
                equip_name = "project_equipment.png"
                saved_project_info["equipment_image_path"] = equip_name

            measurements_meta = []
            
            # Guardamos los archivos a escribir en un dict para procesar después de cerrar el JSON
            files_to_zip = []

            for i, m in enumerate(self._measurements):
                if m["original_image"] is None:
                    continue  # Saltar mediciones vacías sin imagen cargada

                # Calcular factor de escala para esta medición
                orig_h, orig_w = m["original_image"].shape[:2]
                curr_h, curr_w = m["current_image"].shape[:2]
                scale_factor = curr_w / orig_w

                # Escalar marcadores
                points_data = []
                for pt in m["points"]:
                    points_data.append({
                        "index": pt.index,
                        "x": int(round(pt.x / scale_factor)),
                        "y": int(round(pt.y / scale_factor)),
                        "rgb": list(pt.rgb),
                        "temperature": pt.temperature,
                        "label": pt.label
                    })

                # Escalar anotaciones
                annotations_data = []
                for ann in m["annotations"]:
                    annotations_data.append({
                        "type": ann.type,
                        "x1": ann.x1 / scale_factor,
                        "y1": ann.y1 / scale_factor,
                        "x2": ann.x2 / scale_factor,
                        "y2": ann.y2 / scale_factor,
                        "text": ann.text,
                        "color": ann.color.name()
                    })

                # Nombres de archivos dentro del ZIP
                thermal_name = f"measurement_{i+1}_thermal.bmp"
                upscaled_name = f"measurement_{i+1}_upscaler.png" if m["upscaled_image"] is not None else ""
                real_name = f"measurement_{i+1}_real.png" if m["real_image_path"] and os.path.exists(m["real_image_path"]) else ""

                m_meta = {
                    "name": m["name"],
                    "distance": m["distance"],
                    "emissivity": m["emissivity"],
                    "observations": m["observations"],
                    "thermal_file_name": thermal_name,
                    "upscaled_file_name": upscaled_name,
                    "real_file_name": real_name,
                    "calibration": {
                        "is_calibrated": m["calibration"]["is_calibrated"],
                        "t_min": m["calibration"]["t_min"],
                        "t_max": m["calibration"]["t_max"],
                        "colorbar_region": m["calibration"]["colorbar_region"]
                    },
                    "settings": {
                        "upscale_method": m["settings"]["upscale_method"],
                        "upscale_factor": m["settings"]["upscale_factor"]
                    },
                    "marked_points": points_data,
                    "annotations": annotations_data
                }
                measurements_meta.append(m_meta)

                # Añadir imágenes a la lista de archivos a comprimir
                # Imagen térmica original
                temp_thermal = os.path.join(tempfile.gettempdir(), f"temp_{i}_thermal.bmp")
                cv2.imwrite(temp_thermal, cv2.cvtColor(m["original_image"], cv2.COLOR_RGB2BGR))
                files_to_zip.append((temp_thermal, thermal_name))

                # Imagen térmica escalada
                if upscaled_name:
                    temp_up = os.path.join(tempfile.gettempdir(), f"temp_{i}_upscale.png")
                    cv2.imwrite(temp_up, cv2.cvtColor(m["upscaled_image"], cv2.COLOR_RGB2BGR))
                    files_to_zip.append((temp_up, upscaled_name))

                # Imagen real óptica
                if real_name:
                    files_to_zip.append((m["real_image_path"], real_name))

            metadata = {
                "project_version": "2.0",
                "project_info": saved_project_info,
                "instrument_info": self._instrument_info,
                "measurements": measurements_meta
            }

            # 2. Escribir ZIP
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zip_proj:
                # Escribir metadata.json
                zip_proj.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))

                # Escribir logo si existe
                if logo_name and os.path.exists(self._project_info["logo_path"]):
                    zip_proj.write(self._project_info["logo_path"], logo_name)

                # Escribir imagen de equipo si existe
                if equip_name and os.path.exists(self._project_info["equipment_image_path"]):
                    zip_proj.write(self._project_info["equipment_image_path"], equip_name)

                # Escribir todas las imágenes de mediciones
                for temp_path, arcname in files_to_zip:
                    zip_proj.write(temp_path, arcname)

            # Limpiar archivos temporales creados para la compresión
            for temp_path, arcname in files_to_zip:
                if "temp_" in temp_path:
                    try:
                        os.remove(temp_path)
                    except:
                        pass

            self.statusBar().showMessage(f"💾 Proyecto guardado: {os.path.basename(filepath)}", 5000)
            self.setWindowTitle(f"ThermalCam Analyzer — {os.path.basename(filepath)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el proyecto:\n{e}")

    def _open_project(self):
        """Abre un proyecto existente desde un archivo .tcp."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Proyecto",
            self._current_dir or os.path.expanduser("~"),
            "ThermalCam Project (*.tcp)"
        )

        if not filepath:
            return

        # Crear una carpeta temporal persistente única para este proyecto
        temp_dir = tempfile.mkdtemp(prefix="thermalcam_project_")

        try:
            with zipfile.ZipFile(filepath, 'r') as zip_proj:
                zip_proj.extractall(temp_dir)

            # 1. Cargar metadatos JSON
            json_path = os.path.join(temp_dir, 'metadata.json')
            if not os.path.exists(json_path):
                raise FileNotFoundError("El proyecto no contiene el archivo de metadatos 'metadata.json'.")

            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            project_version = metadata.get("project_version", "1.0")

            if project_version == "1.0":
                # Compatibilidad hacia atrás: Convertir proyecto 1.0 (imagen única) a formato 1.1
                self._project_info = {
                    "title": metadata.get("project_info", {}).get("title", "Informe de Análisis Térmico"),
                    "author": metadata.get("project_info", {}).get("author", ""),
                    "project_name": metadata.get("project_info", {}).get("project_name", ""),
                    "location": metadata.get("project_info", {}).get("location", ""),
                    "client": metadata.get("project_info", {}).get("client", ""),
                    "date": "",
                    "time": "",
                    "ambient_temp": 20.0,
                    "logo_path": "",
                    "equipment_image_path": ""
                }
                self._instrument_info = {
                    "brand": "Mastfuyi",
                    "model": "",
                    "serial_number": ""
                }

                # Cargar la imagen original
                bmp_path = os.path.join(temp_dir, 'original_image.bmp')
                if not os.path.exists(bmp_path):
                    raise FileNotFoundError("El proyecto no contiene la imagen original 'original_image.bmp'.")

                image_rgb = load_mastfuyi_bmp(bmp_path)
                if image_rgb is None:
                    img_bgr = cv2.imread(bmp_path)
                    if img_bgr is not None:
                        image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    else:
                        raise ValueError("No se pudo decodificar la imagen original.")

                # Reconstruir puntos y anotaciones
                points = []
                for p in metadata.get("marked_points", []):
                    pt = ThermalPoint(
                        index=p["index"],
                        x=p["x"],
                        y=p["y"],
                        rgb=tuple(p["rgb"]),
                        temperature=p["temperature"],
                        label=p.get("label", "")
                    )
                    points.append(pt)

                annotations = []
                for a in metadata.get("annotations", []):
                    ann = AnnotationItem(
                        type_=a["type"],
                        x1=a["x1"],
                        y1=a["y1"],
                        x2=a["x2"],
                        y2=a["y2"],
                        text=a.get("text", ""),
                        color=QColor(a.get("color", "#FFD700"))
                    )
                    annotations.append(ann)

                # Intentar cargar la imagen escalada si existe
                orig_name = metadata.get("original_file_name", "original.bmp")
                name_no_ext, _ = os.path.splitext(orig_name)
                upscaled_in_proj = os.path.join(temp_dir, f"{name_no_ext}_upscaler.png")

                loaded_upscaled = None
                if os.path.exists(upscaled_in_proj):
                    img_bgr = cv2.imread(upscaled_in_proj)
                    if img_bgr is not None:
                        loaded_upscaled = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

                # Calibración
                cal_data = metadata.get("calibration", {})
                t_min = cal_data.get("t_min", 20.0)
                t_max = cal_data.get("t_max", 50.0)
                
                settings = metadata.get("settings", {})
                upscale_method = settings.get("upscale_method", "Cúbico (INTER_CUBIC)")
                upscale_factor_str = settings.get("upscale_factor", "×2")

                self._measurements = [{
                    "name": orig_name,
                    "distance": 1.0,
                    "emissivity": 0.95,
                    "observations": "",
                    "real_image_path": "",
                    "thermal_file_path": bmp_path,
                    "points": points,
                    "annotations": annotations,
                    "calibration": {
                        "is_calibrated": cal_data.get("is_calibrated", False),
                        "t_min": t_min,
                        "t_max": t_max,
                        "colorbar_region": cal_data.get("colorbar_region")
                    },
                    "settings": {
                        "upscale_method": upscale_method,
                        "upscale_factor": upscale_factor_str
                    },
                    "original_image": image_rgb,
                    "current_image": loaded_upscaled if loaded_upscaled is not None else image_rgb.copy(),
                    "upscaled_image": loaded_upscaled
                }]

            else:
                # Formato de proyecto 1.1 (Multi-Medición)
                self._project_info = metadata.get("project_info", {})
                self._instrument_info = metadata.get("instrument_info", {})

                # Resolver rutas del logotipo y la imagen del equipo a la carpeta temporal unzipped
                if self._project_info.get("logo_path") == "project_logo.png":
                    self._project_info["logo_path"] = os.path.join(temp_dir, "project_logo.png")
                
                if self._project_info.get("equipment_image_path") == "project_equipment.png":
                    self._project_info["equipment_image_path"] = os.path.join(temp_dir, "project_equipment.png")

                self._measurements = []
                for m_meta in metadata.get("measurements", []):
                    # 1. Cargar imagen original BMP
                    bmp_path = os.path.join(temp_dir, m_meta["thermal_file_name"])
                    image_rgb = load_mastfuyi_bmp(bmp_path)
                    if image_rgb is None:
                        img_bgr = cv2.imread(bmp_path)
                        if img_bgr is not None:
                            image_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                        else:
                            raise ValueError(f"No se pudo cargar la imagen térmica {bmp_path}")

                    # 2. Cargar imagen escalada si existe
                    loaded_upscaled = None
                    if m_meta.get("upscaled_file_name"):
                        up_path = os.path.join(temp_dir, m_meta["upscaled_file_name"])
                        if os.path.exists(up_path):
                            img_bgr = cv2.imread(up_path)
                            if img_bgr is not None:
                                loaded_upscaled = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

                    # 3. Cargar imagen real óptica si existe
                    real_image_path = ""
                    if m_meta.get("real_file_name"):
                        real_path = os.path.join(temp_dir, m_meta["real_file_name"])
                        if os.path.exists(real_path):
                            real_image_path = real_path

                    # 4. Calcular factor de escala para recrear los puntos y dibujos en el espacio del viewer
                    orig_h, orig_w = image_rgb.shape[:2]
                    curr_h, curr_w = (loaded_upscaled.shape[:2] if loaded_upscaled is not None else (orig_h, orig_w))
                    scale_factor = curr_w / orig_w

                    # Reconstruir marcadores
                    points = []
                    for p in m_meta.get("marked_points", []):
                        pt = ThermalPoint(
                            index=p["index"],
                            x=int(round(p["x"] * scale_factor)),
                            y=int(round(p["y"] * scale_factor)),
                            rgb=tuple(p["rgb"]),
                            temperature=p["temperature"],
                            label=p.get("label", "")
                        )
                        points.append(pt)

                    # Reconstruir anotaciones
                    annotations = []
                    for a in m_meta.get("annotations", []):
                        ann = AnnotationItem(
                            type_=a["type"],
                            x1=a["x1"] * scale_factor,
                            y1=a["y1"] * scale_factor,
                            x2=a["x2"] * scale_factor,
                            y2=a["y2"] * scale_factor,
                            text=a.get("text", ""),
                            color=QColor(a.get("color", "#FFD700"))
                        )
                        annotations.append(ann)

                    m = {
                        "name": m_meta["name"],
                        "distance": m_meta.get("distance", 1.0),
                        "emissivity": m_meta.get("emissivity", 0.95),
                        "observations": m_meta.get("observations", ""),
                        "real_image_path": real_image_path,
                        "thermal_file_path": bmp_path,
                        "points": points,
                        "annotations": annotations,
                        "calibration": {
                            "is_calibrated": m_meta["calibration"].get("is_calibrated", False),
                            "t_min": m_meta["calibration"].get("t_min", 20.0),
                            "t_max": m_meta["calibration"].get("t_max", 50.0),
                            "colorbar_region": m_meta["calibration"].get("colorbar_region")
                        },
                        "settings": {
                            "upscale_method": m_meta["settings"].get("upscale_method", "Cúbico (INTER_CUBIC)"),
                            "upscale_factor": m_meta["settings"].get("upscale_factor", "×2")
                        },
                        "original_image": image_rgb,
                        "current_image": loaded_upscaled if loaded_upscaled is not None else image_rgb.copy(),
                        "upscaled_image": loaded_upscaled
                    }
                    self._measurements.append(m)

            # Cargar la primera medición
            self._current_measurement_index = 0
            self._current_project_file = filepath
            self._current_dir = os.path.dirname(filepath)

            # Actualizar barra lateral
            names = [m["name"] for m in self._measurements]
            self.sidebar.update_measurement_list(names, 0)
            self._load_measurement_state(0)

            self.statusBar().showMessage(f"📂 Proyecto cargado con éxito: {os.path.basename(filepath)}", 5000)
            self.setWindowTitle(f"ThermalCam Analyzer — {os.path.basename(filepath)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el proyecto:\n{e}")
            # Si falló, intentar limpiar la carpeta temporal
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

