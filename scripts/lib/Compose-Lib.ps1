# Shared Docker Compose helpers for PowerShell.

function Get-ComposeRoot {
    $scriptsDir = Split-Path -Parent $PSScriptRoot
    Split-Path -Parent $scriptsDir
}

function Resolve-ComposeProfile {
    param([string]$Name = "local")
    switch ($Name) {
        "local" { "app-backend.local" }
        { $_ -in "local-dev", "dev" } { "app-backend.local-dev" }
        "standalone" { "app-backend.standalone" }
        "workers" { "app-backend.workers" }
        "register" { "app-register" }
        { $_ -in "distributed", "stack" } { "stack.distributed" }
        "minio" { "infra.minio" }
        { $_ -in "postgresql", "postgres" } { "infra.postgresql" }
        "redis" { "infra.redis" }
        "base" { "base" }
        default { $Name }
    }
}

function Get-ComposeFileArgs {
    param([string]$Profile)
    $root = Get-ComposeRoot
    $resolved = Resolve-ComposeProfile $Profile
    $overlay = Join-Path $root "compose\$resolved.yml"
    if (-not (Test-Path $overlay)) {
        throw "Unknown compose profile '$Profile' (resolved: $resolved)"
    }
    if ($resolved -eq "stack.distributed") {
        return @("-f", $overlay)
    }
    if ($resolved -like "infra.*") {
        return @("-f", $overlay)
    }
    if ($resolved -eq "base") {
        return @("-f", $overlay)
    }
    $base = Join-Path $root "compose\base.yml"
    return @("-f", $base, "-f", $overlay)
}

function Invoke-Compose {
    param(
        [string]$Profile,
        [string[]]$ComposeArgs = @()
    )
    $root = Get-ComposeRoot
    Set-Location $root
    $files = Get-ComposeFileArgs $Profile
    & docker compose @files @ComposeArgs
    if ($null -ne $LASTEXITCODE) { exit $LASTEXITCODE }
}
