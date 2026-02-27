@echo off
:: Market Digest — Setup (Windows)
:: This just calls the PowerShell setup script.
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
