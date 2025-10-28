#Requires -Version 7.0
param()

$ErrorActionPreference = 'Continue'

function Write-Section {
    param([string]$Title)
    Write-Output "=== $Title ==="
}

Write-Section "Windows Docker Doctor"

$dockerDesktopRunning = $false
try {
    if (Get-Process -Name "Docker Desktop" -ErrorAction Stop) {
        $dockerDesktopRunning = $true
        Write-Output "Docker Desktop process: running"
    }
} catch {
    Write-Output "Docker Desktop process: not running"
}

$wslRaw = & wsl.exe -l -v 2>&1
Write-Output "WSL distros (wsl.exe -l -v):"
Write-Output $wslRaw

$distros = @()
foreach ($line in $wslRaw -split "`r?`n") {
    $trim = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trim)) { continue }
    if ($trim -match '^(NAME\s+STATE\s+VERSION)') { continue }
    if ($trim.StartsWith('*')) { $trim = $trim.Substring(1).Trim() }
    $parts = $trim -split '\s{2,}'
    if ($parts.Length -ge 3) {
        $distros += [pscustomobject]@{
            Name    = $parts[0]
            State   = $parts[1]
            Version = $parts[2]
        }
    }
}

$integrationHint = "Open Docker Desktop → Settings → Resources → WSL Integration → enable your distro."

$status = if ($dockerDesktopRunning) { "ok" } else { "error" }

$payload = [ordered]@{
    status                 = $status
    docker_desktop_running = $dockerDesktopRunning
    wsl_distros            = $distros
    integration_hint       = $integrationHint
}

$payload | ConvertTo-Json -Depth 4 -Compress

if (-not $dockerDesktopRunning) {
    exit 1
}
