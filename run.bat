@echo off
REM Script para iniciar o sistema e exibir link de acesso universal
echo Obtendo IP local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do set IP=%%a
set IP=%IP: =%
echo.
echo ===================================================
echo Acesse o sistema em qualquer PC da rede:
echo http://%IP%:5000/login
echo ===================================================
python app.py
