# Node 22 LTS (y 24 para MyPersonalWeb) con fnm en Windows, sin tocar el Node
# del sistema. Ejecutar en PowerShell, como usuario normal (sin admin):
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup-node.ps1
#
# fnm cambia de versión solo al entrar en una carpeta con .nvmrc (este repo pide 22).

$ErrorActionPreference = "Stop"

# 1. fnm: gestor de versiones rápido, instalado con winget
winget install --id Schniz.fnm --exact --accept-source-agreements --accept-package-agreements

# 2. Recarga el PATH de esta sesión (winget acaba de añadir fnm)
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
fnm --version

# 3. Activa fnm en todas las sesiones futuras de PowerShell (auto-cambio al entrar en carpetas con .nvmrc)
$line = 'fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression'
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
if (-not (Select-String -Path $PROFILE -Pattern 'fnm env' -Quiet)) { Add-Content -Path $PROFILE -Value $line }
Invoke-Expression $line

# 4. Instala 22 (por defecto) y 24
fnm install 22
fnm install 24
fnm default 22
fnm use 22

Write-Host ""
Write-Host "node $(node -v)  npm $(npm -v)" -ForegroundColor Green
Write-Host "Abre una terminal nueva para que el perfil cargue fnm. En MonsterBroker: 'fnm use' lee .nvmrc (22)."
Write-Host "Opcional, para quitar el Node 20 del sistema:  winget uninstall --id OpenJS.NodeJS"
