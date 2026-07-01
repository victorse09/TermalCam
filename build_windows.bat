@echo off
:: =====================================================================
:: ThermalCam Analyzer - Windows Build Script
:: Genera la versión ejecutable para Windows 10 (ThermalCam1_5)
:: =====================================================================
title ThermalCam Analyzer - Compilador Windows v1.5

echo.
echo =====================================================================
echo  Iniciando proceso de compilación para ThermalCam Analyzer v1.5
echo =====================================================================
echo.

:: 1. Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado en este sistema o no se encuentra en el PATH.
    echo Por favor, instala Python 3.8+ y marca la casilla "Add Python to PATH" durante la instalación.
    pause
    exit /b 1
)

:: 2. Instalar dependencias necesarias
echo [1/4] Instalando dependencias de requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Hubo un problema al instalar algunas dependencias. Intentando continuar...
)

:: 3. Instalar PyInstaller
echo [2/4] Instalando PyInstaller para generación del ejecutable...
python -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo instalar PyInstaller.
    pause
    exit /b 1
)

:: 4. Compilar aplicación con PyInstaller en modo carpeta unificada (onedir)
:: Esto mantiene las carpetas "resources" y "models" en la raíz del ejecutable,
:: permitiendo que las hojas de estilo QSS carguen los iconos correctamente a nivel de OS.
echo [3/4] Compilando la aplicación con PyInstaller...
python -m PyInstaller --noconfirm --onedir --windowed --name="ThermalCam1_5" ^
    --add-data "resources;resources" ^
    --add-data "models;models" ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] Falló la compilación de la aplicación.
    pause
    exit /b 1
)

:: Copiar recursos y modelos a la raíz de la carpeta de distribución para compatibilidad con rutas relativas
echo [4/4] Copiando recursos y modelos a la raíz del directorio de distribución...
xcopy /E /I /Y "resources" "dist\ThermalCam1_5\resources"
xcopy /E /I /Y "models" "dist\ThermalCam1_5\models"

if %errorlevel% neq 0 (
    echo [WARNING] No se pudieron copiar algunos recursos a la raíz de la carpeta dist.
)

:: 5. Finalizado
echo.
echo =====================================================================
echo  ¡Compilación completada exitosamente!
echo =====================================================================
echo.
echo El ejecutable y todos sus recursos se han generado en la carpeta:
echo   dist\ThermalCam1_5\
echo.
echo Para ejecutar la aplicación en tu oficina con Windows 10:
echo 1. Copia la carpeta completa "dist\ThermalCam1_5" a tu equipo.
echo 2. Abre la carpeta y ejecuta "ThermalCam1_5.exe".
echo.
echo Nota: No separes el archivo "ThermalCam1_5.exe" de su carpeta,
echo ya que depende de las bibliotecas y recursos incluidos en ella.
echo.
pause
