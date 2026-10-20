<#
.SYNOPSIS
  Guia a instalação do runner do GitHub Actions no PC do dono (Windows, no Brasil), com o
  label "brasil". Serve às fontes que só respondem a IP brasileiro (geobloqueio).

.DESCRIPTION
  NÃO é proxy nem truque: é uma máquina no Brasil fazendo a coleta pública normalmente.

  O que o script faz, em ordem:
    1. confere pré-requisitos (PowerShell como administrador, git, python, gh logado);
    2. baixa o runner oficial (versão fixa) e confere o SHA-256 antes de extrair;
    3. cria (se faltar) um usuário local SEM privilégio de administrador para rodar o serviço;
    4. extrai o runner numa pasta FORA do repositório e restringe o acesso a ela;
    5. pede ao GitHub (via `gh`, com a sua conta) um token de registro de uso único;
    6. registra o runner com o label "brasil" e instala como serviço do Windows.

  Nada é gravado no repositório. Nenhum segredo é impresso. O DATABASE_URL continua só nos
  Secrets do GitHub: o runner o recebe em cada job e não o guarda no disco.

  Para parar: veja docs/DEPLOY_GRATUITO.md, "Runner no Brasil" (pausar e remover).

.EXAMPLE
  # PowerShell COMO ADMINISTRADOR, na raiz do repositório:
  powershell -ExecutionPolicy Bypass -File scripts\instalar-runner-brasil.ps1

  # Só ver o que faria, sem alterar nada:
  powershell -ExecutionPolicy Bypass -File scripts\instalar-runner-brasil.ps1 -SoConferir
#>
param(
    [string]$Repositorio = 'Gipsy7/panoptico',
    [string]$Pasta = 'C:\actions-runner-panoptico',      # fora do repositório e de pastas sincronizadas
    [string]$Usuario = 'runner-panoptico',               # usuário local sem admin que roda o serviço
    [string]$NomeDoRunner = "panoptico-brasil-$env:COMPUTERNAME",
    [switch]$SoConferir
)

$ErrorActionPreference = 'Stop'

# Versão fixa do runner e SHA-256 do zip (publicado nas notas da versão, github.com/actions/runner/releases).
# Ao atualizar: troque as duas linhas juntas, conferindo o hash nas notas da versão nova.
$Versao = '2.338.0'
$Zip = "actions-runner-win-x64-$Versao.zip"
$Sha256Esperado = 'f48e0750a21812bca5f82de5f7f5aeae71abee647fab5a582f1742d07eba455f'
$Url = "https://github.com/actions/runner/releases/download/v$Versao/$Zip"

function Passo($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }
function Falha($texto) { Write-Host "ERRO: $texto" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------------------------
Passo '1. Pré-requisitos'
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin -and -not $SoConferir) { Falha 'abra o PowerShell como administrador (instalar serviço exige).' }
foreach ($cmd in 'git', 'python', 'gh') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Falha "'$cmd' não está no PATH. Instale para TODOS os usuários (o serviço roda com outro usuário)."
    }
}
# Os jobs usam shell bash (Git para Windows) e `python -m pip install uv`.
$bash = Join-Path (Split-Path (Split-Path (Get-Command git).Source)) 'bin\bash.exe'
if (-not (Test-Path $bash)) { Write-Host 'Aviso: bash.exe do Git não encontrado ao lado do git; os jobs usam "shell: bash".' -ForegroundColor Yellow }
python --version
gh auth status
Write-Host "Repositório: $Repositorio | pasta: $Pasta | usuário do serviço: $Usuario | runner $Versao"
if ($SoConferir) { Write-Host "`n-SoConferir: nada foi alterado."; exit 0 }

