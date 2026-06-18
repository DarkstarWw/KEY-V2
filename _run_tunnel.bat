@echo off
cd /d %~dp0
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 --url http://127.0.0.1:5000 > "%~dp0tunnel.log" 2>&1
