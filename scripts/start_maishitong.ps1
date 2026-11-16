# 麦视通本机演示启动脚本：打开两个可见 PowerShell 窗口，便于查看启动日志。
$project = 'D:\Desktop\wheat\source-code\wheat-phenotyping'
$frontend = 'D:\Desktop\wheat\source-code\wheat-phenotyping\frontend'
$python = 'D:\Desktop\wheat\source-code\wheat-phenotyping\.venv\Scripts\python.exe'
$src = 'D:\Desktop\wheat\source-code\wheat-phenotyping\src'
$dinov2 = 'D:\Desktop\wheat\source-code\wheat-phenotyping\.external\dinov2'

if (!(Test-Path $python)) { throw "未找到项目 Python：$python" }
if (!(Test-Path "$frontend\package.json")) { throw "未找到前端 package.json：$frontend" }

$backendCommand = "`$env:PYTHONPATH='$src;$dinov2;$project'; & '$python' -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',$backendCommand -WorkingDirectory 'D:\Desktop\wheat\source-code\wheat-phenotyping' -WindowStyle Normal
Start-Process powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command','npm.cmd run dev' -WorkingDirectory 'D:\Desktop\wheat\source-code\wheat-phenotyping\frontend' -WindowStyle Normal

Write-Host '麦视通正在启动。前端：http://127.0.0.1:5173/' -ForegroundColor Green
Write-Host '后端健康检查：http://127.0.0.1:8000/api/health' -ForegroundColor Green
