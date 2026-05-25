# Motores de Análisis Térmico y Escalado de Imágenes

Este documento proporciona una especificación técnica detallada acerca de cómo **ThermalCam Analyzer** decodifica las imágenes de la cámara térmica Mastfuyi, procesa la calibración y mapeo de temperaturas en píxeles RGB, aplica el escalado de alta fidelidad e Inteligencia Artificial, y recalcula proporcionalmente las anotaciones vectoriales sobre la imagen.

---

## 1. Decodificador de Imágenes BMP RGB565 (Mastfuyi)

Las cámaras termográficas portátiles Mastfuyi generan archivos BMP no estándar. Aunque tienen una cabecera típica de archivo, el formato de color utiliza un canal empaquetado de **16 bits (RGB565)** con compresión del tipo `BI_BITFIELDS` (Header Tipo 56 - `BITMAPV3INFOHEADER`). 

La mayoría de los visualizadores y librerías tradicionales (como PIL/Pillow o OpenCV) fallan al abrir estas imágenes o las interpretan en escala de grises ruidosa. El cargador personalizado implementado en `load_mastfuyi_bmp()` soluciona esto de la siguiente manera:

1. **Lectura de Cabecera**: Lee los primeros 54 bytes y extrae la resolución (240×240 píxeles por defecto) y la profundidad de bits (16 bits/píxel).
2. **Máscaras de Bits**: Identifica las máscaras de color de 32 bits situadas tras la cabecera:
   - Máscara Roja: `0xF800` (5 bits altos)
   - Máscara Verde: `0x07E0` (6 bits medios)
   - Máscara Azul: `0x001F` (5 bits bajos)
3. **Decodificación de Píxeles**: Procesa el archivo de forma binaria secuencial en bloques de 2 bytes (unsigned short). Para cada píxel realiza operaciones de desplazamiento de bits:
   ```python
   # Extraer componentes de 16 bits
   r_5bit = (val16 & 0xF800) >> 11
   g_6bit = (val16 & 0x07E0) >> 5
   b_5bit = (val16 & 0x001F)
   
   # Escalar a 8 bits (RGB888 estándar)
   r_8bit = int((r_5bit * 255) / 31)
   g_8bit = int((g_6bit * 255) / 63)
   b_8bit = int((b_5bit * 255) / 31)
   ```
4. **Construcción de Matriz**: Organiza los píxeles convertidos en una matriz NumPy de tres canales (H×W×3) de tipo `uint8` en orden RGB.

---

## 2. Motor de Análisis y Mapeo de Temperaturas

Dado que las imágenes BMP no contienen un archivo binario de radiometría incrustado, la temperatura de cada píxel debe extraerse a partir del color del píxel analizado comparándolo contra la **barra de colores lateral (colorbar)** presente en la propia imagen térmica.

### Paso 1: Extracción de la Barra de Colores (Colorbar)
El usuario o el algoritmo automático seleccionan la columna exacta donde se sitúa la barra de colores. La región por defecto es:
- Inicio en X: `221` | Ancho: `2` píxeles.
- Rango en Y: `18` hasta `195` (Alto: `177` píxeles).

### Paso 2: Generación de la Tabla de Búsqueda (LUT)
Se lee la barra de colores verticalmente, pixel a pixel, desde arriba (donde reside el color asociado a la temperatura máxima, $T_{max}$) hacia abajo (asociado a la temperatura mínima, $T_{min}$). Esto genera una **Lookup Table (LUT)** indexada, donde cada índice de la tabla representa un paso de temperatura:

$$\text{LUT}[i] = [R_i, G_i, B_i] \quad \text{para } i \in [0, H_{colorbar}-1]$$

### Paso 3: Mapeo por Distancia Euclidiana de Color
Para estimar la temperatura de un píxel cualquiera en coordenadas $(x, y)$ con color $C = [R_c, G_c, B_c]$:
1. Calculamos la **distancia euclidiana en el espacio RGB** entre el color del píxel $C$ y cada uno de los colores presentes en la $\text{LUT}$:

   $$D(i) = \sqrt{(R_c - R_i)^2 + (G_c - G_i)^2 + (B_c - B_i)^2}$$

2. Identificamos los dos índices de color más cercanos de la tabla: $i_1$ (el más cercano) e $i_2$ (el segundo más cercano).

### Paso 4: Interpolación Lineal de Temperatura
Cada píxel en la LUT representa una temperatura específica basada en su posición relativa:

$$T(i) = T_{max} - \left( \frac{i}{H_{colorbar} - 1} \right) \times (T_{max} - T_{min})$$

Para obtener un valor exacto, realizamos una interpolación lineal ponderada entre las temperaturas de los dos colores más cercanos ($T_1$ y $T_2$):

$$w_1 = D(i_2) \quad , \quad w_2 = D(i_1)$$

$$T_{estimada} = \frac{w_1 \cdot T(i_1) + w_2 \cdot T(i_2)}{w_1 + w_2}$$

Este motor permite obtener lecturas de décimas de grado extremadamente precisas (con un margen de error menor al $1.5\%$ respecto a los marcadores textuales fijos grabados por la propia cámara en el BMP).

