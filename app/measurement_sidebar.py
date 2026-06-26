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
        self.setMaximumWidth(600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        header_layout = QHBoxLayout()
        title = QLabel("Mediciones")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ff6b35;")
        header_layout.addWidget(title)
        layout.addLayout(header_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(130, 60))
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
        import os
        from PyQt6.QtGui import QPainter
        self._is_updating = True
        self.list_widget.clear()
        
        for i, m in enumerate(measurements):
            name = m["name"]
            item_text = f"{i+1}. {name}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            combined_pixmap = QPixmap(130, 60)
            combined_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(combined_pixmap)
            
            x_offset = 0
            
            # 1. Dibujar Imagen Real (si existe)
            real_path = m.get("real_image_path", "")
            if real_path and os.path.exists(real_path):
                real_pix = QPixmap(real_path).scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(0, (60 - real_pix.height()) // 2, real_pix)
                x_offset = 70
                
            # 2. Dibujar Imagen Térmica
            if m.get("original_image") is not None:
                img_rgb = m["original_image"]
                h, w, ch = img_rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                therm_pix = QPixmap.fromImage(qimg).scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(x_offset, (60 - therm_pix.height()) // 2, therm_pix)
            
            painter.end()
            item.setIcon(QIcon(combined_pixmap))
            self.list_widget.addItem(item)
            
        if 0 <= current_index < self.list_widget.count():
            self.list_widget.setCurrentRow(current_index)
            
        self._is_updating = False
