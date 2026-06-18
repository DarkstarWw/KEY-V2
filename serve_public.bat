@echo off
chcp 65001 >nul
REM ===== 临时公网测试：起服务 + 开 cloudflared 隧道 =====
cd /d %~dp0

REM 关调试（公网暴露安全），关自动开浏览器；子窗口会继承这些变量
set TU_DEBUG=0
set TU_AUTO_OPEN=0

REM 1) 新窗口启动 Flask 服务（127.0.0.1:5000）
start "TU-SERVER" cmd /k python run.py

REM 2) 等服务起来
echo 正在启动服务，请稍候...
ping -n 5 127.0.0.1 >nul

REM 3) 本窗口开隧道，输出里 trycloudflare.com 那行就是公网地址
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5000

pause
