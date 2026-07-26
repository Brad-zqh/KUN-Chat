param(
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = "D:\LocalDevDeps\OneDriveMirror\LLMs\KUN-Chat\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Migrated Python runtime was not found: $PythonExe"
}

$env:WEB_HOST = "0.0.0.0"
$env:WEB_PORT = $Port.ToString()
Set-Location -LiteralPath $ProjectRoot

Write-Host "KUN Chat local service is starting in the foreground."
Write-Host "Computer: http://127.0.0.1:$Port/chat.html"
Write-Host "Phone on the same Wi-Fi: use http://<this-computer-LAN-IP>:$Port/chat.html"
Write-Host "Press Ctrl+C to stop."

& $PythonExe -m worker.web_server

