# Show containers for a profile.
param(
    [Parameter(Position = 0)]
    [string]$Profile = "local"
)

. "$PSScriptRoot\lib\Compose-Lib.ps1"
Invoke-Compose -Profile $Profile -ComposeArgs (@("ps") + @($args))
