"""
ThermalCam Analyzer — Barra Lateral de Mediciones
Panel izquierdo para gestionar las mediciones del proyecto mediante Drag and Drop.
"""

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
    QLabel, QPushButton, QHBoxLayout, QAbstractItemView
)

class MeasurementSidebar(QWidget):
    """Barra lateral izquierda para gestionar la lista de mediciones."""

    measurement_selected = pyqtSignal(int)
    measurements_reordered = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._is_updating = False

    def _setup_ui(self):
        self.setObjectName("measurementSidebar")
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        header_layout = QHBoxLayout()
        title = QLabel("Mediciones")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ff6b35;")
        header_layout.addWidget(title)
        layout.addLayout(header_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(60, 60))
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: 1px solid #2a2a45; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2a2a45; color: #e0e0e8; }
            QListWidget::item:selected { background-color: #3a3a5a; border-left: 3px solid #ff6b35; }
        """)
        
        layout.addWidget(self.list_widget)
        
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)

    def _on_row_changed(self, index):
        if not self._is_updating and index >= 0:
            self.measurement_selected.emit(index)

    def _on_rows_moved(self, parent, start, end, destination, row):
        # Cuando se reordena la lista, calculamos el nuevo orden de los índices originales
        if not self._is_updating:
            new_order = []
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                old_index = item.data(Qt.ItemDataRole.UserRole)
                new_order.append(old_index)
            self.measurements_reordered.emit(new_order)

    def update_list(self, measurements, current_index):
        """Actualiza la lista visual con las mediciones actuales."""
        self._is_updating = True
        self.list_widget.clear()
        
        for i, m in enumerate(measurements):
            name = m["name"]
            # Mostrar un asterisco o algo si está vacía? No, solo el nombre.
            item_text = f"{i+1}. {name}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            # Crear miniatura si la imagen existe
            if m.get("original_image") is not None:
                img_rgb = m["original_image"]
                h, w, ch = img_rgb.shape
                bytes_per_line = ch * w
                # Es importante que el array img_rgb se mantenga vivo
                qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg).scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                item.setIcon(QIcon(pixmap))
            else:
                # Icono por defecto o miniatura vacía
                pixmap = QPixmap(60, 60)
                pixmap.fill(Qt.GlobalColor.black)
                item.setIcon(QIcon(pixmap))
                
            self.list_widget.addItem(item)
            
        if 0 <= current_index < self.list_widget.count():
            self.list_widget.setCurrentRow(current_index)
            
        self._is_updating = False
