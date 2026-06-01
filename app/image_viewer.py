"""
ThermalCam Analyzer — Visor de Imagen Interactivo
QGraphicsView con zoom, pan, marcadores de temperatura y anotaciones interactivas (rectángulo, círculo, texto).
"""

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QImage, QPixmap, QPen, QBrush, QColor, QFont,
    QPainter, QCursor, QWheelEvent, QMouseEvent
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsItemGroup, QMenu, QRubberBand,
    QWidget, QInputDialog
)
from .thermal_analyzer import ThermalAnalyzer, ThermalPoint


class MarkerItem(QGraphicsItemGroup):
    """Marcador visual para un punto de medición térmica."""

    def __init__(self, x: float, y: float, index: int,
                 temperature: float = None, label_str: str = "",
                 show_label: bool = True, parent=None):
        super().__init__(parent)
        self.point_x = x
        self.point_y = y
        self.point_index = index

        size = 6
        pen_cross = QPen(QColor("#FFD700"), 1.5)
        pen_circle = QPen(QColor("#FF6B35"), 2)

        # Círculo del marcador
        circle = QGraphicsEllipseItem(x - size, y - size, size * 2, size * 2)
        circle.setPen(pen_circle)
        circle.setBrush(QBrush(QColor(255, 107, 53, 60)))
        self.addToGroup(circle)

        # Cruz
        line_h = QGraphicsLineItem(x - size * 1.5, y, x + size * 1.5, y)
        line_h.setPen(pen_cross)
        self.addToGroup(line_h)

        line_v = QGraphicsLineItem(x, y - size * 1.5, x, y + size * 1.5)
        line_v.setPen(pen_cross)
        self.addToGroup(line_v)

        # Etiqueta de texto
        temp_str = f"{temperature:.1f}°C" if temperature is not None else "---"
        if show_label and label_str.strip():
            label_text = f"P{index} ({label_str}): {temp_str}"
        else:
            label_text = f"P{index}: {temp_str}"

        label_bg = QGraphicsRectItem()
        label_bg.setBrush(QBrush(QColor(15, 15, 26, 200)))
        label_bg.setPen(QPen(QColor("#FF6B35"), 1))

        label = QGraphicsTextItem(label_text)
        label.setDefaultTextColor(QColor("#FFFFFF"))
        font = QFont("Inter", 8, QFont.Weight.Bold)
        label.setFont(font)

        # Posicionar etiqueta arriba-derecha del punto
        label.setPos(x + size + 4, y - size - 14)
        rect = label.boundingRect()
        label_bg.setRect(x + size + 2, y - size - 16,
                         rect.width() + 4, rect.height() + 2)

        self.addToGroup(label_bg)
        self.addToGroup(label)
        self._label = label
        self._label_bg = label_bg


class AnnotationItem:
    """Representa una anotación interactiva (rectángulo, círculo o texto) sobre la imagen."""
    def __init__(self, type_: str, x1: float, y1: float, x2: float, y2: float, text: str = "", color: QColor = None):
        self.type = type_          # "rect", "circle", "text"
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.text = text
        self.color = color or QColor("#FFD700")
        self.graphics_item = None


