# 📸 ThermalCam Analyzer

**ThermalCam Analyzer** es un software profesional de escritorio multiplataforma diseñado específicamente para la decodificación, visualización, mejora de resolución mediante Inteligencia Artificial y análisis térmico cuantitativo de imágenes capturadas con cámaras térmicas (como la **Mastfuyi** y similares).

Este software ha sido optimizado y cuenta con un tema oscuro moderno de alta fidelidad, herramientas interactivas de anotación y un generador de informes en PDF automático.

---

## 🚀 Características Clave

* **🔌 Decodificador Personalizado BMP RGB565**: Permite abrir y parsear imágenes BMP térmicas Mastfuyi de 16-bits (con cabecera tipo 56 `BITMAPV3INFOHEADER`), un formato crudo propietario no estándar que los visores comunes, OpenCV o PIL no logran abrir.
* **⚡ Mapeo Térmico y Auto-Calibración**:
  * Entrada manual o automática de rangos de temperatura mínima y máxima.
  * Extracción inteligente de barra de color (*trimming*) recortando bordes inútiles para una precisión absoluta.
  * Estimación de temperatura en tiempo real al hacer clic en cualquier píxel de la imagen.
* **⬆️ Súper-Resolución (IA & Interpolación)**:
  * Escalado clásico (Cúbico, Lanczos).
  * Escalado inteligente basado en Inteligencia Artificial mediante modelos **FSRCNN** y **ESPCN** (factores x2, x3 y x4) para recuperar bordes nítidos sin alterar la calibración de temperatura.
* **✏️ Suite de Anotación y Edición Gráfica**:
  * Colocación ilimitada de **puntos de medición de temperatura** con etiquetas automáticas (`P1`, `P2`, etc.).
  * Dibujo interactivo de **rectángulos (recuadros)** y **círculos** con rellenos translúcidos.
  * Inserción de **notas de texto** personalizadas en cualquier coordenada.
  * Selector integrado de color de alto contraste en la barra de herramientas para evitar que las marcaciones se mezclen con el fondo térmico.
  * Ajuste y escalado vectorial inteligente de todos los dibujos si se cambia la resolución de la imagen.
* **📊 Histograma Térmico en Tiempo Real**: Análisis de la distribución de colores e intensidad térmica de la imagen en un histograma Matplotlib integrado.
* **📄 Generador de Informes PDF Profesionales**:
  * Exporta informes con logo de la empresa, título, observaciones personalizadas, lugar del equipo y tabla con la lista de puntos de temperatura analizados.
  * Incluye la opción de adjuntar una foto de referencia real (óptica).
  * **Imagen limpia vs. anotada**: La imagen térmica original se incluye en su estado natural limpio, mientras que la sección de imagen escalada de alta resolución plasma todas las anotaciones y marcaciones para un informe impecable.
* **🔥 Marca e Identidad Premium**: Icono oficial integrado y diálogo "Acerca de" completamente personalizado.

---

## 🛠️ Estructura del Proyecto

```text
termalcam/
├── main.py                      # Punto de entrada de la aplicación
├── requirements.txt             # Dependencias del sistema
├── README.md                    # Este archivo de documentación
├── resources/
│   ├── logo.png                 # Logotipo premium de la aplicación
│   └── icons/                   # Suite de iconos SVG de alto contraste
│       ├── camera.svg           # Captura/cámara
│       ├── circle.svg           # Herramienta Círculo
│       ├── color.svg            # Selector de color
│       ├── rect.svg             # Herramienta Rectángulo
│       ├── text.svg             # Herramienta Texto
│       ├── target.svg           # Herramienta Puntos
│       └── ...
├── app/
│   ├── thermal_analyzer.py      # Motor de decodificación BMP y calibrador de LUT térmica
│   ├── upscaler.py              # Backend de escalado clásica e inferencia de super-resolución por IA
│   ├── image_viewer.py          # Visor interactivo (QGraphicsView) de marcadores y dibujos vectoriales
│   ├── histogram_widget.py      # Histograma integrado con Matplotlib
│   ├── sidebar_panel.py         # Panel de control lateral para calibración y configuraciones
│   ├── report_dialog.py         # Diálogo configurador y motor de renderizado de informes PDF
│   ├── main_window.py           # Ventana principal e integración de la suite gráfica
│   └── styles.py                # Estilo QSS premium (Tema oscuro moderno)
└── models/                      # Modelos de redes neuronales (descargados automáticamente)
```

---

## 📦 Requisitos e Instalación

Para ejecutar este software, asegúrate de tener instalado **Python 3.8+** en tu sistema.

1. **Clona el repositorio** o descarga los archivos en una carpeta local:
   ```bash
   git clone <url-de-tu-repositorio>
   cd termalcam
   ```

2. **Instala las dependencias necesarias** mediante `pip`:
   ```bash
   pip install -r requirements.txt
   ```
   *Nota: Las dependencias principales son `PyQt6`, `opencv-python`, `numpy`, `matplotlib`, `pillow` y `fpdf2`.*

---

## 🖥️ Cómo Ejecutar la Aplicación

Para iniciar la interfaz gráfica del programa, simplemente ejecuta el archivo `main.py` desde la terminal:

```bash
python3 main.py
```

---

## 📖 Guía Básica de Uso

1. **Cargar Imagen**: Utiliza el botón **📂** en la barra de herramientas o el atajo `Ctrl + O` para cargar tu imagen térmica BMP original.
2. **Auto-Calibración**: Introduce los valores de temperatura mínima y máxima impresos en tu imagen térmica original en la sección lateral, y pulsa **⚡ Auto-Cal**. El software extraerá automáticamente la barra de color y calibrará la escala de temperatura al instante.
3. **Analizar y Dibujar**:
   * Selecciona el modo **Puntos (🎯)** y haz clic sobre la imagen para colocar termopares virtuales.
   * Utiliza las herramientas de **Rectángulo (⬜)** y **Círculo (◯)** para marcar zonas específicas.
   * Utiliza la herramienta de **Texto (🔤)** para agregar aclaraciones.
   * Utiliza el selector de **Color (🎨)** para destacar tus marcas sobre fondos claros u oscuros.
4. **Mejora de Resolución (Upscaling)**: Selecciona un método en el panel lateral (ej. Lanczos o modelos neuronales como FSRCNN) junto a un factor de escala (x2, x3 o x4) y pulsa **Aplicar Upscale** para obtener una imagen térmica nítida de alta resolución.
5. **Generar Informe**: Haz clic en el botón de **Informe (📄)** en la barra de herramientas o presiona `Ctrl + P`. Rellena los datos de tu empresa, agrega observaciones y observaciones y expórtalo en un PDF estructurado.

---

## 🤝 Créditos y Comunidad

**ThermalCam Analyzer** ha sido desarrollado con ❤️.

* **Desarrollador principal**: Vito
* **Comunidad**: Creado especialmente para la **comunidad Naseriana**.

---
*Este proyecto está bajo la licencia MIT. Siente libre de reportar bugs, sugerir mejoras o contribuir al código.*
