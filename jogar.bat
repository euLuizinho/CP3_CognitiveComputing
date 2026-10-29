@echo off
title Muro Humano - Hole in the Wall
echo ==============================================
echo       MURO HUMANO - INICIANDO O JOGO
echo ==============================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
