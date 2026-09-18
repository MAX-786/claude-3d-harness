<#
.SYNOPSIS
    Move upstream submodules to their branch tips and review what changed.
.DESCRIPTION
    Nothing is staged or committed. After the move the script reports, per upstream,
    a GitHub compare link, registry drift (new or removed SKILL.md files) and an
    audit of the changed files. Accept an upstream with
        uv run scripts/harness.py catalog-bump <key>
    and commit the submodule pointer together with registry/. Back out with -Rollback.
.PARAMETER Only
    Upstream keys to update (cc, gaius, kb, jo, newo). Default: all.
.PARAMETER Rollback
    Return the submodules to the commits pinned in the index.
.EXAMPLE
    .\scripts\update.ps1 -Only cc
.EXAMPLE
    .\scripts\update.ps1 -Rollback
#>
[CmdletBinding()]
param(
    [string[]]$Only = @(),
    [switch]$Rollback
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$harnessArgs = @('update') + $Only
if ($Rollback) { $harnessArgs += '--rollback' }
& uv run scripts/harness.py @harnessArgs
exit $LASTEXITCODE