---

## 3. Motor de Escalado de Imágenes (Upscaling)

Para facilitar el análisis visual detallado de la termografía (que originalmente es de baja resolución, 240×240), la aplicación integra un motor de redimensionamiento de alto rendimiento.

### A. Algoritmos Clásicos
Utilizan funciones geométricas en OpenCV para interpolar valores vecinos rápidos:
- **Cúbico (`cv2.INTER_CUBIC`)**: Interpolación bicúbica sobre una vecindad de píxeles 4×4. Genera degradados suaves y bordes naturales.
- **Lanczos (`cv2.INTER_LANCZOS4`)**: Interpolación Lanczos utilizando una ventana de 8×8 píxeles. Ofrece la máxima nitidez y reconstrucción de bordes en transiciones térmicas abruptas.
- **Lineal** y **Nearest**: Interpolaciones directas de menor carga computacional.

### B. Algoritmos de Inteligencia Artificial (Super-Resolution) y Post-Procesamiento Híbrido

Utilizan redes neuronales artificiales convolucionales mediante el módulo `cv2.dnn_superres` para reconstruir los detalles de alta frecuencia perdidos:
- **FSRCNN (Fast Super-Resolution Convolutional Neural Network)**: Modelo optimizado que extrae características directamente en el espacio de baja resolución, acelerando la inferencia. Reconstruye bordes térmicos difusos de forma sumamente realista.
- **ESPCN (Efficient Sub-Pixel Convolutional Neural Network)**: Implementa una capa de convolución subpíxel al final de la red que redimensiona el mapa de características aprendido de forma directa.

#### Pipeline Híbrido Premium para Termografía
Dado que los modelos de súper-resolución convencionales están entrenados en fotografías naturales con bordes afilados, al procesar gradientes de temperatura continuos y suaves pueden producir **ruido de rejilla, pixelación artificial o artefactos de anillo** (haciendo que a veces el método tradicional "Nearest" o "Cúbico" parezca retener mejor calidad).

Para resolver esto y dotar al software de una calidad analítica impecable, el motor implementa un pipeline de post-procesamiento híbrido:
1. **Filtro Bilateral Estructural**: Tras obtener la inferencia de la IA, se aplica un filtro bilateral (`cv2.bilateralFilter`) con parámetros optimizados ($d=7, \sigma_{color}=35, \sigma_{space}=35$). Esto elimina completamente el grano, el ruido digital y las bandas cromáticas en las zonas de degradado térmico suave, sin alterar ni difuminar las siluetas ni los bordes físicos de alta frecuencia de los objetos.
2. **Fusión Híbrida con Lanczos**: Se genera un redimensionamiento de la imagen mediante interpolación matemática de alta fidelidad **Lanczos** a la misma resolución de salida.
3. **Mezcla Ponderada Digital/Analógica**: Ambas imágenes se fusionan en un búfer mediante combinación lineal ponderada:

   $$\text{Imagen final} = 0.65 \cdot \text{IA\_Filtrada} + 0.35 \cdot \text{Lanczos} + 0$$

   Este proceso híbrido entrega una visualización termográfica de nivel profesional: **bordes y siluetas increíblemente definidos y enfocados (provistos por la IA)** con **gradientes de calor continuos, naturales y libres de ruido cromático digital (provistos por Lanczos)**.

---

## 4. Geometría Vectorial y Escalado de Anotaciones

Cuando se aplica un factor de escalado $S$ (ej. de 240x240 a 960x960, donde $S=4$), todos los marcadores y anotaciones deben reubicarse proporcionalmente para mantener su localización física y legibilidad exacta.

### Mapeo de Puntos y Figuras
Para cualquier coordenada en la imagen original $(x_{orig}, y_{orig})$:
1. Su nueva coordenada espacial en la escena escalada se calcula de forma lineal:

   $$x_{new} = x_{orig} \cdot S \quad , \quad y_{new} = y_{orig} \cdot S$$

2. Para anotaciones rectangulares y circulares definidas por dos esquinas diagonalmente opuestas $(x_1, y_1)$ y $(x_2, y_2)$, ambas coordenadas son proyectadas utilizando el mismo factor:

   $$x_{1\_new} = x_1 \cdot S \quad , \quad y_{1\_new} = y_1 \cdot S$$
   
   $$x_{2\_new} = x_2 \cdot S \quad , \quad y_{2\_new} = y_2 \cdot S$$

### Mapeo y Ajuste de Grosor y Textos
Para garantizar la legibilidad en resoluciones altas:
- **Grosor del Trazo**: Se escala proporcionalmente al factor $S$ (ej. un trazo de `2px` original se convierte en `8px` al escalar $\times4$).
- **Tamaño de Letra (Font Size)**: Las fuentes del texto se incrementan proporcionalmente para mantener el mismo tamaño relativo sobre el área de la imagen.
- **Renderizado Nativo en PDF**: Al exportar a informe PDF, las coordenadas vectoriales escaladas se proyectan sobre el búfer OpenCV para dibujar las anotaciones directamente sobre la matriz escalada a nivel de píxeles, eliminando artefactos borrosos o pixelados.