# ---------------------------------------------------------------------------------------------
Passo '2. Baixar o runner oficial e conferir o SHA-256'
$tmp = Join-Path $env:TEMP "runner-$Versao"
New-Item -ItemType Directory -Force $tmp | Out-Null
$arquivo = Join-Path $tmp $Zip
if (-not (Test-Path $arquivo)) { Invoke-WebRequest -Uri $Url -OutFile $arquivo }
$hash = (Get-FileHash -Algorithm SHA256 $arquivo).Hash.ToLower()
if ($hash -ne $Sha256Esperado) {
    Remove-Item $arquivo -Force
    Falha "SHA-256 diferente do esperado ($hash). Arquivo apagado; nada foi instalado."
}
Write-Host 'SHA-256 confere.'

# ---------------------------------------------------------------------------------------------
Passo '3. Usuário local sem privilégio de administrador'
if (-not (Get-LocalUser -Name $Usuario -ErrorAction SilentlyContinue)) {
    $senha = Read-Host "Defina uma senha forte para o usuário '$Usuario' (fica só no Windows)" -AsSecureString
    New-LocalUser -Name $Usuario -Password $senha -PasswordNeverExpires `
        -UserMayNotChangePassword -Description 'Executa o runner do Panóptico (sem admin)' | Out-Null
    Add-LocalGroupMember -Group 'Users' -Member $Usuario -ErrorAction SilentlyContinue
    # Não pode entrar interativamente nem por área de trabalho remota: só roda o serviço.
    Write-Host "Usuário '$Usuario' criado (grupo Users, sem admin)."
} else {
    $senha = Read-Host "Senha atual do usuário '$Usuario'" -AsSecureString
}
if (Get-LocalGroupMember -Group 'Administrators' -Member $Usuario -ErrorAction SilentlyContinue) {
    Falha "'$Usuario' é administrador. Remova-o do grupo Administrators e rode de novo."
}
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($senha)
$senhaTexto = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# ---------------------------------------------------------------------------------------------
Passo '4. Extrair numa pasta fora do repositório e restringir o acesso'
if (Test-Path (Join-Path $Pasta 'config.cmd')) { Falha "$Pasta já tem um runner. Para reinstalar, remova antes (docs/DEPLOY_GRATUITO.md)." }
New-Item -ItemType Directory -Force $Pasta | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($arquivo, $Pasta)
# Só administradores, SYSTEM e o usuário do serviço leem/escrevem na pasta.
icacls $Pasta /inheritance:r /grant:r 'Administrators:(OI)(CI)F' 'SYSTEM:(OI)(CI)F' "${Usuario}:(OI)(CI)M" | Out-Null

# ---------------------------------------------------------------------------------------------
Passo '5. Token de registro (uso único, expira em 1 hora; não é impresso)'
$token = gh api -X POST "repos/$Repositorio/actions/runners/registration-token" --jq .token
if (-not $token) { Falha 'não foi possível obter o token (sua conta precisa ser dona/admin do repositório).' }

# ---------------------------------------------------------------------------------------------
Passo '6. Registrar com o label "brasil" e instalar como serviço'
Push-Location $Pasta
try {
    & .\config.cmd --unattended --url "https://github.com/$Repositorio" --token $token `
        --name $NomeDoRunner --labels brasil --work _work --replace `
        --runasservice --windowslogonaccount ".\$Usuario" --windowslogonpassword $senhaTexto
    if ($LASTEXITCODE -ne 0) { Falha 'config.cmd falhou.' }
} finally {
    Pop-Location
    $token = $null
    $senhaTexto = $null
}

Get-Service "actions.runner.*" | Format-Table Name, Status -AutoSize
Write-Host @"

Pronto. Confira em https://github.com/$Repositorio/settings/actions/runners (deve aparecer
'$NomeDoRunner' como Idle, com os labels self-hosted, Windows, X64, brasil).

Falta (manual, no GitHub):
  Settings > Actions > General > Fork pull request workflows from outside collaborators:
  "Require approval for all outside collaborators".
Teste: Actions > "Câmaras e assembleias (SAPL)" > Run workflow (ufs = ["RR"]) e veja o job
alerr rodar no seu PC.
"@
