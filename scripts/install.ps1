<#
.SYNOPSIS
    Set up claude-3d-harness on this machine.
.DESCRIPTION
    Runs `uv run scripts/harness.py setup`, which:
    1. Checks out every upstream submodule at its pinned commit.
    2. Writes .mcp.json for the chosen Blender MCP provider (one server, named "blender").
    3. Downloads, checksums and installs the provider's Blender extension, if Blender is found.
    4. Runs the environment and registry checks.
    All logic lives in scripts/harness.py; this file only checks the two tools it needs and passes the switches on.
    On macOS and Linux, run the same command directly: uv run scripts/harness.py setup
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

Assert-Tool git 'Install Git for Windows from https://git-scm.com/download/win'
Assert-Tool uv  'Install uv from https://docs.astral.sh/uv/getting-started/installation/'

$setupArgs = @('setup', '--provider', $Mcp)
if ($BlenderPath) { $setupArgs += @('--blender', $BlenderPath) }
if ($SkipBlenderExtension) { $setupArgs += '--skip-blender-extension' }

& uv run scripts/harness.py @setupArgs
exit $LASTEXITCODE
