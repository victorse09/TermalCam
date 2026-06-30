"""
ThermalCam Analyzer — Diálogos de Proyecto e Instrumento
Maneja la edición de metadatos globales del proyecto y la cámara térmica.
"""

import os
from datetime import datetime
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
    QFileDialog, QFormLayout, QToolButton, QDateEdit, QTimeEdit,
    QTextEdit, QListWidget, QSplitter, QWidget, QComboBox, QSlider
)


class ProjectInfoDialog(QDialog):
    """Diálogo para configurar y guardar la información general del proyecto."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Información del Proyecto")
        self.setMinimumSize(450, 480)
        self.info = info.copy()  # Copia local de trabajo
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Grupo: Información del informe
        info_group = QGroupBox("Detalles del Proyecto y Cliente")
        form = QFormLayout(info_group)
        form.setSpacing(10)

        self.edit_title = QLineEdit(self.info.get("title", "Informe de Análisis Térmico"))
        self.edit_title.setPlaceholderText("Título del informe")
        form.addRow("Título:", self.edit_title)

        self.edit_report_number = QLineEdit(self.info.get("report_number", ""))
        self.edit_report_number.setPlaceholderText("Número o código del informe")
        form.addRow("Informe:", self.edit_report_number)

        self.edit_author = QLineEdit(self.info.get("author", ""))
        self.edit_author.setPlaceholderText("Nombre del autor/analista")
        form.addRow("Autor/Analista:", self.edit_author)

        self.edit_project = QLineEdit(self.info.get("project_name", ""))
        self.edit_project.setPlaceholderText("Nombre del proyecto o instalación")
        form.addRow("Proyecto:", self.edit_project)

        self.edit_location = QLineEdit(self.info.get("location", ""))
        self.edit_location.setPlaceholderText("Ubicación física")
        form.addRow("Ubicación:", self.edit_location)

        self.edit_client = QLineEdit(self.info.get("client", ""))
        self.edit_client.setPlaceholderText("Nombre de la empresa o cliente")
        form.addRow("Cliente/Equipo:", self.edit_client)

        # Campos de Fecha y Hora
        self.edit_date = QDateEdit()
        self.edit_date.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        self.edit_date.setCalendarPopup(True)
        date_str = self.info.get("date", "")
        if date_str:
            self.edit_date.setDate(QDate.fromString(date_str, Qt.DateFormat.ISODate))
        else:
            self.edit_date.setDate(QDate.currentDate())
        form.addRow("Fecha Medición:", self.edit_date)

        self.edit_time = QTimeEdit()
        self.edit_time.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        time_str = self.info.get("time", "")
        if time_str:
            self.edit_time.setTime(QTime.fromString(time_str, Qt.DateFormat.ISODate))
        else:
            self.edit_time.setTime(QTime.currentTime())
        form.addRow("Hora Medición:", self.edit_time)

        # Temperatura ambiente
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(-40.0, 80.0)
        self.spin_temp.setDecimals(1)
        self.spin_temp.setSuffix(" °C")
        try:
            self.spin_temp.setValue(float(self.info.get("ambient_temp", 20.0)))
        except:
            self.spin_temp.setValue(20.0)
        form.addRow("Temp. Ambiente:", self.spin_temp)

        # Logotipo
        logo_layout = QHBoxLayout()
        self.edit_logo = QLineEdit(self.info.get("logo_path", ""))
        self.edit_logo.setPlaceholderText("Ruta del logo de la empresa (opcional)")
        btn_logo = QToolButton()
        btn_logo.setText("...")
        btn_logo.clicked.connect(lambda: self._browse_file(self.edit_logo, "Seleccionar Logotipo"))
        logo_layout.addWidget(self.edit_logo)
        logo_layout.addWidget(btn_logo)
        form.addRow("Logo Empresa:", logo_layout)

        # Imagen del equipo (óptica)
        equip_layout = QHBoxLayout()
        self.edit_equip = QLineEdit(self.info.get("equipment_image_path", ""))
        self.edit_equip.setPlaceholderText("Foto óptica del equipo bajo análisis (opcional)")
        btn_equip = QToolButton()
        btn_equip.setText("...")
        btn_equip.clicked.connect(lambda: self._browse_file(self.edit_equip, "Seleccionar Foto del Equipo"))
        equip_layout.addWidget(self.edit_equip)
        equip_layout.addWidget(btn_equip)
        form.addRow("Imagen Equipo:", equip_layout)

        # Imagen del equipo 2 (óptica opcional)
        equip_layout2 = QHBoxLayout()
        self.edit_equip2 = QLineEdit(self.info.get("equipment_image_path2", ""))
        self.edit_equip2.setPlaceholderText("Segunda foto óptica del equipo (opcional)")
        btn_equip2 = QToolButton()
        btn_equip2.setText("...")
        btn_equip2.clicked.connect(lambda: self._browse_file(self.edit_equip2, "Seleccionar Segunda Foto del Equipo"))
        equip_layout2.addWidget(self.edit_equip2)
        equip_layout2.addWidget(btn_equip2)
        form.addRow("Imagen Equipo 2:", equip_layout2)

        layout.addWidget(info_group)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self._save_data)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Estilo de inputs
        if parent := self.parent():
            if hasattr(parent, 'styleSheet'):
                self.setStyleSheet(parent.styleSheet())

    def _browse_file(self, line_edit: QLineEdit, title: str):
        """Abre un diálogo de búsqueda de archivos para imágenes."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, title, "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos (*)"
        )
        if filepath:
            line_edit.setText(filepath)

    def _save_data(self):
        """Valida y guarda las entradas en el diccionario de información."""
        self.info["title"] = self.edit_title.text()
        self.info["report_number"] = self.edit_report_number.text()
        self.info["author"] = self.edit_author.text()
        self.info["project_name"] = self.edit_project.text()
        self.info["location"] = self.edit_location.text()
        self.info["client"] = self.edit_client.text()
        self.info["date"] = self.edit_date.date().toString(Qt.DateFormat.ISODate)
        self.info["time"] = self.edit_time.time().toString(Qt.DateFormat.ISODate)
        self.info["ambient_temp"] = self.spin_temp.value()
        self.info["logo_path"] = self.edit_logo.text()
        self.info["equipment_image_path"] = self.edit_equip.text()
        self.info["equipment_image_path2"] = self.edit_equip2.text()

        self.accept()


