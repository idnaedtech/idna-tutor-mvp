@echo off
REM Start keep-alive script in background
start /B powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0keep-alive.ps1"
echo Keep-alive started. Check keep-alive.log for status.
