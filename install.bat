@echo off
echo =========================================
echo 1. Create Virtual Environment...
echo =========================================
python -m venv venv

echo.
echo =========================================
echo 2. Activate Virtual Environment...
echo =========================================
call venv\Scripts\activate.bat

echo.
echo =========================================
echo 3. Install Libraries (this might take a few minutes)...
echo =========================================
pip install -r requirements.txt

echo.
echo =========================================
echo Install finished! 
echo You can now close this window and open run.bat
echo =========================================
pause
