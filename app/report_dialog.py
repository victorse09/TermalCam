"""
ThermalCam Analyzer — Diálogo de Generación de Informe PDF Multipágina
Genera informes profesionales y consolidados con todas las mediciones, imágenes térmicas, fotos reales e histogramas.
"""

import os
import tempfile
import numpy as np
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTextEdit, QPushButton, QFileDialog,
    QMessageBox, QCheckBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QComboBox
)
from .thermal_analyzer import ThermalPoint, ThermalAnalyzer
from .image_viewer import AnnotationItem


class ReportDialog(QDialog):
    """Diálogo para configurar y generar un informe PDF multipágina consolidado."""

    def __init__(self, project_info: dict, instrument_info: dict,
                 measurements: list, histogram_widget=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar Informe PDF Consolidado")
        self.setMinimumSize(520, 480)
        self._project_info = project_info
        self._instrument_info = instrument_info
        self._measurements = measurements
        self._histogram_widget = histogram_widget
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Resumen del Proyecto y Cliente (Lectura)
        proj_group = QGroupBox("Resumen del Proyecto")
        form = QFormLayout(proj_group)
        
        lbl_title = QLabel(self._project_info.get("title", "Informe de Análisis Térmico"))
        lbl_title.setStyleSheet("font-weight: bold; color: #ff6b35;")
        form.addRow("Título:", lbl_title)
        
        lbl_client = QLabel(self._project_info.get("client", "---"))
        form.addRow("Cliente/Equipo:", lbl_client)
        
        lbl_proj = QLabel(self._project_info.get("project_name", "---"))
        form.addRow("Proyecto:", lbl_proj)
        
        lbl_author = QLabel(self._project_info.get("author", "---"))
        form.addRow("Autor/Analista:", lbl_author)

        lbl_meas_count = QLabel(f"{len([m for m in self._measurements if m.get('original_image') is not None])} medición(es) con imagen")
        form.addRow("Mediciones:", lbl_meas_count)
        
        layout.addWidget(proj_group)

        # 2. Opciones del Contenido del Informe
        content_group = QGroupBox("Configuración del Contenido")
        content_layout = QVBoxLayout(content_group)
        content_layout.setSpacing(8)

        self.chk_cover = QCheckBox("Incluir portada corporativa premium")
        self.chk_cover.setChecked(True)
        content_layout.addWidget(self.chk_cover)

        self.chk_instrument = QCheckBox("Incluir datos de instrumentación y cámara")
        self.chk_instrument.setChecked(True)
        content_layout.addWidget(self.chk_instrument)

        self.chk_original = QCheckBox("Incluir imagen térmica original")
        self.chk_original.setChecked(True)
        content_layout.addWidget(self.chk_original)

        self.chk_real_img = QCheckBox("Incluir fotos ópticas reales (si están cargadas)")
        self.chk_real_img.setChecked(True)
        content_layout.addWidget(self.chk_real_img)

        self.chk_upscaled = QCheckBox("Incluir imagen escalada de alta resolución con dibujos")
        self.chk_upscaled.setChecked(True)
        content_layout.addWidget(self.chk_upscaled)

        self.chk_points = QCheckBox("Incluir tablas detalladas de puntos medidos")
        self.chk_points.setChecked(True)
        content_layout.addWidget(self.chk_points)

        self.chk_histogram = QCheckBox("Incluir gráficos de histograma de temperatura")
        self.chk_histogram.setChecked(True)
        content_layout.addWidget(self.chk_histogram)

        layout.addWidget(content_group)

        # 3. Formato de Página
        format_group = QGroupBox("Formato de Página")
        format_layout = QHBoxLayout(format_group)
        format_layout.setContentsMargins(10, 8, 10, 8)
        
        lbl_format = QLabel("Tamaño de Papel:")
        lbl_format.setStyleSheet("font-weight: bold; color: #a0a0b0;")
        format_layout.addWidget(lbl_format)
        
        self.combo_format = QComboBox()
        self.combo_format.addItem("A4 (Estándar - 210x297 mm)", "a4")
        self.combo_format.addItem("Carta (Letter - 215.9x279.4 mm)", "letter")
        self.combo_format.addItem("Oficio (Legal - 215.9x355.6 mm)", "legal")
        format_layout.addWidget(self.combo_format)
        
        layout.addWidget(format_group)

        # Botones de Acción
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("Generar Informe PDF")
        self.btn_generate.setObjectName("btnPrimary")
        self.btn_generate.setMinimumHeight(40)
        font = self.btn_generate.font()
        font.setPointSize(12)
        font.setBold(True)
        self.btn_generate.setFont(font)
        self.btn_generate.clicked.connect(self._generate_report)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_generate)
        layout.addLayout(btn_layout)

        # Cargar estilos
        if self.parent() and hasattr(self.parent(), 'styleSheet'):
            self.setStyleSheet(self.parent().styleSheet())

    def _generate_report(self):
        """Genera el informe PDF multipágina."""
        # Verificar fpdf2
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

        default_name = f"informe_inspeccion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Guardar Informe PDF", default_name,
            "Archivos PDF (*.pdf)")

        if not filepath:
            return

        try:
            self._build_pdf(filepath, self.combo_format.currentData())
            QMessageBox.information(
                self, "Éxito",
                f"Informe multipágina generado exitosamente:\n{filepath}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Error al generar el informe consolidado:\n{str(e)}")

    def _build_pdf(self, filepath: str, format_str: str = "a4"):
        """Construye el PDF multipágina usando FPDF2."""
        from fpdf import FPDF
        from PIL import Image

        class ThermalReportPDF(FPDF):
            def __init__(self, project_info: dict, version_str: str = "v1.1", has_cover: bool = True, format_val: str = "a4"):
                super().__init__(format=format_val)
                self._project_info = project_info
                self.version_str = version_str
                self.has_cover = has_cover

            def footer(self):
                self.set_y(-15)
                self.set_draw_color(200, 200, 210)
                self.line(10, self.get_y(), self.w - 10, self.get_y())
                self.ln(2)
                
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(120, 120, 140)
                
                # Nombre de la suite + versión v1.1
                self.cell(self.w - 40, 5, f"ThermalCam Analyzer - Suite de Inspección Multi-Medición {self.version_str}", align='L')
                # Número de página sin fecha
                self.cell(0, 5, f"Página {self.page_no()}", align='R')

        pdf = ThermalReportPDF(self._project_info, version_str="v1.1", has_cover=self.chk_cover.isChecked(), format_val=format_str)
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Archivos temporales para limpiar al final
        tmp_files = []

        # ── 1. PORTADA CORPORATIVA ──────────────────────────────────────────
        if self.chk_cover.isChecked():
            pdf.add_page()
            
            # Encabezado corporativo premium (Bloque superior azul oscuro más angosto)
            pdf.set_fill_color(22, 22, 40)
            pdf.rect(0, 0, pdf.w, 65, 'F')
            
            # Dibujar línea naranja decorativa
            pdf.set_fill_color(255, 107, 53)
            pdf.rect(0, 65, pdf.w, 4, 'F')

            # Renderizar logotipo si existe
            logo_path = self._project_info.get("logo_path", "")
            if logo_path and os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, x=15, y=15, h=20)
                except Exception as e:
                    print(f"Error cargando logo en portada: {e}")

            # Título y Subtítulo
            pdf.set_y(42)
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, self._project_info.get("title", "Informe de Inspección Térmica"),
                     align='L', new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("Helvetica", "I", 12)
            pdf.set_text_color(180, 180, 200)
            pdf.cell(0, 8, "Inspección Termográfica Cuantitativa de Alta Resolución",
                     align='L', new_x="LMARGIN", new_y="NEXT")

            # Espaciado para el bloque de metadatos (ajustado hacia arriba por el encabezado angosto)
            pdf.set_y(78)
            pdf.set_text_color(40, 40, 50)
            
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(255, 107, 53)
            pdf.cell(0, 10, "Detalles del Informe y Cliente", new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(255, 107, 53)
            pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(6)

            # Tabla de metadatos en portada
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(60, 60, 70)
            
            metadata_rows = [
                ("Cliente / Equipo:", self._project_info.get("client", "---")),
                ("Proyecto / Planta:", self._project_info.get("project_name", "---")),
                ("Ubicación Física:", self._project_info.get("location", "---")),
                ("Autor / Analista:", self._project_info.get("author", "---")),
                ("Fecha de Medición:", self._project_info.get("date", "---")),
                ("Hora de Medición:", self._project_info.get("time", "---")),
                ("Temp. Ambiente:", f"{self._project_info.get('ambient_temp', 20.0):.1f} °C"),
                ("Informe:", self._project_info.get("report_number", "---")),
            ]
            
            for label, val in metadata_rows:
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(45, 6, label)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 6, str(val), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)

            # Mostrar foto del equipo en portada si existe
            equip_path = self._project_info.get("equipment_image_path", "")
            if equip_path and os.path.exists(equip_path):
                try:
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.set_text_color(255, 107, 53)
                    pdf.cell(0, 8, "Equipo / Instalación Bajo Análisis", new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)
                    
                    # Cargar dimensiones para redimensionar de forma responsiva
                    with Image.open(equip_path) as img:
                        w, h = img.size
                    img_w = min(110, 190)
                    img_h = img_w * h / w
                    
                    pdf.image(equip_path, x=(pdf.w - img_w) / 2, w=img_w, h=img_h)
                except Exception as e:
                    print(f"Error cargando imagen del equipo en portada: {e}")

        # ── 2. INSTRUMENTACIÓN Y RESUMEN ────────────────────────────────────
        if self.chk_instrument.isChecked():
            pdf.add_page()
            
            # Encabezado de página
            self._write_page_header(pdf, "Resumen e Instrumentación")

            # Instrumento
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(255, 107, 53)
            pdf.cell(0, 8, "Especificaciones de la Cámara Térmica", new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(255, 107, 53)
            pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(4)

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(60, 60, 70)
            
            inst_rows = [
                ("Marca del Instrumento:", self._instrument_info.get("brand", "Mastfuyi")),
                ("Modelo del Instrumento:", self._instrument_info.get("model", "---")),
                ("Número de Serie:", self._instrument_info.get("serial_number", "---")),
            ]
            for label, val in inst_rows:
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(50, 6, label)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 6, str(val), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)

            # Resumen de mediciones
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(255, 107, 53)
            pdf.cell(0, 8, "Índice de Mediciones del Proyecto", new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(255, 107, 53)
            pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(4)

            # Header tabla resumen
            col_widths = [15, 60, 25, 25, 20, 45]
            headers = ["#", "Nombre Medición", "Distancia", "Emisividad", "Puntos", "Estado"]
            
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(22, 22, 40)
            pdf.set_text_color(255, 255, 255)
            for header, w in zip(headers, col_widths):
                pdf.cell(w, 8, header, border=1, fill=True, align='C')
            pdf.ln()

            # Rellenar filas
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 50)
            valid_meas = [m for m in self._measurements if m.get("original_image") is not None]
            
            for idx, m in enumerate(valid_meas):
                status_str = "Analizada" if m["points"] else "Sin puntos"
                row = [
                    str(idx + 1),
                    m["name"],
                    f"{m['distance']:.1f} m",
                    f"{m['emissivity']:.2f}",
                    str(len(m["points"])),
                    status_str
                ]
                for val, w in zip(row, col_widths):
                    pdf.cell(w, 7, val, border=1, align='C')
                pdf.ln()

            # Observaciones Generales del Proyecto
            general_obs = self._project_info.get("general_observations", "").strip()
            if general_obs:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 8, "Observaciones Generales del Proyecto", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 50)
                pdf.multi_cell(0, 6, general_obs)

        # ── 3. DETALLE POR MEDICIÓN ─────────────────────────────────────────
        fig_counter = 1
        valid_meas = [m for m in self._measurements if m.get("original_image") is not None]
        for idx, m in enumerate(valid_meas):
            obs_printed = False
            pdf.add_page()
            
            # Encabezado
            self._write_page_header(pdf, f"Medición {idx + 1}: {m['name']}")

            # Parámetros técnicos
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(255, 107, 53)
            pdf.cell(0, 6, "Parámetros Técnicos de Medición", new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(255, 107, 53)
            pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(3)

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(60, 60, 70)
            pdf.cell(30, 5, "Distancia:")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(40, 5, f"{m['distance']:.1f} m")
            
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(30, 5, "Emisividad:")
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(40, 5, f"{m['emissivity']:.2f}")
            
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(30, 5, "Rango Calibración:")
            pdf.set_font("Helvetica", "", 9)
            cal_range = f"{m['calibration']['t_min']:.1f}°C - {m['calibration']['t_max']:.1f}°C" if m['calibration']['is_calibrated'] else "Sin Calibrar"
            pdf.cell(0, 5, cal_range, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

            # IMÁGENES APILADAS Y CENTRADAS (Térmica original vs Foto real óptica)
            y_before_images = pdf.get_y()
            
            # Cargar imagen térmica original
            has_orig = self.chk_original.isChecked()
            has_real = self.chk_real_img.isChecked() and m["real_image_path"] and os.path.exists(m["real_image_path"])

            if has_orig or has_real:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 6, "Referencias Visuales de Campo", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                # Si tenemos ambas, las dibujamos apiladas verticalmente y centradas
                if has_orig and has_real:
                    img_w = 75
                    x_pos = (pdf.w - img_w) / 2
                    
                    # 1. Imagen térmica original
                    tmp_t = self._save_temp_image(m["original_image"], f"orig_{idx}")
                    tmp_files.append(tmp_t)
                    pdf.image(tmp_t, x=x_pos, w=img_w, h=img_w)
                    pdf.ln(1.5) # FPDF2 ya avanzó y por el alto, solo bajamos 1.5mm para el texto
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(100, 100, 110)
                    pdf.cell(0, 4, f"Fig {fig_counter} : Imagen Termográfica", align='C', new_x="LMARGIN", new_y="NEXT")
                    fig_counter += 1
                    pdf.ln(1.5)
                    
                    # 2. Imagen real visible
                    try:
                        with Image.open(m["real_image_path"]) as img:
                            w, h = img.size
                        real_h = img_w * h / w
                        if real_h > 75:
                            real_h = 75
                        
                        pdf.image(m["real_image_path"], x=x_pos, w=img_w, h=real_h)
                        pdf.ln(1.5) # FPDF2 ya avanzó y por el alto, solo bajamos 1.5mm para el texto
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.set_text_color(100, 100, 110)
                        pdf.cell(0, 4, f"Fig {fig_counter} : Imagen Real", align='C', new_x="LMARGIN", new_y="NEXT")
                        fig_counter += 1
                        pdf.ln(2)
                    except Exception as e:
                        print(f"Error cargando foto real: {e}")
                else:
                    # Dibujar solo la que esté disponible al centro
                    img_w = 90
                    x_pos = (pdf.w - img_w) / 2
                    if has_orig:
                        tmp_t = self._save_temp_image(m["original_image"], f"orig_{idx}")
                        tmp_files.append(tmp_t)
                        pdf.image(tmp_t, x=x_pos, w=img_w, h=img_w)
                        pdf.ln(1.5) # FPDF2 ya avanzó y por el alto, solo bajamos 1.5mm para el texto
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.set_text_color(100, 100, 110)
                        pdf.cell(0, 4, f"Fig {fig_counter} : Imagen Termográfica", align='C', new_x="LMARGIN", new_y="NEXT")
                        fig_counter += 1
                        pdf.ln(2)
                    elif has_real:
                        try:
                            with Image.open(m["real_image_path"]) as img:
                                w, h = img.size
                            real_h = img_w * h / w
                            pdf.image(m["real_image_path"], x=x_pos, w=img_w, h=real_h)
                            pdf.ln(1.5) # FPDF2 ya avanzó y por el alto, solo bajamos 1.5mm para el texto
                            pdf.set_font("Helvetica", "I", 9)
                            pdf.set_text_color(100, 100, 110)
                            pdf.cell(0, 4, f"Fig {fig_counter} : Imagen Real", align='C', new_x="LMARGIN", new_y="NEXT")
                            fig_counter += 1
                            pdf.ln(2)
                        except Exception as e:
                            print(f"Error cargando foto real: {e}")

            # IMAGEN ESCALADA CON DIBUJOS Y ANOTACIONES
            if self.chk_upscaled.isChecked():
                # Forzar salto de página para la imagen de alta resolución anotada
                pdf.add_page()
                self._write_page_header(pdf, f"Medición {idx + 1} - Análisis Gráfico")

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 6, "Termografía Escalada con Marcadores de Medición", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                # Renderizar dibujos y puntos directamente sobre la imagen escalada activa
                img_up_to_render = m["current_image"].copy()
                oh, ow = m["original_image"].shape[:2]
                ch, cw = img_up_to_render.shape[:2]
                current_size = (ch, cw)

                if m["points"]:
                    img_up_to_render = self._draw_markers_on_array(img_up_to_render, m["points"], current_size)
                if m["annotations"]:
                    img_up_to_render = self._draw_annotations_on_array(img_up_to_render, m["annotations"], current_size)

                tmp_up = self._save_temp_image(img_up_to_render, f"upscaled_{idx}")
                tmp_files.append(tmp_up)

                # Dibujar al centro
                w_disp = 120
                h_disp = w_disp * ch / cw
                pdf.image(tmp_up, x=(pdf.w - w_disp) / 2, w=w_disp, h=h_disp)
                pdf.ln(1.5) # FPDF2 ya avanzó y por el alto, solo bajamos 1.5mm para el texto
                
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 110)
                method_used = m["settings"]["upscale_method"]
                factor_used = m["settings"]["upscale_factor"]
                pdf.cell(0, 4, f"Fig {fig_counter} : Imagen con Super-resolución ({method_used} {factor_used}) - {cw}x{ch} px", align='C', new_x="LMARGIN", new_y="NEXT")
                fig_counter += 1
                pdf.ln(4)

                # OBSERVACIONES (Añadido abajo de la imagen en la misma página del análisis gráfico)
                obs_text = m["observations"].strip()
                if obs_text:
                    pdf.ln(2)
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.set_text_color(255, 107, 53)
                    pdf.cell(0, 6, "Observaciones y Notas de Inspección de Campo", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_draw_color(255, 107, 53)
                    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                    pdf.ln(4)

                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(40, 40, 50)
                    pdf.multi_cell(0, 5, obs_text)
                    pdf.ln(4)
                    obs_printed = True

            # TABLA DE PUNTOS MEDIDOS
            if self.chk_points.isChecked() and m["points"]:
                # Si nos queda poco espacio vertical, hacemos salto de página
                if pdf.get_y() > 200:
                    pdf.add_page()
                    self._write_page_header(pdf, f"Medición {idx + 1} - Datos Numéricos")

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 6, f"Tabla de Puntos de Temperatura Medidos ({len(m['points'])} puntos)", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                col_widths_pt = [20, 25, 25, 45, 35, 40]
                headers_pt = ["Punto", "X (orig)", "Y (orig)", "Valor RGB", "Temp. (°C)", "Comentario"]

                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(22, 22, 40)
                pdf.set_text_color(255, 255, 255)
                for header, w in zip(headers_pt, col_widths_pt):
                    pdf.cell(w, 7, header, border=1, fill=True, align='C')
                pdf.ln()

                # Filas
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 50)
                
                # Calcular factor de escala para mostrar coordenadas de pixeles en espacio 240x240
                scale_f = cw / ow
                
                for pt in m["points"]:
                    x_240 = int(round(pt.x / scale_f))
                    y_240 = int(round(pt.y / scale_f))
                    temp_str = f"{pt.temperature:.1f} °C" if pt.temperature is not None else "---"
                    rgb_str = f"({pt.rgb[0]},{pt.rgb[1]},{pt.rgb[2]})"
                    row = [
                        f"P{pt.index}",
                        str(x_240),
                        str(y_240),
                        rgb_str,
                        temp_str,
                        pt.label or "---"
                    ]
                    for val, w in zip(row, col_widths_pt):
                        pdf.cell(w, 6, val, border=1, align='C')
                    pdf.ln()
                pdf.ln(6)

            # HISTOGRAMA DE TEMPERATURA
            if self.chk_histogram.isChecked() and self._histogram_widget is not None:
                if pdf.get_y() > 180:
                    pdf.add_page()
                    self._write_page_header(pdf, f"Medición {idx + 1} - Análisis Estadístico")

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 6, "Distribución y Frecuencia de Intensidad Térmica (Histograma)", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                tmp_hist = os.path.join(tempfile.gettempdir(), f"temp_{idx}_hist.png")
                # Forzar el histograma a renderizar los datos numéricos de la imagen de esta medición
                self._histogram_widget.save_histogram_for_data(tmp_hist, m["current_image"], m["points"], dpi=120)
                tmp_files.append(tmp_hist)

                # Reducir a la mitad la altura del histograma en el PDF y centrar dinámicamente
                pdf.image(tmp_hist, x=(pdf.w - 160) / 2, w=160, h=32.5)
                pdf.ln(3.0) # FPDF2 ya avanzó y por el alto, solo bajamos 3mm para la separación

            # OBSERVACIONES (Si no se imprimieron antes, por ejemplo si chk_upscaled estaba desactivado)
            obs_text = m["observations"].strip()
            if obs_text and not obs_printed:
                if pdf.get_y() > 210:
                    pdf.add_page()
                    self._write_page_header(pdf, f"Medición {idx + 1} - Observaciones")

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 107, 53)
                pdf.cell(0, 6, "Observaciones y Notas de Inspección de Campo", new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(255, 107, 53)
                pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
                pdf.ln(4)

                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 50)
                pdf.multi_cell(0, 6, obs_text)
                pdf.ln(4)

        # ── 4. EXPORTAR PDF FINAL ───────────────────────────────────────────
        pdf.output(filepath)

        # ── 5. LIMPIEZA DE TEMPORALES ──────────────────────────────────────
        for tmp in tmp_files:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception as e:
                print(f"Error al remover temporal de reporte: {e}")

    def _write_page_header(self, pdf, section_title: str):
        """Dibuja un encabezado estandarizado en la parte superior de cada página de reporte."""
        pdf.set_fill_color(22, 22, 40)
        pdf.rect(0, 0, pdf.w, 22, 'F')
        
        pdf.set_fill_color(255, 107, 53)
        pdf.rect(0, 22, pdf.w, 1.5, 'F')

        # Logotipo a escala en esquina
        logo_path = self._project_info.get("logo_path", "")
        if logo_path and os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=10, y=3, h=16)
            except:
                pass

        pdf.set_y(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, section_title, align='R')
        pdf.set_y(28)
        pdf.ln(2)

    def _save_temp_image(self, image_rgb: np.ndarray, prefix: str) -> str:
        """Guarda un array de imagen temporal como archivo PNG para insertar en el PDF."""
        from PIL import Image
        tmp_path = os.path.join(tempfile.gettempdir(), f"report_{prefix}.png")
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
