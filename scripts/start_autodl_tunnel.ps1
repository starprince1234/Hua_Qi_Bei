param(
    [string]$PlinkPath = $env:AUTODL_PLINK_PATH
)

$ErrorActionPreference = "Stop"

function Require-Env {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing required environment variable: $Name"
    }
    return $Value
}

$HostName = Require-Env "AUTODL_SSH_HOST"
$Port = Require-Env "AUTODL_SSH_PORT"
$User = Require-Env "AUTODL_SSH_USER"
$Password = Require-Env "AUTODL_SSH_PASSWORD"
$LocalPort = Require-Env "AUTODL_LOCAL_PORT"
$RemoteHost = Require-Env "AUTODL_REMOTE_HOST"
$RemotePort = Require-Env "AUTODL_REMOTE_PORT"
$HostKey = [Environment]::GetEnvironmentVariable("AUTODL_PLINK_HOSTKEY")

if ([string]::IsNullOrWhiteSpace($PlinkPath)) {
    $Command = Get-Command "plink.exe" -ErrorAction SilentlyContinue
    if ($null -eq $Command) {
        throw "plink.exe not found. Set AUTODL_PLINK_PATH in Doppler, for example D:\PuTTY\plink.exe"
    }
    $PlinkPath = $Command.Source
}

if (-not (Test-Path -LiteralPath $PlinkPath)) {
    throw "plink.exe path does not exist: $PlinkPath"
}

$ExistingListener = Get-NetTCPConnection -LocalPort ([int]$LocalPort) -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
    Write-Host "Local port $LocalPort is already listening; tunnel may already be running."
    exit 0
}

$LogDir = Join-Path $PSScriptRoot "..\.tmp"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$StdoutLogPath = Join-Path $LogDir "autodl-plink.out.log"
$StderrLogPath = Join-Path $LogDir "autodl-plink.err.log"
foreach ($Path in @($StdoutLogPath, $StderrLogPath)) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force
    }
}

$Arguments = @(
    "-batch",
    "-ssh",
    "-N",
    "-v",
    "-no-antispoof",
    "-P", $Port,
    "-pw", $Password,
    "-L", "127.0.0.1:${LocalPort}:${RemoteHost}:${RemotePort}",
    "${User}@${HostName}"
)

if (-not [string]::IsNullOrWhiteSpace($HostKey)) {
    $Arguments = @("-hostkey", $HostKey) + $Arguments
}

Write-Host "Starting AutoDL tunnel: 127.0.0.1:$LocalPort -> ${RemoteHost}:$RemotePort via ${User}@${HostName}:$Port"
$Process = Start-Process -FilePath $PlinkPath -ArgumentList $Arguments -WindowStyle Hidden -RedirectStandardError $StderrLogPath -RedirectStandardOutput $StdoutLogPath -PassThru
Start-Sleep -Seconds 3

$Listener = Get-NetTCPConnection -LocalPort ([int]$LocalPort) -State Listen -ErrorAction SilentlyContinue
if (-not $Listener) {
    $LogText = ""
    if (Test-Path -LiteralPath $StderrLogPath) {
        $LogText = Get-Content -LiteralPath $StderrLogPath -Raw -Encoding UTF8
    }
    throw "Tunnel process started with PID $($Process.Id), but local port $LocalPort is not listening yet. plink stderr log: $StderrLogPath`n$LogText"
}

Write-Host "AutoDL tunnel is listening on 127.0.0.1:$LocalPort. PID=$($Process.Id)"
