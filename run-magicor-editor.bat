@echo off
cd /d "%~dp0"
py -3 Magicor-LevelEditor.py
if errorlevel 1 pause
