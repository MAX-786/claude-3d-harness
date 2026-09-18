<#
.SYNOPSIS
    Set up claude-3d-harness on this machine.
.DESCRIPTION
    1. Checks out every upstream submodule at its pinned commit.
    2. Writes .mcp.json for the chosen Blender MCP provider (one server, named "blender").
    3. Downloads, checksums and installs the provider's Blender extension, if Blender is found.
    4. Runs the environment and registry checks.
    All logic lives in scripts/harness.py; this file only sequences it.
.PARAMETER Mcp
    newo-ether (default, pinned release of the structured fork) or ahujasid (the original server).
.PARAMETER BlenderPath
    Path to blender.exe when it is not in a standard location.
.PARAMETER SkipBlenderExtension
    Do not download or install anything into Blender.
.EXAMPLE
    .\scripts\install.ps1
.EXAMPLE
    .\scripts\install.ps1 -Mcp ahujasid -SkipBlenderExtension
#>
[CmdletBinding()]
param(
    [ValidateSet('newo-ether', 'ahujasid')]
    [string]$Mcp = 'newo-ether',
    [string]$BlenderPath,
    [switch]$SkipBlenderExtension
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Assert-Tool([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found on PATH. $Hint"
    }
}

function Invoke-Harness {
    & uv run scripts/harness.py @args
    if ($LASTEXITCODE -ne 0) { throw "harness.py $($args -join ' ') failed with exit code $LASTEXITCODE" }
}

Assert-Tool git 'Install Git for Windows from https://git-scm.com/download/win'
Assert-Tool uv  'Install uv from https://docs.astral.sh/uv/getting-started/installation/'

Write-Host '== 1/4  upstream submodules' -ForegroundColor Cyan
Invoke-Harness bootstrap

Write-Host "== 2/4  MCP configuration ($Mcp)" -ForegroundColor Cyan
Invoke-Harness mcp-config --provider $Mcp --write

Write-Host '== 3/4  Blender extension' -ForegroundColor Cyan
if ($SkipBlenderExtension) {
    Write-Host 'skipped (-SkipBlenderExtension)'
} else {
    $extArgs = @('install-extension')
    if ($BlenderPath) { $extArgs += @('--blender', $BlenderPath) }
    & uv run scripts/harness.py @extArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'The Blender extension was not installed. Install Blender, then re-run this script.'
    }
}

Write-Host '== 4/4  checks' -ForegroundColor Cyan
& uv run scripts/harness.py doctor
$doctor = $LASTEXITCODE
& uv run scripts/harness.py verify
if ($doctor -ne 0 -or $LASTEXITCODE -ne 0) {
    Write-Warning 'Setup finished with open issues: see the FAIL lines above.'
    exit 1
}

Write-Host ''
Write-Host 'Ready. Start Blender, check the BlenderMCP tab in the 3D View sidebar (N), then open Claude Code in this folder.' -ForegroundColor Green
