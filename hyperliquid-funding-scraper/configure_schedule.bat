@echo off
title Configurador de Agendamento - Hyperliquid Scraper
color 0E

echo ============================================================
echo   Configurador de Execucao Automatica
echo   Hyperliquid Funding Rate Scraper
echo ============================================================
echo.

echo [INFO] Este script vai configurar a execucao automatica do scraper.
echo [INFO] Voce pode escolher diferentes intervalos e metodos.
echo.

:menu
echo ============================================================
echo                 OPCOES DE AGENDAMENTO
echo ============================================================
echo.
echo  1. Modo Daemon (Recomendado)          [Executa continuamente]
echo  2. Agendamento Windows (Task Scheduler) [Sistema operacional]
echo  3. Configurar Intervalo Personalizado   [Minutos customizados]
echo  4. Configurar APScheduler              [Agendador Python]
echo  5. Ver Configuracao Atual              [Status do agendamento]
echo  6. Parar Execucao Automatica           [Desativar scheduler]
echo  0. Voltar ao Menu Principal            [Sair]
echo.
echo ============================================================

set /p choice="[INPUT] Selecione uma opcao (0-6): "

if "%choice%"=="1" goto daemon_mode
if "%choice%"=="2" goto windows_scheduler
if "%choice%"=="3" goto custom_interval
if "%choice%"=="4" goto apscheduler_config
if "%choice%"=="5" goto show_config
if "%choice%"=="6" goto stop_scheduler
if "%choice%"=="0" goto exit
goto invalid_option

:daemon_mode
echo.
echo ============================================================
echo                    MODO DAEMON
echo ============================================================
echo.
echo [INFO] O modo daemon executa o scraper continuamente em segundo plano.
echo [INFO] Ele coleta dados automaticamente no intervalo configurado.
echo.
echo Intervalos disponiveis:
echo  1. A cada 15 minutos (Recomendado para alta frequencia)
echo  2. A cada 30 minutos (Equilibrio entre frequencia e recursos)
echo  3. A cada 1 hora (Padrao - boa para maioria dos casos)
echo  4. A cada 2 horas (Menor uso de recursos)
echo  5. A cada 4 horas (Minimo recomendado)
echo  6. Personalizado (especificar minutos)
echo.

set /p interval_choice="[INPUT] Escolha o intervalo (1-6): "

if "%interval_choice%"=="1" set minutes=15
if "%interval_choice%"=="2" set minutes=30
if "%interval_choice%"=="3" set minutes=60
if "%interval_choice%"=="4" set minutes=120
if "%interval_choice%"=="5" set minutes=240
if "%interval_choice%"=="6" (
    set /p minutes="[INPUT] Digite o intervalo em minutos: "
)

if "%minutes%"=="" set minutes=60

echo.
echo [INFO] Configurando intervalo para %minutes% minutos...

REM Update .env file with new interval
if exist ".env" (
    powershell -command "(Get-Content .env) -replace 'RUN_INTERVAL_MINUTES=.*', 'RUN_INTERVAL_MINUTES=%minutes%' | Set-Content .env"
    powershell -command "(Get-Content .env) -replace 'ENABLE_SCHEDULER=.*', 'ENABLE_SCHEDULER=true' | Set-Content .env"
) else (
    echo RUN_INTERVAL_MINUTES=%minutes% >> .env
    echo ENABLE_SCHEDULER=true >> .env
)

echo [OK] Configuracao salva!
echo [INFO] Intervalo definido para %minutes% minutos
echo.
echo [INFO] Iniciando modo daemon...
echo [WARNING] Pressione Ctrl+C para parar a execucao
echo.
pause

REM Activate venv and run daemon
call venv\Scripts\activate
python -m src.main --daemon

echo.
echo [INFO] Daemon parado.
pause
goto menu

