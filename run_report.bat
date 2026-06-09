@echo off
chcp 65001 >nul
set ROOT=D:\otkat\Grand Theft Auto V
python "%~dp0gibdd_points.py" --root "%ROOT%" --include-root-files
pause
