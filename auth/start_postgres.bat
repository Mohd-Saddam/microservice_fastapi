@echo off
REM Start PostgreSQL Service on Windows
REM This script attempts to start the PostgreSQL service

echo === Starting PostgreSQL Service ===
echo.

REM Try to find and start PostgreSQL service
REM Common PostgreSQL service names on Windows
set services=postgresql-x64-16 postgresql-x64-15 postgresql-x64-14 postgresql-x64-13 postgresql-x64-12 postgresql

for %%s in (%services%) do (
    echo Attempting to start service: %%s
    sc query %%s >nul 2>&1
    if %errorlevel% equ 0 (
        net start %%s
        if %errorlevel% equ 0 (
            echo.
            echo PostgreSQL service %%s started successfully!
            goto :success
        )
    )
)

echo.
echo Could not find or start PostgreSQL service automatically.
echo.
echo Please try one of the following options:
echo.
echo Option 1: Start PostgreSQL manually using Windows Services
echo    1. Press Win + R, type "services.msc" and press Enter
echo    2. Find "postgresql" service in the list
echo    3. Right-click and select "Start"
echo.
echo Option 2: Use pgAdmin to start the server
echo    1. Open pgAdmin
echo    2. Right-click on your server
echo    3. Select "Start/Restart Server"
echo.
echo Option 3: Use Docker to run PostgreSQL
echo    docker run --name postgres-db -e POSTGRES_PASSWORD=%POSTGRES_PASSWORD% -e POSTGRES_USER=%POSTGRES_USER% -e POSTGRES_DB=%POSTGRES_DB% -p 5432:5432 -d postgres
echo.
goto :end

:success
echo.
echo Running health check to verify services...
echo.
python check_services.py

:end
pause

