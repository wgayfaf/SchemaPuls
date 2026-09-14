@echo off
chcp 65001 >nul
echo ========================================================
echo   SchemaPulse - 启动后端 API 服务 (Port: 8000)
echo ========================================================
cd /d "%~dp0\.."
python backend\run.py
pause
