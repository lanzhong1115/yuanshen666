# 养基助手 - 一键部署脚本（在服务器上运行）
Write-Host "=== 养基助手 服务器部署 ===" -ForegroundColor Green

# 1. Install Python
$pythonUrl = "https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe"
$pythonInstaller = "$env:TEMP\python-installer.exe"
Write-Host "[1/4] Downloading Python..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
Start-Process -Wait -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
Write-Host "[1/4] Python installed" -ForegroundColor Green

# 2. Download code
Write-Host "[2/4] Downloading code..." -ForegroundColor Yellow
$env:PATH = "C:\Python313;C:\Python313\Scripts;$env:PATH"
pip install fastapi uvicorn akshare pandas numpy aiosqlite httpx python-dateutil apscheduler
New-Item -ItemType Directory -Path C:\fund-app -Force
Set-Location C:\fund-app
Invoke-WebRequest -Uri "https://github.com/lanzhong1115/yuanshen666/archive/refs/heads/main.zip" -OutFile main.zip
Expand-Archive -Path main.zip -DestinationPath . -Force
Move-Item -Path yuanshen666-main\* -Destination . -Force
Remove-Item -Recurse -Force yuanshen666-main, main.zip
Write-Host "[2/4] Code downloaded" -ForegroundColor Green

# 3. Start server
Write-Host "[3/4] Starting server..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8765"

# 4. Done
Write-Host "[4/4] DONE! Server running at http://139.155.150.75:8765" -ForegroundColor Green
Write-Host "Update APK capacitor.config.json to point to this URL" -ForegroundColor Cyan