class ThermalImageViewer(QGraphicsView):
    """
    Visor interactivo de imágenes térmicas.
    Soporta zoom, pan, marcadores de temperatura, selección de barra de colores
    y anotaciones de figuras y texto personalizables.
    """

    # Señales
    point_added = pyqtSignal(ThermalPoint)
    point_removed = pyqtSignal(int)
    colorbar_selected = pyqtSignal(tuple)  # (x, y, w, h)
    mouse_moved = pyqtSignal(int, int, tuple)  # x, y, rgb
    image_loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Configuración del view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMouseTracking(True)

        # Estado
        self._pixmap_item: QGraphicsPixmapItem = None
        self._image_rgb: np.ndarray = None  # Imagen actual en RGB
        self._original_rgb: np.ndarray = None  # Imagen original sin escalar
        self._markers: list[MarkerItem] = []
        self._points: list[ThermalPoint] = []
        self._point_counter: int = 0
        self._zoom_level: float = 1.0
        self._selecting_colorbar: bool = False
        self._selection_start: QPointF = None
        self._selection_rect: QGraphicsRectItem = None
        self._panning: bool = False
        self._pan_start: QPointF = None

        # Anotaciones interactivas
        self._draw_mode = "point"  # "point", "rect", "circle", "text"
        self._annotation_color = QColor("#FFD700")  # Amarillo Oro por defecto
        self._annotations: list[AnnotationItem] = []
        self._current_drawing_item: AnnotationItem = None
        self._drawing_start: QPointF = None
        self._show_marker_labels = True

        # Analizador térmico (se configura externamente)
        self.analyzer: ThermalAnalyzer = None

    def load_image(self, image_rgb: np.ndarray, is_original: bool = True):
        """
        Carga una imagen RGB (numpy array) en el visor.

        Args:
            image_rgb: Array numpy HxWx3 en formato RGB, o None para limpiar el visor.
            is_original: Si es True, guarda como imagen original.
        """
        if image_rgb is None:
            self._image_rgb = None
            self._original_rgb = None
            self._pixmap_item = None
            self._scene.clear()
            self._selection_rect = None
            self._markers.clear()
            self._points.clear()
            self._annotations.clear()
            self._point_counter = 0
            return

        # Si ya había una imagen, calcular el factor de escala para ajustar los puntos y anotaciones existentes
        if self._image_rgb is not None:
            old_h, old_w = self._image_rgb.shape[:2]
            new_h, new_w = image_rgb.shape[:2]
            scale_x = new_w / old_w
            scale_y = new_h / old_h
            if scale_x != 1.0 or scale_y != 1.0:
                # Escalar marcadores de temperatura
                for pt in self._points:
                    pt.x = int(round(pt.x * scale_x))
                    pt.y = int(round(pt.y * scale_y))
                # Escalar anotaciones existentes
                for ann in self._annotations:
                    ann.x1 *= scale_x
                    ann.y1 *= scale_y
                    ann.x2 *= scale_x
                    ann.y2 *= scale_y

        self._image_rgb = image_rgb.copy()
        if is_original:
            self._original_rgb = image_rgb.copy()

        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        img_contiguous = np.ascontiguousarray(image_rgb)
        qimg = QImage(img_contiguous.data, w, h, bytes_per_line,
                      QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg.copy())

        self._scene.clear()
        self._selection_rect = None
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._markers.clear()

        # Re-dibujar puntos existentes
        for pt in self._points:
            self._add_marker_visual(pt)

        # Re-dibujar anotaciones existentes
        for ann in self._annotations:
            self._add_annotation_visual(ann)

        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = 1.0
        self.image_loaded.emit()

    def set_colorbar_selection_mode(self, enabled: bool):
        """Activa/desactiva el modo de selección de barra de colores."""
        self._selecting_colorbar = enabled
        if enabled:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self._draw_mode = "point"
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def set_draw_mode(self, mode: str):
        """Establece el modo de dibujo/anotación: 'point', 'rect', 'circle', 'text'."""
        self._draw_mode = mode
        self._selecting_colorbar = False
        if mode == "point":
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def set_annotation_color(self, color: QColor):
        """Establece el color de las nuevas anotaciones."""
        self._annotation_color = color

    def clear_points(self):
        """Elimina todos los puntos marcados."""
        for marker in self._markers:
            self._scene.removeItem(marker)
        self._markers.clear()
        self._points.clear()
        self._point_counter = 0

    def clear_annotations(self):
        """Elimina todas las anotaciones personalizadas."""
        for ann in self._annotations:
            if ann.graphics_item:
                try:
                    self._scene.removeItem(ann.graphics_item)
                except RuntimeError:
                    pass
        self._annotations.clear()

    def remove_point(self, index: int):
        """Elimina un punto por su índice."""
        for i, pt in enumerate(self._points):
            if pt.index == index:
                if i < len(self._markers):
                    self._scene.removeItem(self._markers[i])
                    self._markers.pop(i)
                self._points.pop(i)
                self.point_removed.emit(index)
                break

    def remove_annotation(self, ann: AnnotationItem):
        """Elimina una anotación personalizada."""
        if ann in self._annotations:
            if ann.graphics_item:
                try:
                    self._scene.removeItem(ann.graphics_item)
                except RuntimeError:
                    pass
            self._annotations.remove(ann)

    def get_points(self) -> list:
        """Retorna la lista de puntos marcados."""
        return self._points.copy()

    def set_show_marker_labels(self, show: bool):
        """Configura si se muestran los comentarios en las etiquetas del visor."""
        self._show_marker_labels = show
        self.refresh_markers()

    def refresh_markers(self):
        """Redibuja todos los marcadores en la escena para aplicar cambios de etiquetas o visibilidad."""
        for marker in self._markers:
            try:
                self._scene.removeItem(marker)
            except:
                pass
        self._markers.clear()
        
        for pt in self._points:
            self._add_marker_visual(pt)

    def update_point_label(self, index: int, label: str):
        """Actualiza la etiqueta (comentario) de un punto por su índice."""
        for pt in self._points:
            if pt.index == index:
                pt.label = label
                self.refresh_markers()
                break

    def get_annotations(self) -> list[AnnotationItem]:
        """Retorna la lista de anotaciones de figuras/texto."""
        return self._annotations.copy()

    def get_current_image(self) -> np.ndarray:
        """Retorna la imagen actualmente mostrada."""
        return self._image_rgb

    def get_original_image(self) -> np.ndarray:
        """Retorna la imagen original sin escalar."""
        return self._original_rgb

    # ── Eventos de ratón ──────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        """Zoom con rueda del ratón."""
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
            self._zoom_level *= factor
        else:
            self.scale(1.0 / factor, 1.0 / factor)
            self._zoom_level /= factor

    def mousePressEvent(self, event: QMouseEvent):
        """Manejo de clicks."""
        if event.button() == Qt.MouseButton.MiddleButton:
            # Pan con botón medio
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())

            if self._selecting_colorbar:
                self._selection_start = scene_pos
                if self._selection_rect:
                    try:
                        self._scene.removeItem(self._selection_rect)
                    except RuntimeError:
                        pass
                self._selection_rect = QGraphicsRectItem()
                self._selection_rect.setPen(QPen(QColor("#4CC9F0"), 2, Qt.PenStyle.DashLine))
                self._selection_rect.setBrush(QBrush(QColor(76, 201, 240, 40)))
                self._scene.addItem(self._selection_rect)
                event.accept()
                return

            # Manejo de dibujo interactivo
            if self._draw_mode in ("rect", "circle"):
                self._drawing_start = scene_pos
                ann = AnnotationItem(
                    type_=self._draw_mode,
                    x1=scene_pos.x(),
                    y1=scene_pos.y(),
                    x2=scene_pos.x(),
                    y2=scene_pos.y(),
                    color=self._annotation_color
                )
                self._add_annotation_visual(ann)
                self._annotations.append(ann)
                self._current_drawing_item = ann
                event.accept()
                return

            elif self._draw_mode == "text":
                text, ok = QInputDialog.getText(self, "Añadir Texto", "Introduce el texto de la anotación:")
                if ok and text:
                    ann = AnnotationItem(
                        type_="text",
                        x1=scene_pos.x(),
                        y1=scene_pos.y(),
                        x2=scene_pos.x(),
                        y2=scene_pos.y(),
                        text=text,
                        color=self._annotation_color
                    )
                    self._add_annotation_visual(ann)
                    self._annotations.append(ann)
                event.accept()
                return

            # Colocar marcador de temperatura (Modo normal)
            if self._draw_mode == "point" and self._pixmap_item and self._image_rgb is not None:
                x = int(scene_pos.x())
                y = int(scene_pos.y())
                h, w = self._image_rgb.shape[:2]

                if 0 <= x < w and 0 <= y < h:
                    rgb = tuple(int(c) for c in self._image_rgb[y, x])
                    temp = None
                    if self.analyzer and self.analyzer.is_calibrated():
                        temp = self.analyzer.get_temperature(rgb)

                    self._point_counter += 1
                    pt = ThermalPoint(
                        index=self._point_counter,
                        x=x, y=y, rgb=rgb,
                        temperature=temp
                    )
                    self._points.append(pt)
                    self._add_marker_visual(pt)
                    self.point_added.emit(pt)
                    event.accept()
                    return

        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Seguimiento del ratón para mostrar coordenadas o redimensionar figuras."""
        if self._panning and self._pan_start:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
            return

        if self._selecting_colorbar and self._selection_start and self._selection_rect:
            try:
                scene_pos = self.mapToScene(event.position().toPoint())
                rect = QRectF(self._selection_start, scene_pos).normalized()
                self._selection_rect.setRect(rect)
            except RuntimeError:
                pass
            event.accept()
            return

        # Redimensionar la figura que se está dibujando
        if self._current_drawing_item and self._drawing_start:
            scene_pos = self.mapToScene(event.position().toPoint())
            ann = self._current_drawing_item
            ann.x2 = scene_pos.x()
            ann.y2 = scene_pos.y()
            if ann.graphics_item:
                rect = QRectF(QPointF(ann.x1, ann.y1), QPointF(ann.x2, ann.y2)).normalized()
                ann.graphics_item.setRect(rect)
            event.accept()
            return

        # Emitir posición del cursor
        scene_pos = self.mapToScene(event.position().toPoint())
        if self._image_rgb is not None:
            x, y = int(scene_pos.x()), int(scene_pos.y())
            h, w = self._image_rgb.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                rgb = tuple(int(c) for c in self._image_rgb[y, x])
                self.mouse_moved.emit(x, y, rgb)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Finalizar pan, selección o dibujo."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            if self._selecting_colorbar:
                self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            elif self._draw_mode != "point":
                self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._current_drawing_item:
            self._current_drawing_item = None
            event.accept()
            return

        if (event.button() == Qt.MouseButton.LeftButton and
                self._selecting_colorbar and self._selection_start):
            scene_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._selection_start, scene_pos).normalized()

            x = max(0, int(rect.x()))
            y = max(0, int(rect.y()))
            w = max(1, int(rect.width()))
            h = max(1, int(rect.height()))

            self._selecting_colorbar = False
            self._selection_start = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

            self.colorbar_selected.emit((x, y, w, h))
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # ── Métodos internos ──────────────────────────────────

    def _add_marker_visual(self, pt: ThermalPoint):
        """Añade un marcador visual al scene."""
        show_lbl = getattr(self, "_show_marker_labels", True)
        marker = MarkerItem(pt.x, pt.y, pt.index, pt.temperature, pt.label, show_lbl)
        self._scene.addItem(marker)
        self._markers.append(marker)

    def _add_annotation_visual(self, ann: AnnotationItem):
        """Añade la representación visual de la anotación al scene."""
        if ann.type == "rect":
            item = QGraphicsRectItem()
            item.setPen(QPen(ann.color, 2))
            item.setBrush(QBrush(QColor(ann.color.red(), ann.color.green(), ann.color.blue(), 30)))
            item.setRect(QRectF(QPointF(ann.x1, ann.y1), QPointF(ann.x2, ann.y2)).normalized())
            self._scene.addItem(item)
            ann.graphics_item = item
        elif ann.type == "circle":
            item = QGraphicsEllipseItem()
            item.setPen(QPen(ann.color, 2))
            item.setBrush(QBrush(QColor(ann.color.red(), ann.color.green(), ann.color.blue(), 30)))
            item.setRect(QRectF(QPointF(ann.x1, ann.y1), QPointF(ann.x2, ann.y2)).normalized())
            self._scene.addItem(item)
            ann.graphics_item = item
        elif ann.type == "text":
            item = QGraphicsTextItem(ann.text)
            item.setDefaultTextColor(ann.color)
            font = QFont("Inter", 10, QFont.Weight.Bold)
            item.setFont(font)
            item.setPos(ann.x1, ann.y1)
            self._scene.addItem(item)
            ann.graphics_item = item

    def _show_context_menu(self, event):
        """Muestra menú contextual."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #1a1a2e; border: 1px solid #2a2a45; }
            QMenu::item { padding: 6px 20px; color: #e8e8f0; }
            QMenu::item:selected { background-color: #ff6b35; }
        """)

        scene_pos = self.mapToScene(event.position().toPoint())

        # Verificar si hay una anotación cerca
        nearby_ann = self._find_nearby_annotation(scene_pos.x(), scene_pos.y(), radius=15)
        if nearby_ann:
            act_remove_ann = menu.addAction("🗑 Eliminar anotación")
            act_remove_ann.triggered.connect(lambda: self.remove_annotation(nearby_ann))
            menu.addSeparator()

        # Verificar si hay un marcador de temperatura cerca
        nearby_pt = self._find_nearby_point(scene_pos.x(), scene_pos.y(), radius=15)
        if nearby_pt:
            act_remove = menu.addAction(
                f"🗑 Eliminar punto P{nearby_pt.index}")
            act_remove.triggered.connect(lambda: self.remove_point(nearby_pt.index))

        if self._points:
            menu.addSeparator()
            act_clear = menu.addAction("🗑 Eliminar todos los puntos")
            act_clear.triggered.connect(self.clear_points)

        if self._annotations:
            act_clear_ann = menu.addAction("🗑 Eliminar todas las anotaciones")
            act_clear_ann.triggered.connect(self.clear_annotations)

        act_fit = menu.addAction("🔍 Ajustar a ventana")
        act_fit.triggered.connect(lambda: self.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))

        if menu.actions():
            menu.exec(event.globalPosition().toPoint())

    def _find_nearby_point(self, x: float, y: float, radius: float = 10):
        """Busca un punto cercano a las coordenadas dadas."""
        for pt in self._points:
            dist = ((pt.x - x) ** 2 + (pt.y - y) ** 2) ** 0.5
            if dist <= radius:
                return pt
        return None

    def _find_nearby_annotation(self, x: float, y: float, radius: float = 15):
        """Busca una anotación cercana a las coordenadas dadas."""
        for ann in self._annotations:
            if ann.type in ("rect", "circle"):
                rect = QRectF(QPointF(ann.x1, ann.y1), QPointF(ann.x2, ann.y2)).normalized()
                if rect.contains(QPointF(x, y)) or rect.adjusted(-radius, -radius, radius, radius).contains(QPointF(x, y)):
                    return ann
            elif ann.type == "text":
                dist = ((ann.x1 - x) ** 2 + (ann.y1 - y) ** 2) ** 0.5
                if dist <= radius * 2:
                    return ann
        return None

    def recalculate_temperatures(self):
        """Recalcula temperaturas de todos los puntos con el analyzer actual."""
        if not self.analyzer or not self.analyzer.is_calibrated():
            return
        if self._image_rgb is None:
            return

        for pt in self._points:
            rgb = tuple(int(c) for c in self._image_rgb[pt.y, pt.x])
            pt.rgb = rgb
            pt.temperature = self.analyzer.get_temperature(rgb)

        # Redibujar marcadores
        for marker in self._markers:
            self._scene.removeItem(marker)
        self._markers.clear()
        for pt in self._points:
            self._add_marker_visual(pt)

    def load_project_data(self, points: list, annotations: list):
        """Carga puntos y anotaciones desde un proyecto guardado."""
        self.clear_points()
        self.clear_annotations()

        max_idx = 0

        # Cargar puntos
        for pt in points:
            self._points.append(pt)
            self._add_marker_visual(pt)
            max_idx = max(max_idx, pt.index)

        # Cargar anotaciones
        for ann in annotations:
            self._annotations.append(ann)
            self._add_annotation_visual(ann)

        self._point_counter = max_idx

