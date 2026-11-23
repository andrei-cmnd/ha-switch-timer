<#
One-command Switch Timer test environment (official Home Assistant image, no dev container).

  scripts\test-env.ps1 up [-FirstInstall]       build, start, wait, print the URL
  scripts\test-env.ps1 reset [-FirstInstall]    wipe the test volume and start fresh
  scripts\test-env.ps1 down                     stop (the volume is kept)
  scripts\test-env.ps1 logs                     follow Home Assistant's log
  scripts\test-env.ps1 verify [-FirstInstall | -Provisioned]
                                                reset + Playwright checks -> verify-report\report.md
                                                (both modes when no switch is given)

-FirstInstall: onboarding only; you add the hub (Add integration -> Switch Timer -> Submit)
               and the cards yourself.
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "reset", "down", "logs", "verify")]
    [string]$Command = "up",
    [switch]$FirstInstall,
    [switch]$Provisioned
)

# Windows PowerShell 5.1 turns any stderr output of a program (docker writes progress there) into an
# error under "Stop", so keep "Continue" and check exit codes ($LASTEXITCODE) explicitly.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Container = "ha-switch-timer-test"
$Provisioner = "ha-switch-timer-test-provision"
$Network = "ha-switch-timer-test_default"
$Url = "http://localhost:8123"
$PlaywrightVersion = "1.64.1"
$PlaywrightImage = "mcr.microsoft.com/playwright:v$PlaywrightVersion-noble"
$env:HA_VERSION = ((Select-String -Path "requirements.txt" -Pattern '^homeassistant==(.+)$').Matches[0].Groups[1].Value).Trim()

function Invoke-Compose {
    & docker compose -f test-env/docker-compose.yml @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $args failed" }
}

function Get-PortOwner {
    # Who holds port 8123, other than our own test container; $null if free.
    $running = & docker ps -q --filter "name=^${Container}$" --filter status=running
    if ($running) { return $null }
    $name = & docker ps --filter publish=8123 --format '{{.Names}}' | Select-Object -First 1
    if ($name) { return "the Docker container `"$name`"" }
    $listener = Get-NetTCPConnection -LocalPort 8123 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        $procName = "process $($listener.OwningProcess)"
        if ($proc) { $procName = $proc.ProcessName }
        return "another program ($procName; often the dev container's Home Assistant, forwarded by VS Code)"
    }
    return $null
}

function Wait-Ready {
    Write-Host "Waiting for Home Assistant and provisioning..."
    $code = (& docker wait $Provisioner).Trim()
    if ($code -ne "0") {
        & docker logs $Provisioner
        throw "Provisioning failed (exit $code). Logs: scripts\test-env.ps1 logs"
    }
    & docker logs $Provisioner | ForEach-Object { "  $_" }
    for ($i = 0; $i -lt 90; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/manifest.json" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    }
    throw "Home Assistant did not answer on $Url"
}

function Start-TestEnv([string]$Mode) {
    $owner = Get-PortOwner
    if ($owner) {
        Write-Host "Port 8123 is already in use by $owner." -ForegroundColor Red
        Write-Host "Stop it first (in VS Code: stop the `"Run Home Assistant on port 8123`" task or close the dev"
        Write-Host "container), then run: scripts\test-env.ps1 up"
        exit 1
    }
    if ($Mode -eq "first-install") { $env:PROVISION_HUB = "false" } else { $env:PROVISION_HUB = "true" }
    Write-Host "Building and starting the test environment (Home Assistant $env:HA_VERSION, $Mode mode)..."
    Invoke-Compose up -d --build
    Wait-Ready
    Write-Host ""
    Write-Host "Ready: $Url" -ForegroundColor Green
    Write-Host "  Mode: $Mode. Login is automatic from this machine (user: test / test-pass-123)."
    if ($Mode -eq "first-install") {
        Write-Host "  Next: Settings -> Devices & services -> Add integration -> Switch Timer -> Submit, then reload the page."
    } else {
        Write-Host "  Dashboard: $Url/switch-timer-test/test"
    }
}

function Reset-TestEnv([string]$Mode) {
    Write-Host "Removing the test environment and its volume..."
    Invoke-Compose down -v --remove-orphans
    Start-TestEnv $Mode
}

function Invoke-VerifyMode([string]$Mode) {
    Reset-TestEnv $Mode
    Write-Host ""
    Write-Host "Running the Playwright checks ($Mode)..."
    $script = "mkdir -p /tmp/verify && cd /tmp/verify && npm init -y >/dev/null && npm install --no-audit --no-fund --silent playwright@$PlaywrightVersion && cp /verify/*.mjs . && node run.mjs"
    & docker run --rm --network $Network --ipc=host -e HOME=/tmp -e "HA_URL=http://${Container}:8123" -e "MODE=$Mode" -e REPORT_DIR=/report `
        -v "${Root}\test-env\verify:/verify:ro" -v "${Root}\verify-report:/report" $PlaywrightImage bash -c $script
    return ($LASTEXITCODE -eq 0)
}

function Invoke-Verify {
    New-Item -ItemType Directory -Force "verify-report" | Out-Null
    Remove-Item "verify-report\*.json", "verify-report\*.png", "verify-report\report.md" -ErrorAction SilentlyContinue
    $modes = @("first-install", "provisioned") # ends in provisioned mode, ready to inspect
    if ($FirstInstall) { $modes = @("first-install") }
    if ($Provisioned) { $modes = @("provisioned") }
    $allOk = $true
    foreach ($mode in $modes) {
        if (-not (Invoke-VerifyMode $mode)) { $allOk = $false }
    }
    & docker run --rm -e REPORT_DIR=/report -e "PLAYWRIGHT_VERSION=$PlaywrightVersion" `
        -v "${Root}\test-env\verify:/verify:ro" -v "${Root}\verify-report:/report" $PlaywrightImage node /verify/assemble.mjs
    Write-Host "Report: verify-report\report.md"
    if (-not $allOk) { exit 1 }
}

$mode = "provisioned"
if ($FirstInstall) { $mode = "first-install" }

switch ($Command) {
    "up" { Start-TestEnv $mode }
    "reset" { Reset-TestEnv $mode }
    "down" { Invoke-Compose down }
    "logs" { & docker logs -f $Container }
    "verify" { Invoke-Verify }
}
