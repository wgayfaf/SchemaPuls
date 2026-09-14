@echo off
chcp 65001 >nul
echo ========================================================
echo   SchemaPulse - 启动独立前端服务 (Port: 3000)
echo ========================================================
cd /d "%~dp0\.."
python frontend\run.py
pause