:windows_scheduler
echo.
echo ============================================================
echo              AGENDAMENTO DO WINDOWS
echo ============================================================
echo.
echo [INFO] Criando tarefa agendada no Windows Task Scheduler
echo [INFO] Isso permitira que o scraper execute mesmo quando voce nao estiver logado.
echo.

echo Intervalos disponiveis:
echo  1. A cada 15 minutos
echo  2. A cada 30 minutos
echo  3. A cada 1 hora
echo  4. A cada 2 horas
echo  5. A cada 4 horas
echo  6. Diariamente (uma vez por dia)
echo.

set /p sched_choice="[INPUT] Escolha o intervalo (1-6): "

set task_name=HyperliquidScraper
set script_path=%CD%\run_scheduled.bat

REM Create batch script for scheduled execution
echo @echo off > %script_path%
echo cd /d "%CD%" >> %script_path%
echo call venv\Scripts\activate >> %script_path%
echo python -m src.main --run-once >> %script_path%

if "%sched_choice%"=="1" (
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc minute /mo 15 /f
    echo [OK] Tarefa criada: Execucao a cada 15 minutos
)
if "%sched_choice%"=="2" (
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc minute /mo 30 /f
    echo [OK] Tarefa criada: Execucao a cada 30 minutos
)
if "%sched_choice%"=="3" (
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc hourly /mo 1 /f
    echo [OK] Tarefa criada: Execucao a cada hora
)
if "%sched_choice%"=="4" (
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc hourly /mo 2 /f
    echo [OK] Tarefa criada: Execucao a cada 2 horas
)
if "%sched_choice%"=="5" (
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc hourly /mo 4 /f
    echo [OK] Tarefa criada: Execucao a cada 4 horas
)
if "%sched_choice%"=="6" (
    set /p daily_time="[INPUT] Digite o horario (HH:MM, ex: 14:30): "
    schtasks /create /tn "%task_name%" /tr "%script_path%" /sc daily /st %daily_time% /f
    echo [OK] Tarefa criada: Execucao diaria as %daily_time%
)

echo.
echo [INFO] Tarefa "%task_name%" criada com sucesso!
echo [INFO] Para gerenciar: Windows + R, digite "taskschd.msc"
echo [INFO] Para remover: schtasks /delete /tn "%task_name%" /f
echo.
pause
goto menu

:custom_interval
echo.
echo ============================================================
echo           CONFIGURACAO DE INTERVALO PERSONALIZADO
echo ============================================================
echo.

set /p custom_minutes="[INPUT] Digite o intervalo em minutos (5-1440): "

REM Validate input
if %custom_minutes% lss 5 (
    echo [ERROR] Intervalo minimo e 5 minutos
    pause
    goto menu
)
if %custom_minutes% gtr 1440 (
    echo [ERROR] Intervalo maximo e 1440 minutos (24 horas)
    pause
    goto menu
)

echo.
echo [INFO] Configurando intervalo personalizado: %custom_minutes% minutos

REM Update .env file
if exist ".env" (
    powershell -command "(Get-Content .env) -replace 'RUN_INTERVAL_MINUTES=.*', 'RUN_INTERVAL_MINUTES=%custom_minutes%' | Set-Content .env"
    powershell -command "(Get-Content .env) -replace 'ENABLE_SCHEDULER=.*', 'ENABLE_SCHEDULER=true' | Set-Content .env"
    echo [OK] Configuracao salva em .env
) else (
    echo [ERROR] Arquivo .env nao encontrado
)

echo.
echo [INFO] Intervalo configurado para %custom_minutes% minutos
echo [INFO] Use "Modo Daemon" ou "run.bat -> opcao 3" para iniciar
echo.
pause
goto menu

:apscheduler_config
echo.
echo ============================================================
echo             CONFIGURACAO AVANCADA - APSCHEDULER
echo ============================================================
echo.
echo [INFO] Configurando agendador Python com multiplos horarios
echo.

