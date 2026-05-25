#!/usr/bin/env python3
"""
ThermalCam Analyzer
Aplicación para análisis de imágenes térmicas de cámaras Mastfuyi.
Permite upscaling, medición de temperatura y generación de informes.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ThermalCam Analyzer")
    app.setOrganizationName("ThermalCam")

    # Fuente por defecto
    font = QFont("Inter", 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
