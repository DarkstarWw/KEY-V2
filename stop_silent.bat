@echo off
chcp 65001 >nul
REM 停止静默运行的图床服务与隧道
taskkill /IM cloudflared.exe /F >nul 2>&1
taskkill /IM pythonw.exe /F >nul 2>&1
echo 已停止 Flask 服务与隧道。
timeout /t 2 >nul
