# Atualiza o acervo local: roda as fontes que passaram da frequência (ingestion/fontes.toml)
# e grava o log em backend/data/logs/acervo_AAAA-MM-DD.log.
#
# Registrar no Agendador de Tarefas do Windows (uma vez, num PowerShell do usuário):
#   $acao = New-ScheduledTaskAction -Execute "powershell.exe" `
#       -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Projetos Mikael\Panoptico\scripts\acervo_diario.ps1"'
#   $quando = New-ScheduledTaskTrigger -Daily -At 3am
#   Register-ScheduledTask -TaskName "Panoptico - acervo" -Action $acao -Trigger $quando
#
# Remover: Unregister-ScheduledTask -TaskName "Panoptico - acervo"

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"
$logs = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$log = Join-Path $logs ("acervo_{0:yyyy-MM-dd}.log" -f (Get-Date))

$env:DATABASE_URL = "postgresql+psycopg://panoptico:panoptico@localhost:5432/panoptico_acervo"
$env:PRESERVAR_RAW = "true"
$env:PYTHONUNBUFFERED = "1"

Set-Location $backend
& ".venv\Scripts\python.exe" -m alembic upgrade head *>> $log
& ".venv\Scripts\python.exe" -m ingestion.acervo rodar --vencidas *>> $log
& ".venv\Scripts\python.exe" -m ingestion.acervo relatorio *>> $log
