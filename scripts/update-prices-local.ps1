# Daily price update from this PC. Woolworths and Coles block GitHub's
# servers but allow a home connection, so this fills them in after the
# GitHub Action's 5am run. Run by the "Everyday Lean prices" scheduled task.
$repo = Split-Path $PSScriptRoot -Parent
$log = Join-Path $env:LOCALAPPDATA 'EverydayLean\price-update.log'
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
$git = 'C:\Program Files\Git\cmd\git.exe'
$python = 'C:\Users\hayle\AppData\Local\Programs\Python\Python312\python.exe'

function Log($msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Add-Content $log -Encoding utf8 }

# Run a program, log its output, and stop the update if it fails.
function Run($exe, [string[]]$arguments) {
    $out = & cmd /c "`"$exe`" $($arguments -join ' ') 2>&1"
    $out | ForEach-Object { Log "  $_" }
    if ($LASTEXITCODE -ne 0) { Log "FAILED ($LASTEXITCODE): $exe $arguments"; exit 1 }
}

Set-Location $repo
$env:PYTHONIOENCODING = 'utf8'
Log 'Starting price update'
Run $git @('pull', '--rebase', '--quiet')
Run $python @('scripts\fetch_prices.py')
Run $git @('add', 'prices.json')
& $git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Log 'No price changes'; exit 0 }
Run $git @('commit', '--quiet', '-m', '"Daily price update (home PC)"')
Run $git @('pull', '--rebase', '--quiet')
Run $git @('push', '--quiet')
Log 'Pushed prices.json'
