# Levanta backend y frontend en dos ventanas separadas.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$root\backend'; Write-Host 'API en http://127.0.0.1:8000/docs' -ForegroundColor Cyan; ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000"
)

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$root\frontend'; Write-Host 'App en http://localhost:5173' -ForegroundColor Cyan; npm run dev"
)

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "Antes de grabar el video, use el boton 'Reiniciar demo'." -ForegroundColor Yellow
