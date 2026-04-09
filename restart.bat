@echo off
echo ===================================================
echo     Restarting Multimodal RAG AI Enterprise System
echo ===================================================

echo.
echo [1/3] Cleaning up old Frontend Node Processes...
FOR /F "tokens=5" %%T IN ('netstat -a -n -o ^| findstr ":5173" ^| findstr "LISTENING"') DO (
   echo Found process on port 5173 with PID %%T. Stopping...
   TaskKill.exe /F /PID %%T 2>NUL
)

echo [2/3] Cleaning up old Backend Python Processes...
FOR /F "tokens=5" %%T IN ('netstat -a -n -o ^| findstr ":8000" ^| findstr "LISTENING"') DO (
   echo Found process on port 8000 with PID %%T. Stopping...
   TaskKill.exe /F /PID %%T 2>NUL
)

echo.
echo [3/3] Launching fresh instances...
timeout /t 2 /nobreak > NUL
call start.bat
