"""
ThermalCam Analyzer — Estilos QSS
Tema oscuro profesional con acentos térmicos.
"""

# Paleta de colores
COLORS = {
    "bg_primary": "#0f0f1a",
    "bg_secondary": "#1a1a2e",
    "bg_tertiary": "#252540",
    "bg_card": "#1e1e35",
    "bg_input": "#141428",
    "accent_hot": "#ff6b35",
    "accent_warm": "#e63946",
    "accent_cool": "#4cc9f0",
    "accent_highlight": "#ff8c42",
    "text_primary": "#e8e8f0",
    "text_secondary": "#8888a0",
    "text_muted": "#555570",
    "border": "#2a2a45",
    "border_focus": "#ff6b35",
    "success": "#06d6a0",
    "warning": "#ffd166",
    "scrollbar_bg": "#1a1a2e",
    "scrollbar_handle": "#3a3a55",
}

DARK_THEME = f"""
/* ===== Global ===== */
QMainWindow, QDialog {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}}

QWidget {{
    color: {COLORS['text_primary']};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
}}

/* ===== Menu Bar ===== */
QMenuBar {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 2px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_tertiary']};
}}

QMenu {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent_hot']};
    color: white;
}}

/* ===== Tool Bar ===== */
QToolBar {{
    background-color: {COLORS['bg_secondary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px;
    spacing: 6px;
}}

QToolButton {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}

QToolButton:hover {{
    background-color: {COLORS['bg_tertiary']};
    border: 1px solid {COLORS['border']};
}}

QToolButton:pressed {{
    background-color: {COLORS['accent_hot']};
    color: white;
}}

/* ===== Labels ===== */
QLabel {{
    color: {COLORS['text_primary']};
}}

QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS['accent_hot']};
    padding: 4px 0;
}}

/* ===== Group Box ===== */
QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 10px 10px 10px;
    font-weight: bold;
    color: {COLORS['accent_hot']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: {COLORS['accent_hot']};
}}

/* ===== Inputs ===== */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent_hot']};
}}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['border_focus']};
}}

QDoubleSpinBox, QSpinBox {{
    padding-right: 24px;
}}

/* ===== SpinBox Buttons and Arrows ===== */
QDoubleSpinBox::up-button, QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {COLORS['border']};
    border-bottom: 0.5px solid {COLORS['border']};
    background-color: {COLORS['bg_secondary']};
    border-top-right-radius: 6px;
}}

QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {{
    background-color: {COLORS['accent_hot']};
}}

QDoubleSpinBox::up-button:pressed, QSpinBox::up-button:pressed {{
    background-color: {COLORS['accent_warm']};
}}

QDoubleSpinBox::down-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid {COLORS['border']};
    border-top: 0.5px solid {COLORS['border']};
    background-color: {COLORS['bg_secondary']};
    border-bottom-right-radius: 6px;
}}

QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS['accent_hot']};
}}

QDoubleSpinBox::down-button:pressed, QSpinBox::down-button:pressed {{
    background-color: {COLORS['accent_warm']};
}}

QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{
    image: url(resources/icons/up_arrow.svg);
    width: 10px;
    height: 10px;
}}

QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
    image: url(resources/icons/down_arrow.svg);
    width: 10px;
    height: 10px;
}}

QComboBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLORS['text_primary']};
    min-width: 100px;
}}

QComboBox:hover {{
    border: 1px solid {COLORS['accent_hot']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent_hot']};
    color: {COLORS['text_primary']};
}}

/* ===== Buttons ===== */
QPushButton {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_hot']};
    color: white;
    border: 1px solid {COLORS['accent_hot']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_warm']};
}}

QPushButton#btnPrimary {{
    background-color: {COLORS['accent_hot']};
    color: white;
    border: none;
}}

QPushButton#btnPrimary:hover {{
    background-color: {COLORS['accent_highlight']};
}}

QPushButton#btnDanger {{
    background-color: {COLORS['accent_warm']};
    color: white;
    border: none;
}}

/* ===== Table ===== */
QTableWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['accent_hot']};
    alternate-background-color: {COLORS['bg_tertiary']};
}}

QTableWidget::item {{
    padding: 4px 8px;
    color: {COLORS['text_primary']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['accent_hot']};
    border: 1px solid {COLORS['border']};
    padding: 6px;
    font-weight: bold;
}}

/* ===== Scroll Bars ===== */
QScrollBar:vertical {{
    background: {COLORS['scrollbar_bg']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['scrollbar_handle']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_hot']};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {COLORS['scrollbar_bg']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['scrollbar_handle']};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['accent_hot']};
}}

/* ===== Status Bar ===== */
QStatusBar {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 12px;
}}

QStatusBar::item {{
    border: none;
}}

/* ===== Splitter ===== */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* ===== Dock Widget ===== */
QDockWidget {{
    color: {COLORS['text_primary']};
    titlebar-close-icon: none;
}}

QDockWidget::title {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    padding: 6px;
    font-weight: bold;
}}

/* ===== Text Edit ===== */
QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent_hot']};
}}

/* ===== Progress Bar ===== */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    color: {COLORS['text_primary']};
    height: 20px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent_warm']},
        stop:1 {COLORS['accent_hot']});
    border-radius: 5px;
}}

/* ===== Tab Widget ===== */
QTabWidget::pane {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['accent_hot']};
    border-bottom: 2px solid {COLORS['accent_hot']};
}}

/* ===== Graphics View ===== */
QGraphicsView {{
    background-color: {COLORS['bg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}

/* ===== Sidebar Panel & Scroll Area ===== */
QWidget#sidebarPanel, QWidget#sidebarContainer {{
    background-color: {COLORS['bg_primary']};
}}

QScrollArea, QScrollArea > QWidget, QScrollArea::viewport {{
    background-color: {COLORS['bg_primary']};
    border: none;
}}
"""
