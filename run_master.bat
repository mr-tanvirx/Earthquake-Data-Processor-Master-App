@echo on
:: Forces Python to instantly stream all terminal output without buffering
set PYTHONUNBUFFERED=1
set VENV_DIR=venv

echo Checking for virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment not found. Creating "%VENV_DIR%"...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo Failed to create virtual environment. Please ensure Python is installed and in your PATH.
        pause
        exit /b
    )
    echo Virtual environment created successfully.
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Installing required Python packages (Verbose Mode Active)...
python -m pip install --upgrade pip -v
pip install -v flask pandas numpy matplotlib pyarrow fastparquet boto3 plotly obspy

echo Starting the Master Web UI Application...
python master_app.py

echo Deactivating virtual environment...
deactivate
pause