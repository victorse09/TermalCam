# Formato de Archivo TCP — ThermalCam Project (.tcp) - Versión 1.2

El formato **TCP (ThermalCam Project)** es la extensión de archivo propietaria utilizada por **ThermalCam Analyzer** para guardar y restaurar sesiones completas de análisis termográfico de manera eficiente y compacta. 

Físicamente, un archivo `.tcp` es un **contenedor comprimido ZIP** que encapsula datos de imágenes sin alterar, fotografías ópticas reales de referencia, logotipos corporativos y archivos de configuración estructurados en JSON.

---

## 1. Estructura Interna del Archivo (Versión 1.2 Multi-Medición)

Cuando un archivo con extensión `.tcp` se descomprime (usando cualquier descompresor ZIP estándar), revela la siguiente jerarquía de archivos:

```
mi_analisis.tcp (Archivo ZIP)
├── metadata.json                 # Índice estructurado central de la suite
├── project_logo.png              # (Opcional) Logotipo corporativo de la empresa
├── project_equipment.png         # (Opcional) Fotografía óptica del equipo bajo análisis
├── measurement_1_thermal.bmp     # Imagen térmica BMP original (240x240 RGB565) de la Medición 1
├── measurement_1_upscaler.png    # (Opcional) Imagen térmica suavizada/escalada de la Medición 1
├── measurement_1_real.png        # (Opcional) Fotografía óptica real de la Medición 1
├── measurement_2_thermal.bmp     # Imagen térmica BMP original de la Medición 2
└── ...
```

---

## 2. Especificación de `metadata.json`

El archivo `metadata.json` es el "cerebro" del proyecto. Contiene toda la información técnica asociada al análisis. A continuación se detalla su esquema y tipos de datos en la versión 1.2:

### Esquema Completo (`metadata.json`)

```json
{
  "project_version": "1.2",
  "project_info": {
    "title": "Informe de Análisis Térmico",
    "author": "Vito",
    "project_name": "Planta Norte - Subestación",
    "location": "Sala de Control A",
    "client": "Compresor Principal",
    "date": "2026-05-25",
    "time": "14:30:00",
    "ambient_temp": 22.5,
    "logo_path": "project_logo.png",
    "equipment_image_path": "project_equipment.png"
  },
  "instrument_info": {
    "brand": "Mastfuyi",
    "model": "FY8300",
    "serial_number": "MF-9830219"
  },
  "measurements": [
    {
      "name": "Caja de Fusibles",
      "distance": 1.5,
      "emissivity": 0.95,
      "observations": "Se observa un punto caliente en el fusible F3.",
      "thermal_file_name": "measurement_1_thermal.bmp",
      "upscaled_file_name": "measurement_1_upscaler.png",
      "real_file_name": "measurement_1_real.png",
      "calibration": {
        "is_calibrated": true,
        "t_min": 20.0,
        "t_max": 80.0,
        "colorbar_region": [220, 10, 10, 220]
      },
      "settings": {
        "upscale_method": "Lanczos (INTER_LANCZOS4)",
        "upscale_factor": "×3"
      },
      "marked_points": [
        {
          "index": 1,
          "x": 120,
          "y": 120,
          "rgb": [220, 45, 10],
          "temperature": 73.3,
          "label": "Fusible F3"
        }
      ],
      "annotations": [
        {
          "type": "rect",
          "x1": 50.0,
          "y1": 50.0,
          "x2": 150.0,
          "y2": 150.0,
          "text": "",
          "color": "#ff6b35"
        }
      ]
    }
  ]
}
```

---

## 3. Regla Crítica: Espacio de Coordenadas Normalizado

Para evitar fallos de desalineación o desbordamiento al abrir proyectos bajo diferentes factores de escala:
* **Todas las coordenadas vectoriales (`x`, `y`, `x1`, `y1`, `x2`, `y2`) almacenadas en `metadata.json` se guardan estrictamente en el espacio de coordenadas original de la imagen (240x240 píxeles)**.
* Si el usuario guarda el proyecto mientras visualiza la imagen escalada (ej. a 960x960), el software divide automáticamente todas las posiciones por el factor de escala activo antes de guardarlas en el JSON.
* Al cargar el proyecto, las figuras se cargan en el lienzo original y se **proyectan dinámicamente** multiplicándolas por el factor de escala correspondiente al inicializar el visor, eliminando cualquier desfase.
