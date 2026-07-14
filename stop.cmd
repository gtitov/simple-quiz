@echo off
chcp 65001 >nul
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if (-not $listeners) { exit 2 }; $listeners | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction Stop }"

if errorlevel 2 (
    echo Сервер не запущен.
) else if errorlevel 1 (
    echo Не удалось остановить сервер.
) else (
    echo Сервер остановлен.
)

pause
