<#
.SYNOPSIS
    Check the machine (doctor) and the registry (verify). Exit code 1 on any failure.
.EXAMPLE
    .\scripts\verify.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv was not found on PATH. Install it from https://docs.astral.sh/uv/getting-started/installation/'
}

& uv run scripts/harness.py doctor
$doctor = $LASTEXITCODE
Write-Host ''
& uv run scripts/harness.py verify
if ($doctor -ne 0 -or $LASTEXITCODE -ne 0) { exit 1 }
