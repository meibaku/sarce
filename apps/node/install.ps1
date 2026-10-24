# Sarce Node installer (ADR 0010). Run once on the helper computer, in PowerShell as Administrator:
#
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Server http://192.168.137.1:8002 -Token <NODE_TOKEN> -Workers 4
#
# Without internet on this machine, add -Kit <folder>: a folder (local or a network share such as
# \\DESKTOP-K5KC76C\SarceNodeKit) with the Python installer, the node's wheels and the Stockfish zip, checked against
# its SHA256SUMS.txt. Only the code bundle then comes over the network, from your Sarce server.
#
# What it does, all under C:\SarceNode:
#   1. Python 3.12 (winget, or the python.org installer) if it isn't there, and a private virtual environment;
#   2. the code bundle from your Sarce server (the same code the server runs) and its few packages;
#   3. Stockfish 18 from the official release, in the build your CPU supports (AVX2, else SSE4.1);
#   4. node.env with the server, token, name and number of engines;
#   5. a "Sarce Node" scheduled task that starts at boot, before anyone logs in, and restarts after a power cut.
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [Parameter(Mandatory = $true)][string]$Token,
    [int]$Workers = 4,
    [string]$Root = "C:\SarceNode",
    [string]$Kit = ""
)
$ErrorActionPreference = "Stop"
$Server = $Server.TrimEnd("/")
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Write-Host "Sarce Node -> $Root"

# 0. Can we reach the server, and does it accept the token?
try {
    $config = Invoke-RestMethod -Uri "$Server/nodes/config" -Headers @{ "X-Sarce-Node" = $Token } -TimeoutSec 15
    Write-Host "Server reachable, bundle $($config.version), Stockfish $($config.stockfish)"
} catch {
    throw "Can't reach $Server/nodes/config with this token. Check the cable, the server's gateway and the token. ($_)"
}

# The offline kit: every file is checked against the kit's SHA256SUMS.txt before it is used.
function Get-KitFile([string]$Name) {
    $path = Join-Path $Kit $Name
    if (-not (Test-Path $path)) { throw "The kit has no $Name" }
    $line = Get-Content (Join-Path $Kit "SHA256SUMS.txt") | Where-Object { $_ -match "  $([regex]::Escape($Name))$" } | Select-Object -First 1
    if (-not $line) { throw "SHA256SUMS.txt doesn't list $Name" }
    if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLower() -ne ($line -split "\s+")[0].ToLower()) { throw "$Name doesn't match its checksum" }
    return $path
}
if ($Kit) { Write-Host "Offline kit: $Kit" }

# 1. Python
$py = (Get-Command py -ErrorAction SilentlyContinue)
$hasPython = $false
if ($py) { try { & py -3.12 --version | Out-Null; $hasPython = ($LASTEXITCODE -eq 0) } catch {} }
if (-not $hasPython) {
    Write-Host "Installing Python 3.12..."
    if ($Kit) {
        $installer = Get-KitFile "python-3.12.10-amd64.exe"
        Start-Process $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1" -Wait
    } elseif (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements --scope machine
    } else {
        $installer = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
        Invoke-WebRequest "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer -UseBasicParsing
        Start-Process $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1" -Wait
    }
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
if (-not (Test-Path "$Root\venv\Scripts\python.exe")) { & py -3.12 -m venv "$Root\venv" }

# 2. The code bundle (its signature checked against the token) and its packages
$res = Invoke-WebRequest -Uri "$Server/nodes/bundle.zip" -Headers @{ "X-Sarce-Node" = $Token } -UseBasicParsing
$bytes = $res.RawContentStream.ToArray()
$hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($Token))
$hex = -join ($hmac.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") })
if ($hex -ne [string]$res.Headers["X-Sarce-Signature"]) { throw "The bundle's signature doesn't match the token: not installing." }
$zip = Join-Path $Root "bundle.zip"
[IO.File]::WriteAllBytes($zip, $bytes)
foreach ($item in "api", "node", "VERSION") { if (Test-Path "$Root\$item") { Remove-Item -Recurse -Force "$Root\$item" } }
Expand-Archive -Path $zip -DestinationPath $Root -Force
Remove-Item $zip
# The runner lives outside node\, so an update (which replaces node\) never removes what the boot task starts.
Copy-Item "$Root\node\run-node.ps1" "$Root\run-node.ps1" -Force
if ($Kit) {
    # Keep the wheels here too, so later updates install offline as well (run-node.ps1 uses them when present).
    $wheels = Join-Path $Root "wheels"
    New-Item -ItemType Directory -Force -Path $wheels | Out-Null
    Get-ChildItem (Join-Path $Kit "wheels") -Filter "*.whl" | ForEach-Object { Copy-Item (Get-KitFile "wheels/$($_.Name)") $wheels -Force }
    & "$Root\venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --no-index --find-links $wheels --upgrade pip
    & "$Root\venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --no-index --find-links $wheels -r "$Root\node\requirements-node.txt"
} else {
    & "$Root\venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --upgrade pip
    & "$Root\venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r "$Root\node\requirements-node.txt"
}
if ($LASTEXITCODE -ne 0) { throw "Installing the node's packages failed" }

# 3. Stockfish 18, the build this CPU runs (an i7-3770 has no AVX2: SSE4.1). Same version as the server, so the
#    node-limited searches give the same results.
$sfDir = Join-Path $Root "stockfish"
$sfExe = Get-ChildItem $sfDir -Recurse -Filter "stockfish*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $sfExe) {
    Add-Type -Namespace Native -Name Cpu -MemberDefinition '[DllImport("kernel32.dll")] public static extern bool IsProcessorFeaturePresent(uint f);'
    $avx2 = [Native.Cpu]::IsProcessorFeaturePresent(40)   # PF_AVX2_INSTRUCTIONS_AVAILABLE
    $build = if ($avx2) { "x86-64-avx2" } else { "x86-64-sse41-popcnt" }
    New-Item -ItemType Directory -Force -Path $sfDir | Out-Null
    if ($Kit) {
        Write-Host "Stockfish 18 ($build) from the kit..."
        Expand-Archive -Path (Get-KitFile "stockfish-windows-$build.zip") -DestinationPath $sfDir -Force
    } else {
        Write-Host "Downloading Stockfish 18 ($build)..."
        $sfZip = Join-Path $env:TEMP "stockfish.zip"
        Invoke-WebRequest "https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-$build.zip" -OutFile $sfZip -UseBasicParsing
        Expand-Archive -Path $sfZip -DestinationPath $sfDir -Force
        Remove-Item $sfZip
    }
    $sfExe = Get-ChildItem $sfDir -Recurse -Filter "stockfish*.exe" | Select-Object -First 1
}

# 4. node.env (the token stays on this machine; only Administrators and SYSTEM can read it)
$name = ($env:COMPUTERNAME).ToLower()
@"
SERVER=$Server
TOKEN=$Token
NODE=$name
WORKERS=$Workers
STOCKFISH_PATH=$($sfExe.FullName)
"@ | Set-Content -Encoding ascii "$Root\node.env"
icacls "$Root\node.env" /inheritance:r /grant:r "Administrators:F" "SYSTEM:F" | Out-Null

# 5. Start at boot, as SYSTEM, and come back after a crash; the machine must not sleep while it works.
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Root\run-node.ps1`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask -TaskName "Sarce Node" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "Sarce Node"
Write-Host ""
Write-Host "Sarce Node is running ($Workers engines). Log: $Root\node.log"
Write-Host "Tip: in the BIOS, set 'Restore on AC power loss' to 'Power On' so the desktop starts by itself after an outage."
