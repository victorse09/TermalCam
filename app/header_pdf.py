import os
from fpdf import FPDF

class HeaderPDF(FPDF):
    def __init__(self, format_val="a4", version_str="v1.5"):
        super().__init__(format=format_val)
        self.version_str = version_str
        
    def footer(self):
        self.set_y(-15)
        self.set_draw_color(200, 200, 210)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(2)
        
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 140)
        
        self.cell(self.w - 40, 5, f"ThermalCam Analyzer - Suite de Inspección Multi-Medición {self.version_str}", align='L')
        self.cell(0, 5, f"Página {self.page_no()}", align='R')

def generate_header_pdf(filepath: str, project_info: dict, header_info: dict, lightness: float = 0.0, format_val: str = "letter", show_signature: bool = False):
    """Genera un documento PDF de cabecera independiente."""
    
    pdf = HeaderPDF(format_val=format_val, version_str="v1.5")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # ── 1. ENCABEZADO CORPORATIVO PREMIUM ──────────────────────────────────
    r = int(22 + (240 - 22) * lightness)
    g = int(22 + (240 - 22) * lightness)
    b = int(40 + (240 - 40) * lightness)
    
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, pdf.w, 65, 'F')
    
    # Dibujar línea naranja decorativa
    pdf.set_fill_color(255, 107, 53)
    pdf.rect(0, 65, pdf.w, 4, 'F')

    # Renderizar logotipo si existe
    logo_path = project_info.get("logo_path", "")
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=15, y=15, h=20)
        except Exception as e:
            print(f"Error cargando logo en cabecera: {e}")

    # Título y Subtítulo
    pdf.set_y(42)
    pdf.set_font("Helvetica", "B", 24)
    if sum((r, g, b)) / 3 > 180:
        pdf.set_text_color(40, 40, 50)
    else:
        pdf.set_text_color(255, 255, 255)
        
    title = project_info.get("title", "Informe de Inspección Térmica")
    pdf.cell(0, 10, title, align='L', new_x="LMARGIN", new_y="NEXT")

    # ── 2. METADATOS EN EL ORDEN SOLICITADO ────────────────────────────────
    # Orden: Cliente, Informe, Proyecto, Autor/Analista, Fecha, Referencia
    pdf.set_y(78)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(0, 10, "Detalles", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(255, 107, 53)
    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
    pdf.ln(6)

    # Formatear la fecha a DD-MM-YYYY
    raw_date = header_info.get("fecha", "---")
    if raw_date != "---" and "-" in raw_date:
        parts = raw_date.split("-")
        if len(parts) == 3:
            raw_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

    # Tabla de metadatos
    metadata_rows = [
        ("Cliente:", header_info.get("cliente", "---")),
        ("Informe:", header_info.get("informe", "---")),
        ("Proyecto:", project_info.get("project_name", "---")),
        ("Autor / Analista:", project_info.get("author", "---")),
        ("Fecha:", raw_date),
        ("Referencia:", header_info.get("referencia", "---")),
    ]
    
    for label, val in metadata_rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(60, 60, 70)
        pdf.cell(45, 6, label)
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 50)
        pdf.cell(0, 6, str(val), new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(10)
    
    # ── 3. CONTENIDO (TEXTO) ────────────────────────────────────────────────
    contenido = header_info.get("contenido", "").strip()
    if contenido:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 107, 53)
        pdf.cell(0, 10, "Contenido", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(255, 107, 53)
        pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
        pdf.ln(6)
        
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(40, 40, 50)
        # Usar multi_cell para respetar saltos de línea y ajustar al ancho
        pdf.multi_cell(0, 6, contenido)

    # ── 4. FIRMA DEL AUTOR ──────────────────────────────────────────────────
    if show_signature:
        sig_path = project_info.get("signature_path", "")
        if sig_path and os.path.exists(sig_path):
            from PIL import Image
            
            author_name = project_info.get("author", "---")
            label_text = f"Analista - {author_name}"
            
            pdf.set_font("Helvetica", "B", 9)
            text_w = pdf.get_string_width(label_text)
            
            # Ancho de firma no supera el ancho del texto de la firma (entre 35 y 55 mm)
            sig_w = min(55, max(35, text_w))
            
            if pdf.get_y() > pdf.h - 55:
                pdf.add_page()
            
            sig_x = pdf.w - 15 - sig_w
            sig_y = pdf.h - 45
            
            try:
                with Image.open(sig_path) as sig_img:
                    sw, sh = sig_img.size
                aspect = sh / sw
                actual_h = sig_w * aspect
                if actual_h > 20: # limitar alto a 20mm
                    actual_h = 20
                    actual_w = actual_h / aspect
                    sig_x_adjusted = sig_x + (sig_w - actual_w) / 2
                else:
                    actual_w = sig_w
                    sig_x_adjusted = sig_x
                
                pdf.image(sig_path, x=sig_x_adjusted, y=sig_y, w=actual_w, h=actual_h)
                
                pdf.set_y(sig_y + actual_h + 2)
                pdf.set_x(pdf.w - 15 - text_w)
                pdf.set_text_color(50, 50, 60)
                pdf.cell(text_w, 5, label_text, align='C')
            except Exception as e:
                print(f"Error al dibujar la firma en PDF de cabecera: {e}")

    pdf.output(filepath)
