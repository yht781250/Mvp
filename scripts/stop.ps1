$ErrorActionPreference = "SilentlyContinue"

$targets = @("uvicorn", "streamlit")

foreach ($name in $targets) {
    Get-CimInstance Win32_Process -Filter "name = 'python.exe' OR name = 'pythonw.exe'" |
        Where-Object { $_.CommandLine -match $name } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force
            Write-Host "已停止进程: $name (PID=$($_.ProcessId))"
        }
}

Write-Host "停止完成。"

