@echo off
echo ===================================================
echo     Starting Multimodal RAG AI Enterprise System
echo ===================================================

echo.
echo [0/2] Checking and setting up environments...

if not exist frontend\node_modules\ (
    echo Frontend node_modules not found. Installing dependencies...
    cd frontend
    call npm install
    cd ..
)

if not exist backend\venv\ (
    echo Backend venv not found. Creating virtual environment and installing dependencies...
    cd backend
    call py -m venv venv
    call .\venv\Scripts\activate
    call pip install -r requirements.txt
    call deactivate
    cd ..
) else (
    echo Environments check passed.
)

echo.
echo [1/2] Launching FastAPI Backend (Port: 8000)...
start "Backend Services (FastAPI)" cmd /c "cd backend && call .\venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo [2/2] Launching React Vite Frontend (Port: 5173)...
start "Frontend UI (React/Vite)" cmd /c "cd frontend && npm run dev"

echo.
echo Both services are now running in separate windows.
echo - Frontend: http://localhost:5173
echo - Backend API Docs: http://localhost:8000/docs
echo.
pause
