@echo off
cd /d "%~dp0"
if "%MI_SCALE_MAC%"=="" (
    echo Defina a variavel de ambiente MI_SCALE_MAC com o endereco da sua
    echo balanca, ou edite este arquivo para passar --mac AA:BB:CC:DD:EE:FF
    echo diretamente na linha abaixo.
    pause
    exit /b 1
)
python mi_scale_reader.py --upload
echo.
pause
