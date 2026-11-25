@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --no-cache-dir --keyring-provider disabled --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --no-cache-dir --keyring-provider disabled torch==2.11.0 torchaudio==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --no-cache-dir --keyring-provider disabled -r requirements.txt
if errorlevel 1 goto failed
if not exist "vendor\seed-vc\inference.py" git clone https://github.com/Plachtaa/seed-vc.git vendor\seed-vc
if errorlevel 1 goto failed
git -C vendor\seed-vc checkout 51383efd921027683c89e5348211d93ff12ac2a8
if errorlevel 1 goto failed
.venv\Scripts\python.exe prepare_seed.py
if errorlevel 1 goto failed
echo Setup complete. Open Launch.cmd.
pause
exit /b 0
:failed
echo Setup failed. The error is shown above.
pause
exit /b 1
