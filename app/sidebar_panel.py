"""
ThermalCam Analyzer — Panel Lateral
Controles de temperatura, upscaling y tabla de puntos medidos.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSizePolicy, QSpacerItem
)
from .thermal_analyzer import ThermalPoint


class SidebarPanel(QWidget):
    """Panel lateral con controles de análisis y tabla de puntos."""

    # Señales
    temperature_changed = pyqtSignal(float, float)  # t_min, t_max
    colorbar_select_requested = pyqtSignal()
    upscale_requested = pyqtSignal(str, int)  # method, factor
    report_requested = pyqtSignal()
    clear_points_requested = pyqtSignal()

    def __init__(self, available_methods: list = None, parent=None):
        super().__init__(parent)
        self._available_methods = available_methods or [
            "Cúbico (INTER_CUBIC)",
            "Lanczos (INTER_LANCZOS4)"
        ]
        self._setup_ui()

    def _setup_ui(self):
        # Scroll area para el panel
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(8)
        self._layout.setContentsMargins(8, 8, 8, 8)

        self._create_info_group()
        self._create_temperature_group()
        self._create_upscale_group()
        self._create_points_group()
        self._create_report_group()

        self._layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum,
                        QSizePolicy.Policy.Expanding))

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_info_group(self):
        """Grupo de información de la imagen."""
        group = QGroupBox("Imagen")
        layout = QVBoxLayout(group)

        self.lbl_filename = QLabel("Sin imagen cargada")
        self.lbl_filename.setWordWrap(True)
        self.lbl_resolution = QLabel("Resolución: ---")
        self.lbl_resolution_upscaled = QLabel("Escalada: ---")

        for lbl in [self.lbl_filename, self.lbl_resolution,
                     self.lbl_resolution_upscaled]:
            lbl.setStyleSheet("color: #8888a0; font-size: 12px;")
            layout.addWidget(lbl)

        self._layout.addWidget(group)
        self._info_group = group

    def _create_temperature_group(self):
        """Grupo de configuración de temperatura."""
        group = QGroupBox("Temperatura")
        layout = QVBoxLayout(group)

        # T Min
        row_min = QHBoxLayout()
        row_min.addWidget(QLabel("T Min (°C):"))
        self.spin_tmin = QDoubleSpinBox()
        self.spin_tmin.setRange(-40, 1000)
        self.spin_tmin.setValue(20.0)
        self.spin_tmin.setDecimals(1)
        self.spin_tmin.setSuffix(" °C")
        row_min.addWidget(self.spin_tmin)
        layout.addLayout(row_min)

        # T Max
        row_max = QHBoxLayout()
        row_max.addWidget(QLabel("T Max (°C):"))
        self.spin_tmax = QDoubleSpinBox()
        self.spin_tmax.setRange(-40, 1000)
        self.spin_tmax.setValue(50.0)
        self.spin_tmax.setDecimals(1)
        self.spin_tmax.setSuffix(" °C")
        row_max.addWidget(self.spin_tmax)
        layout.addLayout(row_max)

        # Botón de selección de colorbar
        self.btn_select_colorbar = QPushButton("Seleccionar Barra")
        self.btn_select_colorbar.setIcon(QIcon("resources/icons/target.svg"))
        self.btn_select_colorbar.setToolTip(
            "Haz click y arrastra sobre la barra de colores de la imagen")
        self.btn_select_colorbar.clicked.connect(
            self.colorbar_select_requested.emit)
        layout.addWidget(self.btn_select_colorbar)

        # Estado de calibración
        self.lbl_calibration = QLabel("⚠ Sin calibrar")
        self.lbl_calibration.setStyleSheet(
            "color: #ffd166; font-size: 11px; padding: 4px;")
        layout.addWidget(self.lbl_calibration)

        # Aplicar cambios de temperatura
        self.btn_apply_temp = QPushButton("Aplicar Rango")
        self.btn_apply_temp.clicked.connect(self._on_temperature_apply)
        layout.addWidget(self.btn_apply_temp)

        self._layout.addWidget(group)

    def _create_upscale_group(self):
        """Grupo de controles de upscaling."""
        group = QGroupBox("Upscaling")
        layout = QVBoxLayout(group)

        # Método
        row_method = QHBoxLayout()
        row_method.addWidget(QLabel("Método:"))
        self.combo_method = QComboBox()
        self.combo_method.addItems(self._available_methods)
        row_method.addWidget(self.combo_method)
        layout.addLayout(row_method)

        # Factor
        row_factor = QHBoxLayout()
        row_factor.addWidget(QLabel("Factor:"))
        self.combo_factor = QComboBox()
        self.combo_factor.addItems(["×2", "×3", "×4"])
        row_factor.addWidget(self.combo_factor)
        layout.addLayout(row_factor)

        # Botón aplicar
        self.btn_upscale = QPushButton("Aplicar Upscale")
        self.btn_upscale.setIcon(QIcon("resources/icons/up.svg"))
        self.btn_upscale.setObjectName("btnPrimary")
        self.btn_upscale.clicked.connect(self._on_upscale_apply)
        layout.addWidget(self.btn_upscale)

        # Botón restaurar original
        self.btn_restore = QPushButton("Restaurar Original")
        self.btn_restore.setIcon(QIcon("resources/icons/undo.svg"))
        self.btn_restore.clicked.connect(lambda: self.upscale_requested.emit("restore", 1))
        layout.addWidget(self.btn_restore)

        self._layout.addWidget(group)

    def _create_points_group(self):
        """Grupo de tabla de puntos medidos."""
        group = QGroupBox("Puntos Medidos")
        layout = QVBoxLayout(group)

        # Tabla
        self.table_points = QTableWidget()
        self.table_points.setColumnCount(5)
        self.table_points.setHorizontalHeaderLabels(
            ["#", "X", "Y", "RGB", "T° (°C)"])
        self.table_points.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table_points.verticalHeader().setVisible(False)
        self.table_points.setAlternatingRowColors(True)
        self.table_points.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table_points.setMinimumHeight(150)
        layout.addWidget(self.table_points)

        # Botón limpiar puntos
        self.btn_clear_points = QPushButton("Limpiar Puntos")
        self.btn_clear_points.setIcon(QIcon("resources/icons/trash.svg"))
        self.btn_clear_points.setObjectName("btnDanger")
        self.btn_clear_points.clicked.connect(
            self.clear_points_requested.emit)
        layout.addWidget(self.btn_clear_points)

        self._layout.addWidget(group)
        self._points_group = group

    def _create_report_group(self):
        """Grupo de generación de informe."""
        group = QGroupBox("Informe")
        layout = QVBoxLayout(group)

        self.btn_report = QPushButton("Generar Informe PDF")
        self.btn_report.setIcon(QIcon("resources/icons/report.svg"))
        self.btn_report.setObjectName("btnPrimary")
        self.btn_report.setMinimumHeight(40)
        font = self.btn_report.font()
        font.setPointSize(13)
        font.setBold(True)
        self.btn_report.setFont(font)
        self.btn_report.clicked.connect(self.report_requested.emit)
        layout.addWidget(self.btn_report)

        self._layout.addWidget(group)

    # ── Slots ──────────────────────────────────────────────

    def _on_temperature_apply(self):
        """Emite señal con los nuevos valores de temperatura."""
        self.temperature_changed.emit(
            self.spin_tmin.value(), self.spin_tmax.value())

    def _on_upscale_apply(self):
        """Emite señal de upscale con método y factor."""
        method = self.combo_method.currentText()
        factor_text = self.combo_factor.currentText()
        factor = int(factor_text.replace("×", ""))
        self.upscale_requested.emit(method, factor)

    # ── Métodos públicos ────────────────────────────────────

    def update_image_info(self, filename: str, original_size: tuple,
                          current_size: tuple = None):
        """Actualiza la información de la imagen en el panel."""
        self.lbl_filename.setText(f"{filename}")
        self.lbl_resolution.setText(
            f"Original: {original_size[0]}×{original_size[1]}")
        if current_size:
            self.lbl_resolution_upscaled.setText(
                f"Actual: {current_size[0]}×{current_size[1]}")
        else:
            self.lbl_resolution_upscaled.setText("Actual: ---")

    def set_calibration_status(self, calibrated: bool, region: tuple = None):
        """Actualiza el estado de calibración."""
        if calibrated and region:
            self.lbl_calibration.setText(
                f"✅ Calibrada ({region[2]}×{region[3]}px)")
            self.lbl_calibration.setStyleSheet(
                "color: #06d6a0; font-size: 11px; padding: 4px;")
        else:
            self.lbl_calibration.setText("⚠ Sin calibrar")
            self.lbl_calibration.setStyleSheet(
                "color: #ffd166; font-size: 11px; padding: 4px;")

    def add_point_to_table(self, point: ThermalPoint):
        """Añade un punto a la tabla."""
        row = self.table_points.rowCount()
        self.table_points.insertRow(row)

        items = [
            QTableWidgetItem(f"P{point.index}"),
            QTableWidgetItem(str(point.x)),
            QTableWidgetItem(str(point.y)),
            QTableWidgetItem(f"({point.rgb[0]},{point.rgb[1]},{point.rgb[2]})"),
            QTableWidgetItem(
                f"{point.temperature:.1f}" if point.temperature is not None
                else "---"),
        ]

        for col, item in enumerate(items):
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_points.setItem(row, col, item)

        # Color de temperatura en la celda
        if point.temperature is not None:
            temp_item = items[-1]
            temp_item.setForeground(QColor("#ff6b35"))

    def clear_points_table(self):
        """Limpia la tabla de puntos."""
        self.table_points.setRowCount(0)

    def refresh_points_table(self, points: list):
        """Refresca toda la tabla con la lista de puntos."""
        self.clear_points_table()
        for pt in points:
            self.add_point_to_table(pt)

    def set_available_methods(self, methods: list):
        """Actualiza los métodos disponibles."""
        self.combo_method.clear()
        self.combo_method.addItems(methods)
