"""
ThermalCam Analyzer — Diálogo de Generación de Informe PDF
Genera informes profesionales con imágenes térmicas y datos de medición.
"""

import os
import tempfile
import numpy as np
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QCheckBox, QFormLayout, QToolButton
)
from .thermal_analyzer import ThermalPoint


class ReportDialog(QDialog):
    """Diálogo para configurar y generar un informe PDF."""

    def __init__(self, image_rgb: np.ndarray, upscaled_rgb: np.ndarray,
                 points: list, t_min: float, t_max: float,
                 histogram_widget=None, filename: str = "",
                 current_size: tuple = None, annotations: list = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Informe PDF")
        self.setMinimumSize(500, 550)
        self._image_rgb = image_rgb
        self._upscaled_rgb = upscaled_rgb
        self._points = points
        self._t_min = t_min
        self._t_max = t_max
        self._histogram_widget = histogram_widget
        self._filename = filename
        self._current_size = current_size or (image_rgb.shape[:2] if image_rgb is not None else (240, 240))
        self._annotations = annotations or []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Información del informe
        info_group = QGroupBox("Información del Informe")
        form = QFormLayout(info_group)

        self.edit_title = QLineEdit("Informe de Análisis Térmico")
        self.edit_title.setPlaceholderText("Título del informe")
        form.addRow("Título:", self.edit_title)

        self.edit_author = QLineEdit()
        self.edit_author.setPlaceholderText("Nombre del autor")
        form.addRow("Autor:", self.edit_author)

        self.edit_project = QLineEdit()
        self.edit_project.setPlaceholderText("Nombre del proyecto")
        form.addRow("Proyecto:", self.edit_project)

        self.edit_location = QLineEdit()
        self.edit_location.setPlaceholderText("Ubicación de la medición")
        form.addRow("Ubicación:", self.edit_location)

        self.edit_equipment = QLineEdit()
        self.edit_equipment.setPlaceholderText("Equipo medido o equipo utilizado")
        form.addRow("Equipo:", self.edit_equipment)

        # Logo layout
        logo_layout = QHBoxLayout()
        self.edit_logo = QLineEdit()
        self.edit_logo.setPlaceholderText("Ruta del logo de la empresa (opcional)")
        btn_logo = QToolButton()
        btn_logo.setText("...")
        btn_logo.clicked.connect(lambda: self._browse_image(self.edit_logo))
        logo_layout.addWidget(self.edit_logo)
        logo_layout.addWidget(btn_logo)
        form.addRow("Logo:", logo_layout)

        layout.addWidget(info_group)

        # Observaciones
        obs_group = QGroupBox("Observaciones")
        obs_layout = QVBoxLayout(obs_group)
        self.text_observations = QTextEdit()
        self.text_observations.setPlaceholderText(
            "Escriba sus observaciones y notas sobre la medición...")
        self.text_observations.setMaximumHeight(120)
        obs_layout.addWidget(self.text_observations)
        layout.addWidget(obs_group)

        # Contenido
        content_group = QGroupBox("Contenido del Informe")
        content_layout = QVBoxLayout(content_group)

        self.chk_original = QCheckBox("Incluir imagen original")
        self.chk_original.setChecked(True)
        content_layout.addWidget(self.chk_original)

        # Imagen real layout
        real_img_layout = QHBoxLayout()
        self.chk_real_img = QCheckBox("Incluir imagen óptica (real)")
        self.chk_real_img.setChecked(False)
        self.edit_real_img = QLineEdit()
        self.edit_real_img.setPlaceholderText("Ruta de la imagen óptica")
        self.edit_real_img.setEnabled(False)
        self.chk_real_img.toggled.connect(self.edit_real_img.setEnabled)
        btn_real_img = QToolButton()
        btn_real_img.setText("...")
        btn_real_img.clicked.connect(lambda: self._browse_image(self.edit_real_img))
        
        real_img_layout.addWidget(self.chk_real_img)
        real_img_layout.addWidget(self.edit_real_img)
        real_img_layout.addWidget(btn_real_img)
        content_layout.addLayout(real_img_layout)

        self.chk_upscaled = QCheckBox("Incluir imagen escalada")
        self.chk_upscaled.setChecked(self._upscaled_rgb is not None)
        self.chk_upscaled.setEnabled(self._upscaled_rgb is not None)
        content_layout.addWidget(self.chk_upscaled)

        self.chk_points = QCheckBox(
            f"Incluir tabla de puntos ({len(self._points)} puntos)")
        self.chk_points.setChecked(len(self._points) > 0)
        self.chk_points.setEnabled(len(self._points) > 0)
        content_layout.addWidget(self.chk_points)

        self.chk_histogram = QCheckBox("Incluir histograma")
        self.chk_histogram.setChecked(self._histogram_widget is not None)
        self.chk_histogram.setEnabled(self._histogram_widget is not None)
        content_layout.addWidget(self.chk_histogram)

        layout.addWidget(content_group)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("Generar PDF")
        self.btn_generate.setObjectName("btnPrimary")
        self.btn_generate.setMinimumHeight(40)
        font = self.btn_generate.font()
        font.setPointSize(13)
        font.setBold(True)
        self.btn_generate.setFont(font)
        self.btn_generate.clicked.connect(self._generate_report)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_generate)
        layout.addLayout(btn_layout)

    def _browse_image(self, line_edit: QLineEdit):
        """Abre un diálogo para seleccionar una imagen."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos (*)")
        if filepath:
            line_edit.setText(filepath)

    def _generate_report(self):
        """Genera el informe PDF."""
        # Verificar que fpdf2 esté instalado
        try:
            from fpdf import FPDF  # noqa: F401
        except ImportError:
            QMessageBox.critical(
                self, "Dependencia Faltante",
                "El paquete 'fpdf2' no está instalado.\n\n"
                "Instálalo ejecutando:\n"
                "  pip install fpdf2\n\n"
                "Luego reinicia la aplicación.")
            return

        # Seleccionar ruta de guardado
        default_name = f"informe_termico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Guardar Informe PDF", default_name,
            "PDF Files (*.pdf)")

        if not filepath:
            return

        try:
            self._build_pdf(filepath)
            QMessageBox.information(
                self, "Éxito",
                f"Informe generado exitosamente:\n{filepath}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Error al generar el informe:\n{str(e)}")

    def _build_pdf(self, filepath: str):
        """Construye el PDF con fpdf2."""
        from fpdf import FPDF
        from PIL import Image

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Encabezado ─────────────────────────────────────
        pdf.set_fill_color(30, 30, 50)
        pdf.rect(0, 0, 210, 35, 'F')

        # Insertar logo si existe
        logo_path = self.edit_logo.text().strip()
        if logo_path and os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=10, y=5, h=25)
            except Exception as e:
                print(f"Error cargando logo: {e}")

        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(255, 107, 53)
        pdf.set_y(8)
        pdf.cell(0, 10, self.edit_title.text() or "Informe de Análisis Térmico",
                 align='C', new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(180, 180, 200)
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        subtitle_parts = [f"Fecha: {date_str}"]
        if self.edit_author.text():
            subtitle_parts.append(f"Autor: {self.edit_author.text()}")
        pdf.cell(0, 6, " | ".join(subtitle_parts),
                 align='C', new_x="LMARGIN", new_y="NEXT")

        pdf.set_y(40)
        pdf.set_text_color(40, 40, 60)

        # ── Información del proyecto ─────────────────────────
        if self.edit_project.text() or self.edit_location.text() or self.edit_equipment.text():
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(255, 107, 53)
            pdf.cell(0, 8, "Información del Proyecto",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(255, 107, 53)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 60)
            if self.edit_project.text():
                pdf.cell(0, 6, f"Proyecto: {self.edit_project.text()}",
                         new_x="LMARGIN", new_y="NEXT")
            if self.edit_location.text():
                pdf.cell(0, 6, f"Ubicación: {self.edit_location.text()}",
                         new_x="LMARGIN", new_y="NEXT")
            if self.edit_equipment.text():
                pdf.cell(0, 6, f"Equipo: {self.edit_equipment.text()}",
                         new_x="LMARGIN", new_y="NEXT")
            if self._filename:
                pdf.cell(0, 6, f"Archivo: {self._filename}",
                         new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6,
                     f"Rango de temperatura: {self._t_min:.1f}°C - {self._t_max:.1f}°C",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # ── Imágenes ──────────────────────────────────────────
        tmp_files = []
        try:
            if self.chk_original.isChecked() and self._image_rgb is not None:
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Imagen Térmica Original",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                tmp_orig = self._save_temp_image(self._image_rgb, "original")
                tmp_files.append(tmp_orig)
                h, w = self._image_rgb.shape[:2]
                img_w = min(120, 190)
                img_h = img_w * h / w
                pdf.image(tmp_orig, x=45, w=img_w)
                pdf.ln(4)

                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 120)
                pdf.cell(0, 5, f"Resolución: {w}×{h} px",
                         align='C', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)
                
            real_img_path = self.edit_real_img.text().strip()
            if self.chk_real_img.isChecked() and real_img_path and os.path.exists(real_img_path):
                if pdf.get_y() > 200:
                    pdf.add_page()

                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Imagen Óptica (Real)",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                try:
                    from PIL import Image
                    with Image.open(real_img_path) as img:
                        w, h = img.size
                        img_w = min(120, 190)
                        img_h = img_w * h / w
                    pdf.image(real_img_path, x=45, w=img_w)
                    pdf.ln(4)
                    
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(100, 100, 120)
                    pdf.cell(0, 5, f"Resolución: {w}×{h} px",
                             align='C', new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(4)
                except Exception as e:
                    print(f"Error cargando imagen real: {e}")

            if (self.chk_upscaled.isChecked() and
                    self._upscaled_rgb is not None):
                if pdf.get_y() > 200:
                    pdf.add_page()

                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Imagen Térmica Escalada",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                # Si el checkbox de puntos está activo, dibujar marcadores y anotaciones sobre la imagen escalada antes de guardarla
                img_up_to_render = self._upscaled_rgb
                if self.chk_points.isChecked():
                    if self._points:
                        img_up_to_render = self._draw_markers_on_array(img_up_to_render, self._points, self._current_size)
                    if self._annotations:
                        img_up_to_render = self._draw_annotations_on_array(img_up_to_render, self._annotations, self._current_size)

                tmp_up = self._save_temp_image(img_up_to_render, "upscaled")
                tmp_files.append(tmp_up)
                h, w = self._upscaled_rgb.shape[:2]
                img_w = min(160, 190)
                img_h = img_w * h / w
                pdf.image(tmp_up, x=25, w=img_w)
                pdf.ln(4)

                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 120)
                pdf.cell(0, 5, f"Resolución escalada: {w}×{h} px",
                         align='C', new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)

            # ── Tabla de puntos ────────────────────────────────
            if self.chk_points.isChecked() and self._points:
                if pdf.get_y() > 220:
                    pdf.add_page()

                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Puntos de Medición",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                # Header
                col_widths = [20, 30, 30, 50, 40]
                headers = ["#", "X", "Y", "RGB", "T° (°C)"]

                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(30, 30, 50)
                pdf.set_text_color(255, 200, 160)
                for i, (header, w) in enumerate(zip(headers, col_widths)):
                    pdf.cell(w, 8, header, border=1, fill=True, align='C')
                pdf.ln()

                # Rows
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 60)
                for pt in self._points:
                    temp_str = (f"{pt.temperature:.1f}"
                                if pt.temperature is not None else "---")
                    rgb_str = f"({pt.rgb[0]},{pt.rgb[1]},{pt.rgb[2]})"
                    row = [f"P{pt.index}", str(pt.x), str(pt.y),
                           rgb_str, temp_str]
                    for val, w in zip(row, col_widths):
                        pdf.cell(w, 7, val, border=1, align='C')
                    pdf.ln()
                pdf.ln(4)

            # ── Histograma ──────────────────────────────────────
            if (self.chk_histogram.isChecked() and
                    self._histogram_widget is not None):
                if pdf.get_y() > 180:
                    pdf.add_page()

                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Histograma de Intensidad",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                tmp_hist = os.path.join(tempfile.gettempdir(),
                                        "thermalcam_histogram.png")
                self._histogram_widget.save_histogram(tmp_hist, dpi=150)
                tmp_files.append(tmp_hist)
                pdf.image(tmp_hist, x=15, w=180)
                pdf.ln(4)

            # ── Observaciones ─────────────────────────────────
            observations = self.text_observations.toPlainText().strip()
            if observations:
                if pdf.get_y() > 230:
                    pdf.add_page()

                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Observaciones",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)

                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 60)
                pdf.multi_cell(0, 6, observations)
                pdf.ln(4)

            # ── Footer ───────────────────────────────────────
            pdf.set_y(-25)
            pdf.set_draw_color(200, 200, 210)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 150, 170)
            pdf.cell(0, 5,
                     f"Generado por ThermalCam Analyzer - {date_str}",
                     align='C')

            pdf.output(filepath)

        finally:
            # Limpiar archivos temporales
            for tmp in tmp_files:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass

    def _save_temp_image(self, image_rgb: np.ndarray, prefix: str) -> str:
        """Guarda una imagen temporal como PNG para insertar en el PDF."""
        from PIL import Image
        tmp_path = os.path.join(tempfile.gettempdir(),
                                f"thermalcam_{prefix}.png")
        pil_img = Image.fromarray(image_rgb)
        pil_img.save(tmp_path, "PNG")
        return tmp_path

    def _draw_markers_on_array(self, image_rgb: np.ndarray, points: list, current_size: tuple) -> np.ndarray:
        """Dibuja los puntos de medición directamente sobre el array RGB usando OpenCV."""
        import cv2
        img = image_rgb.copy()
        h_target, w_target = img.shape[:2]
        h_curr, w_curr = current_size

        # Tamaño de escala para dibujar según la resolución del destino
        scale_factor = w_target / 240.0
        size = int(max(6, round(6 * scale_factor)))
        thickness = int(max(1, round(1.5 * scale_factor)))
        font_scale = 0.35 * scale_factor

        for pt in points:
            # Calcular la posición en la resolución destino
            x_norm = pt.x / w_curr
            y_norm = pt.y / h_curr
            x = int(round(x_norm * w_target))
            y = int(round(y_norm * h_target))

            color_circle = (255, 107, 53)  # Naranja
            color_cross = (255, 215, 0)   # Oro
            color_text = (255, 255, 255)  # Blanco
            color_bg = (15, 15, 26)       # Oscuro

            # Dibujar elementos gráficos
            cv2.circle(img, (x, y), size, color_circle, thickness)
            cv2.line(img, (x - int(size * 1.5), y), (x + int(size * 1.5), y), color_cross, int(max(1, thickness - 1)))
            cv2.line(img, (x, y - int(size * 1.5)), (x, y + int(size * 1.5)), color_cross, int(max(1, thickness - 1)))

            # Etiqueta de texto (P1: 75.9°C)
            temp_str = f"{pt.temperature:.1f}C" if pt.temperature is not None else "---"
            label_text = f"P{pt.index}: {temp_str}"

            (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, int(max(1, thickness - 1)))

            # Posición arriba-derecha
            tx = x + size + int(4 * scale_factor)
            ty = y - size - int(4 * scale_factor)

            # Evitar desbordamiento por la derecha o arriba
            if tx + tw > w_target:
                tx = x - size - tw - int(4 * scale_factor)
            if ty - th < 0:
                ty = y + size + th + int(10 * scale_factor)

            cv2.rectangle(img, (tx - 2, ty - th - 2), (tx + tw + 2, ty + baseline + 2), color_bg, -1)
            cv2.rectangle(img, (tx - 2, ty - th - 2), (tx + tw + 2, ty + baseline + 2), color_circle, 1)
            cv2.putText(img, label_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color_text, int(max(1, thickness - 1)), cv2.LINE_AA)

        return img

    def _draw_annotations_on_array(self, image_rgb: np.ndarray, annotations: list, current_size: tuple) -> np.ndarray:
        """Dibuja las anotaciones personalizadas (rectángulos, círculos, textos) sobre el array RGB."""
        import cv2
        img = image_rgb.copy()
        h_target, w_target = img.shape[:2]
        h_curr, w_curr = current_size

        scale_factor = w_target / 240.0
        thickness = int(max(1, round(2 * scale_factor)))
        font_scale = 0.45 * scale_factor

        for ann in annotations:
            # Escalar coordenadas a la resolución de la imagen de salida
            x1_norm = ann.x1 / w_curr
            y1_norm = ann.y1 / h_curr
            x1 = int(round(x1_norm * w_target))
            y1 = int(round(y1_norm * h_target))

            x2_norm = ann.x2 / w_curr
            y2_norm = ann.y2 / h_curr
            x2 = int(round(x2_norm * w_target))
            y2 = int(round(y2_norm * h_target))

            # Obtener el color en formato RGB
            color = (ann.color.red(), ann.color.green(), ann.color.blue())

            if ann.type == "rect":
                # Dibujar rectángulo exterior
                cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
                # Dibujar relleno translúcido
                overlay = img.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

            elif ann.type == "circle":
                # Calcular centro y radio
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                rx = abs(x2 - x1) / 2
                ry = abs(y2 - y1) / 2
                radius = int(max(rx, ry))
                cv2.circle(img, (cx, cy), radius, color, thickness)
                # Relleno translúcido
                overlay = img.copy()
                cv2.circle(overlay, (cx, cy), radius, color, -1)
                cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

            elif ann.type == "text":
                (tw, th), baseline = cv2.getTextSize(ann.text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                # Dibujar rectángulo de fondo oscuro para que resalte
                color_bg = (15, 15, 26)
                cv2.rectangle(img, (x1 - 2, y1 - th - 2), (x1 + tw + 2, y1 + baseline + 2), color_bg, -1)
                cv2.rectangle(img, (x1 - 2, y1 - th - 2), (x1 + tw + 2, y1 + baseline + 2), color, 1)
                cv2.putText(img, ann.text, (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        return img
