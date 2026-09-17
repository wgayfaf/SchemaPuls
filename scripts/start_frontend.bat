@echo off
chcp 65001 >nul
echo ========================================================
echo   SchemaPulse - 启动前端 Vite DevServer (Port: 3000)
echo ========================================================
cd /d "%~dp0\.."
cd frontend
if not exist node_modules (
    echo 首次运行: 正在安装前端依赖...
    call npm install
)
call npm run dev
pause