echo Opcoes de agendamento:
echo  1. Intervalo simples (minutos)
echo  2. Horarios especificos (ex: 9:00, 14:00, 18:00)
echo  3. Dias da semana especificos
echo  4. Configuracao CRON customizada
echo.

set /p sched_type="[INPUT] Escolha o tipo (1-4): "

if "%sched_type%"=="1" (
    set /p interval_min="[INPUT] Intervalo em minutos: "
    echo RUN_INTERVAL_MINUTES=%interval_min% > .temp_config
    echo SCHEDULE_TYPE=interval >> .temp_config
)

if "%sched_type%"=="2" (
    set /p times="[INPUT] Horarios (ex: 09:00,14:00,18:00): "
    echo SCHEDULE_TIMES=%times% > .temp_config
    echo SCHEDULE_TYPE=times >> .temp_config
)

if "%sched_type%"=="3" (
    echo Dias: 1=Segunda, 2=Terca, 3=Quarta, 4=Quinta, 5=Sexta, 6=Sabado, 7=Domingo
    set /p days="[INPUT] Dias da semana (ex: 1,2,3,4,5): "
    set /p time="[INPUT] Horario (HH:MM): "
    echo SCHEDULE_DAYS=%days% > .temp_config
    echo SCHEDULE_TIME=%time% >> .temp_config
    echo SCHEDULE_TYPE=weekly >> .temp_config
)

if "%sched_type%"=="4" (
    echo Exemplo CRON: "0 */2 * * *" (a cada 2 horas)
    set /p cron="[INPUT] Expressao CRON: "
    echo SCHEDULE_CRON=%cron% > .temp_config
    echo SCHEDULE_TYPE=cron >> .temp_config
)

REM Append to .env
if exist ".temp_config" (
    type .temp_config >> .env
    del .temp_config
    echo [OK] Configuracao avancada salva!
)

echo.
pause
goto menu

:show_config
echo.
echo ============================================================
echo              CONFIGURACAO ATUAL
echo ============================================================
echo.

if exist ".env" (
    echo [INFO] Configuracoes atuais do .env:
    echo.
    findstr /C:"RUN_INTERVAL_MINUTES" .env 2>nul && echo [OK] Intervalo configurado
    findstr /C:"ENABLE_SCHEDULER" .env 2>nul && echo [OK] Scheduler configurado
    echo.

    REM Show Windows scheduled task
    schtasks /query /tn "HyperliquidScraper" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Tarefa do Windows encontrada:
        schtasks /query /tn "HyperliquidScraper" /fo LIST | findstr /C:"Next Run Time"
    ) else (
        echo [INFO] Nenhuma tarefa do Windows configurada
    )
) else (
    echo [WARNING] Arquivo .env nao encontrado
)

echo.
echo ============================================================
pause
goto menu

:stop_scheduler
echo.
echo ============================================================
echo             PARAR EXECUCAO AUTOMATICA
echo ============================================================
echo.

echo [INFO] Desativando execucao automatica...

REM Update .env to disable scheduler
if exist ".env" (
    powershell -command "(Get-Content .env) -replace 'ENABLE_SCHEDULER=.*', 'ENABLE_SCHEDULER=false' | Set-Content .env"
    echo [OK] Scheduler desativado no .env
)

REM Remove Windows scheduled task
schtasks /delete /tn "HyperliquidScraper" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Tarefa do Windows removida
) else (
    echo [INFO] Nenhuma tarefa do Windows encontrada
)

REM Remove scheduled script
if exist "run_scheduled.bat" (
    del "run_scheduled.bat"
    echo [OK] Script de execucao removido
)

echo.
echo [OK] Execucao automatica desativada com sucesso!
echo.
pause
goto menu

:invalid_option
echo.
echo [ERROR] Opcao invalida! Escolha entre 0-6.
timeout /t 2 >nul
goto menu

:exit
echo.
echo [INFO] Voltando ao menu principal...
call run.bat
exit /b 0