class InstrumentInfoDialog(QDialog):
    """Diálogo para configurar y guardar la información del instrumento termográfico."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instrumento de Medición")
        self.setMinimumSize(380, 240)
        self.info = info.copy()  # Copia local de trabajo
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Grupo: Detalles de la cámara
        cam_group = QGroupBox("Datos de la Cámara Térmica")
        form = QFormLayout(cam_group)
        form.setSpacing(10)

        self.edit_brand = QLineEdit(self.info.get("brand", "Mastfuyi"))
        self.edit_brand.setPlaceholderText("Ej: Mastfuyi")
        form.addRow("Marca:", self.edit_brand)

        self.edit_model = QLineEdit(self.info.get("model", ""))
        self.edit_model.setPlaceholderText("Ej: FY8300")
        form.addRow("Modelo:", self.edit_model)

        self.edit_serial = QLineEdit(self.info.get("serial_number", ""))
        self.edit_serial.setPlaceholderText("Número de serie único")
        form.addRow("Nº de Serie:", self.edit_serial)

        layout.addWidget(cam_group)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Instrumento")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self._save_data)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        if parent := self.parent():
            if hasattr(parent, 'styleSheet'):
                self.setStyleSheet(parent.styleSheet())

    def _save_data(self):
        """Guarda la información de la cámara."""
        self.info["brand"] = self.edit_brand.text()
        self.info["model"] = self.edit_model.text()
        self.info["serial_number"] = self.edit_serial.text()

        self.accept()


class ProjectObservationsDialog(QDialog):
    """Diálogo para configurar y guardar las observaciones generales del proyecto."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Observaciones del Proyecto")
        self.setMinimumSize(500, 350)
        self.info = info.copy()  # Copia local de trabajo
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Grupo: Observaciones
        obs_group = QGroupBox("Observaciones y Comentarios Generales")
        group_layout = QVBoxLayout(obs_group)
        group_layout.setSpacing(8)

        lbl_desc = QLabel(
            "Ingrese las observaciones, alcances y comentarios generales del proyecto.\n"
            "Este texto aparecerá en la página de Resumen e Instrumentación del informe."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        group_layout.addWidget(lbl_desc)

        self.edit_obs = QTextEdit()
        self.edit_obs.setPlainText(self.info.get("general_observations", ""))
        self.edit_obs.setPlaceholderText("Ej: La presente inspección técnica se realizó en condiciones normales de operación...")
        group_layout.addWidget(self.edit_obs)

        layout.addWidget(obs_group)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Observaciones")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self._save_data)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        if parent := self.parent():
            if hasattr(parent, 'styleSheet'):
                self.setStyleSheet(parent.styleSheet())

    def _save_data(self):
        """Guarda las observaciones en el diccionario local."""
        self.info["general_observations"] = self.edit_obs.toPlainText()
        self.accept()


class PointCommentsDialog(QDialog):
    """Diálogo para editar los comentarios de los puntos de forma expandida."""

    def __init__(self, points: list, initial_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Comentarios de Puntos")
        self.setMinimumSize(600, 400)
        self.points = points  # Referencia o copia, preferible trabajar con copia local de los labels
        self.comments = {pt.index: (pt.label or "") for pt in points}
        self.initial_index = initial_index
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Lista de puntos
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #1a1a2e; border: 1px solid #2a2a45; color: #e0e0e8; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2a2a45; }
            QListWidget::item:selected { background-color: #3a3a5a; border-left: 3px solid #ff6b35; color: white; }
        """)
        for pt in self.points:
            temp_str = f"{pt.temperature:.1f} °C" if pt.temperature is not None else "---"
            self.list_widget.addItem(f"P{pt.index} ({temp_str})")
            
        self.list_widget.currentRowChanged.connect(self._on_point_selected)
        splitter.addWidget(self.list_widget)

        # Editor de comentario
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_current_point = QLabel("Seleccione un punto")
        self.lbl_current_point.setStyleSheet("font-weight: bold; color: #ff6b35;")
        editor_layout.addWidget(self.lbl_current_point)
        
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("""
            QTextEdit { background-color: #1a1a2e; border: 1px solid #2a2a45; color: #e0e0e8; border-radius: 4px; padding: 8px; }
        """)
        self.text_edit.setPlaceholderText("Escriba aquí los comentarios detallados para este punto...")
        self.text_edit.textChanged.connect(self._on_text_changed)
        editor_layout.addWidget(self.text_edit)
        
        splitter.addWidget(editor_widget)
        
        # Ajustar proporciones (1:2)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setMinimumHeight(35)
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        if parent := self.parent():
            if hasattr(parent, 'styleSheet'):
                self.setStyleSheet(parent.styleSheet())
                
        # Seleccionar índice inicial si existe
        if self.points:
            row_to_select = 0
            for i, pt in enumerate(self.points):
                if pt.index == self.initial_index:
                    row_to_select = i
                    break
            self.list_widget.setCurrentRow(row_to_select)

    def _on_point_selected(self, row: int):
        if row < 0 or row >= len(self.points):
            return
        pt = self.points[row]
        self.lbl_current_point.setText(f"Editando comentario de P{pt.index}")
        
        # Cargar comentario sin emitir señal
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(self.comments.get(pt.index, ""))
        self.text_edit.blockSignals(False)

    def _on_text_changed(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.points):
            return
        pt = self.points[row]
        self.comments[pt.index] = self.text_edit.toPlainText().strip()


class ProjectHeaderDialog(QDialog):
    """Diálogo para configurar los datos de la cabecera independiente."""

    def __init__(self, header_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cabecera de Proyecto")
        self.setMinimumSize(450, 300)
        self.header_info = header_info.copy()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        group = QGroupBox("Datos para Cabecera de Informe PDF")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.edit_informe = QLineEdit(self.header_info.get("informe", ""))
        self.edit_informe.setPlaceholderText("Número o código de informe")
        form.addRow("Informe:", self.edit_informe)

        self.edit_client = QLineEdit(self.header_info.get("cliente", ""))
        self.edit_client.setPlaceholderText("Información del Cliente")
        form.addRow("Cliente:", self.edit_client)

        self.edit_date = QDateEdit()
        self.edit_date.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        self.edit_date.setCalendarPopup(True)
        date_str = self.header_info.get("fecha", "")
        if date_str:
            self.edit_date.setDate(QDate.fromString(date_str, Qt.DateFormat.ISODate))
        else:
            self.edit_date.setDate(QDate.currentDate())
        form.addRow("Fecha:", self.edit_date)

        self.edit_ref = QLineEdit(self.header_info.get("referencia", ""))
        self.edit_ref.setPlaceholderText("Referencia del documento")
        form.addRow("Referencia:", self.edit_ref)

        self.edit_content = QTextEdit(self.header_info.get("contenido", ""))
        self.edit_content.setPlaceholderText("Contenido de la cabecera...")
        form.addRow("Contenido:", self.edit_content)

        layout.addWidget(group)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def accept(self):
        self.header_info["informe"] = self.edit_informe.text().strip()
        self.header_info["cliente"] = self.edit_client.text().strip()
        self.header_info["fecha"] = self.edit_date.date().toString(Qt.DateFormat.ISODate)
        self.header_info["referencia"] = self.edit_ref.text().strip()
        self.header_info["contenido"] = self.edit_content.toPlainText().strip()
        super().accept()

class HeaderExportDialog(QDialog):
    """Diálogo para configurar el formato y la opacidad antes de generar el PDF de la cabecera."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Exportación PDF")
        self.setMinimumWidth(350)
        self.format_val = "letter"
        self.lightness = 0.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Formato de página
        group_format = QGroupBox("Formato de Página")
        form_format = QFormLayout(group_format)
        self.combo_format = QComboBox()
        self.combo_format.addItem("Carta (Letter - 215.9x279.4 mm)", "letter")
        self.combo_format.addItem("A4 (Estándar - 210x297 mm)", "a4")
        self.combo_format.addItem("Oficio (Legal - 215.9x355.6 mm)", "legal")
        form_format.addRow("Tamaño:", self.combo_format)
        layout.addWidget(group_format)
        
        # Opacidad / Brillo
        group_lightness = QGroupBox("Estilo de Portada")
        v_lightness = QVBoxLayout(group_lightness)
        self.slider_lightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_lightness.setRange(0, 100)
        self.slider_lightness.setValue(0)
        self.slider_lightness.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_lightness.setTickInterval(10)
        v_lightness.addWidget(QLabel("Aclarar barra de título:"))
        v_lightness.addWidget(self.slider_lightness)
        layout.addWidget(group_lightness)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_generate = QPushButton("Generar")
        btn_generate.setDefault(True)
        btn_generate.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        
        layout.addLayout(btn_layout)

    def accept(self):
        self.format_val = self.combo_format.currentData()
        self.lightness = self.slider_lightness.value() / 100.0
        super().accept()
