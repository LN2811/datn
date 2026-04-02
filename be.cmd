@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\backend-dev.ps1" %*
