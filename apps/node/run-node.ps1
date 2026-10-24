# Sarce Node runner (ADR 0010): keeps the node going for good. Started at boot by the "Sarce Node" scheduled task.
# - downloads the code bundle from the server when the node reports it is out of date (exit code 3);
# - restarts the node whenever it stops (a crash, or the server going away), after a short pause.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent   # C:\SarceNode
$cfg = @{}
Get-Content (Join-Path $root "node.env") | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" } | ForEach-Object {
    $k, $v = $_ -split "=", 2; $cfg[$k.Trim()] = $v.Trim()
}
$python = Join-Path $root "venv\Scripts\python.exe"
$log = Join-Path $root "node.log"

function Update-Bundle {
    $zip = Join-Path $root "bundle.zip"
    Invoke-WebRequest -Uri "$($cfg.SERVER)/nodes/bundle.zip" -Headers @{ "X-Sarce-Node" = $cfg.TOKEN } -OutFile $zip -UseBasicParsing
    foreach ($dir in "api", "node") { if (Test-Path (Join-Path $root $dir)) { Remove-Item -Recurse -Force (Join-Path $root $dir) } }
    Expand-Archive -Path $zip -DestinationPath $root -Force
    Remove-Item $zip
    & $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $root "node\requirements-node.txt") | Out-Null
}

while ($true) {
    if (-not (Test-Path (Join-Path $root "node\sarce_node.py"))) {
        try { Update-Bundle } catch { Add-Content $log "$(Get-Date -Format s) bundle download failed: $_"; Start-Sleep 60; continue }
    }
    & $python (Join-Path $root "node\sarce_node.py") *>> $log
    if ($LASTEXITCODE -eq 3) {
        try { Update-Bundle; Add-Content $log "$(Get-Date -Format s) bundle updated" } catch { Add-Content $log "$(Get-Date -Format s) update failed: $_" }
    } else {
        Add-Content $log "$(Get-Date -Format s) node stopped (exit $LASTEXITCODE); restarting in 30 s"
        Start-Sleep 30
    }
    # Keep the log from growing without bound on a machine that runs for months.
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 20MB) { Move-Item -Force $log "$log.old" }
}
