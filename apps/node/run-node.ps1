# Sarce Node runner (ADR 0010): keeps the node going for good. Started at boot by the "Sarce Node" scheduled task.
# It lives in C:\SarceNode itself, outside the node\ folder an update replaces, so a power cut mid-update can't
# remove what the boot task starts.
# - downloads the code bundle when the node reports it is out of date (exit code 3), checks its signature (HMAC
#   with the pairing token) and swaps it in only once it is complete;
# - restarts the node whenever it stops (a crash, or the server going away), after a short pause.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path   # C:\SarceNode
$cfg = @{}
Get-Content (Join-Path $root "node.env") | Where-Object { $_ -match "=" -and $_ -notmatch "^\s*#" } | ForEach-Object {
    $k, $v = $_ -split "=", 2; $cfg[$k.Trim()] = $v.Trim()
}
$python = Join-Path $root "venv\Scripts\python.exe"
$log = Join-Path $root "node.log"

function Get-SignedBundle {
    # The gateway signs the bundle with the pairing token; anything else on the network can't produce that.
    $res = Invoke-WebRequest -Uri "$($cfg.SERVER)/nodes/bundle.zip" -Headers @{ "X-Sarce-Node" = $cfg.TOKEN } -UseBasicParsing
    $bytes = $res.RawContentStream.ToArray()
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($cfg.TOKEN))
    $hex = -join ($hmac.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") })
    if ($hex -ne [string]$res.Headers["X-Sarce-Signature"]) { throw "bundle signature doesn't match: not installed" }
    return $bytes
}

function Update-Bundle {
    $bytes = Get-SignedBundle
    $zip = Join-Path $root "bundle.zip"
    $new = Join-Path $root "bundle.new"
    [IO.File]::WriteAllBytes($zip, $bytes)
    if (Test-Path $new) { Remove-Item -Recurse -Force $new }
    Expand-Archive -Path $zip -DestinationPath $new -Force
    Remove-Item $zip
    # Offline machines install from the wheels the kit left in C:\SarceNode\wheels; online ones from PyPI.
    $wheels = Join-Path $root "wheels"
    $source = if (Test-Path $wheels) { @("--no-index", "--find-links", $wheels) } else { @() }
    & $python -m pip install --quiet --disable-pip-version-check @source -r (Join-Path $new "node\requirements-node.txt") | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "the new bundle's packages didn't install (offline: add their wheels to $wheels)" }
    # Swap only now that the new bundle is complete.
    foreach ($item in "api", "node", "VERSION") {
        $old = Join-Path $root $item
        if (Test-Path $old) { Remove-Item -Recurse -Force $old }
        Move-Item (Join-Path $new $item) $old
    }
    Remove-Item -Recurse -Force $new
}

while ($true) {
    if (-not (Test-Path (Join-Path $root "node\sarce_node.py"))) {
        try { Update-Bundle } catch { Add-Content $log "$(Get-Date -Format s) bundle download failed: $_"; Start-Sleep 60; continue }
    }
    & $python (Join-Path $root "node\sarce_node.py") *>> $log
    if ($LASTEXITCODE -eq 3) {
        try { Update-Bundle; Add-Content $log "$(Get-Date -Format s) bundle updated" } catch { Add-Content $log "$(Get-Date -Format s) update failed: $_"; Start-Sleep 60 }
    } else {
        Add-Content $log "$(Get-Date -Format s) node stopped (exit $LASTEXITCODE); restarting in 30 s"
        Start-Sleep 30
    }
    # Keep the log from growing without bound on a machine that runs for months.
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 20MB) { Move-Item -Force $log "$log.old" }
}
