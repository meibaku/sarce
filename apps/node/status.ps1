# Sarce Node status (ADR 0010): a live view of this node and the whole analysis queue, redrawn every 2 seconds.
# Open it from the "Sarce Node status" shortcut on the Desktop; Ctrl+C closes it. It only reads the small files the
# node writes in C:\SarceNode\status (no token, no admin), so it costs the laptop nothing extra.
param([int]$Every = 2, [switch]$Once)  # -Once: print one frame (also when output is not a console)
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)   # C:\SarceNode
$statusDir = Join-Path $root "status"
$log = Join-Path $root "node.log"
$plain = $Once -or [Console]::IsOutputRedirected
if (-not $plain) { $Host.UI.RawUI.WindowTitle = "Sarce Node status"; [Console]::CursorVisible = $false }

function Read-Json($path) { try { Get-Content $path -Raw -ErrorAction Stop | ConvertFrom-Json } catch { $null } }
function Ago([double]$epoch) {
    if (-not $epoch) { return "never" }
    $s = [int]((Get-Date).ToUniversalTime() - [DateTime]::new(1970, 1, 1, 0, 0, 0, [DateTimeKind]::Utc).AddSeconds($epoch)).TotalSeconds
    if ($s -lt 60) { return "${s}s ago" } elseif ($s -lt 3600) { return "$([int]($s / 60))m ago" } else { return "$([math]::Round($s / 3600, 1))h ago" }
}
function Dur([double]$seconds) { if ($seconds -lt 60) { "{0}s" -f [int]$seconds } else { "{0}m{1:00}s" -f [int][math]::Floor($seconds / 60), [int]($seconds % 60) } }
function Bar([double]$fraction, [int]$width = 20) {
    $full = [int][math]::Round([math]::Max(0.0, [math]::Min(1.0, [double]$fraction)) * $width)  # doubles: Min(1, x) would pick the Int32 overload
    return ("#" * $full) + ("." * ($width - $full))
}
function N($n) { if ($null -eq $n) { "-" } else { "{0:N0}" -f $n } }

try {
    while ($true) {
        $lines = New-Object System.Collections.Generic.List[string]
        $server = Read-Json (Join-Path $statusDir "server.json")
        $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        if (-not $server) {
            $lines.Add("Sarce Node: no status yet. Is the 'Sarce Node' task running? (log: $log)")
        } else {
            $link = if ($server.ok) { "connected" } else { "NOT REACHABLE ($($server.error)); last answer $(Ago $server.lastOk)" }
            $stale = if ($now - $server.at -gt 30) { "  (node not writing status: is the task running?)" } else { "" }
            $lines.Add("SARCE NODE  $($server.node)  |  laptop $($server.server): $link$stale")
            $lines.Add("bundle $($server.bundle)  |  $($server.engines) engines  |  $(Get-Date -Format 'HH:mm:ss')")
            $lines.Add("")
            if ($server.queue) {
                $q = $server.queue
                $done = [double]$q.complete; $total = [math]::Max(1, [double]$q.total)
                $lines.Add(("QUEUE      {0} done of {1}  [{2}] {3:P0}" -f (N $q.complete), (N $q.total), (Bar ($done / $total) 30), ($done / $total)))
                $eta = if ($server.etaHours) { if ($server.etaHours -ge 48) { "{0:N1} days" -f ($server.etaHours / 24) } else { "{0:N1} h" -f $server.etaHours } } else { "-" }
                $lines.Add(("           {0} left  |  {1} analysing now  |  {2} failed  |  about {3} to go" -f (N $q.pending), (N $q.processing), (N $q.failed), $eta))
                $r = $server.rates
                $lines.Add(("SPEED      {0} games/h finished  =  {1} by the laptop's engine  +  {2} searched by nodes" -f (N $r.allPerHour), (N $r.serverPerHour), (N $r.nodesPerHour)))
                foreach ($m in $server.machines) {
                    $lines.Add(("           {0,-18} {1} engines  searched {2,4} in the last hour, {3,5} today  {4,7} positions today" -f $m.machine, $m.engines, (N $m.searchedLastHour), (N $m.searchedToday), (N $m.positionsToday)))
                }
            }
        }
        $lines.Add("")
        $lines.Add("THIS MACHINE'S ENGINES")
        $engines = Get-ChildItem $statusDir -Filter "engine-*.json" -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object { Read-Json $_.FullName }
        if (-not $engines) { $lines.Add("  none running yet") }
        foreach ($e in $engines) {
            $tag = "  engine {0}" -f $e.engine
            $today = "{0} today, last {1}" -f (N $e.gamesToday), $(if ($e.lastGameSeconds) { Dur $e.lastGameSeconds } else { "-" })
            if ($now - $e.at -gt 120) { $lines.Add("$tag  quiet for $(Ago $e.at)  |  $today"); continue }
            switch ($e.state) {
                "searching" {
                    $frac = if ($e.total) { $e.done / $e.total } else { 0 }
                    $lines.Add(("{0}  game {1}  positions {2,3}/{3,-3} [{4}] {5,4:P0}  {6}  |  {7}" -f $tag, $e.gameId.Substring(0, 8), $e.done, $e.total, (Bar $frac), $frac, (Dur ($now - $e.startedAt)), $today))
                }
                "threats" { $lines.Add(("{0}  game {1}  checking threats ({2})  {3}  |  {4}" -f $tag, $e.gameId.Substring(0, 8), $e.threatsDone, (Dur ($now - $e.startedAt)), $today)) }
                "idle" { $lines.Add("$tag  idle: nothing left to search  |  $today") }
                default { $lines.Add("$tag  asking the laptop for a game  |  $today") }
            }
        }
        $lines.Add("")
        try {
            $cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
            $os = Get-CimInstance Win32_OperatingSystem
            $used = 1 - $os.FreePhysicalMemory / $os.TotalVisibleMemorySize
            $lines.Add(("COMPUTER   CPU {0,3:N0}%  [{1}]   memory {2:P0} of {3:N1} GB" -f $cpu, (Bar ($cpu / 100) 15), $used, ($os.TotalVisibleMemorySize / 1MB)))
        } catch {}
        if (Test-Path $log) {
            $last = Get-Content $log -Tail 1 -ErrorAction SilentlyContinue
            if ($last) { $lines.Add("LAST LOG   " + $last.Trim()) }
        }
        $lines.Add("")
        $lines.Add("Ctrl+C to close  |  refreshes every $Every s  |  log: $log")

        if ($plain) { $lines | ForEach-Object { Write-Output $_ }; break }
        # Redraw in place (no flicker): every line padded to the window width, then blank the rest.
        $width = [math]::Max(40, $Host.UI.RawUI.WindowSize.Width - 1)
        [Console]::SetCursorPosition(0, 0)
        foreach ($l in $lines) { $text = if ($l.Length -gt $width) { $l.Substring(0, $width) } else { $l.PadRight($width) }; [Console]::WriteLine($text) }
        $rows = $Host.UI.RawUI.WindowSize.Height
        for ($i = $lines.Count; $i -lt $rows - 1; $i++) { [Console]::WriteLine("".PadRight($width)) }
        Start-Sleep -Seconds $Every
    }
} finally {
    if (-not $plain) { [Console]::CursorVisible = $true }
}
