# Tail logs for a profile.
#   .\scripts\compose-logs.ps1 local-dev app-backend -f
param(
    [Parameter(Position = 0)]
    [string]$Profile = "local"
)

. "$PSScriptRoot\lib\Compose-Lib.ps1"
Invoke-Compose -Profile $Profile -ComposeArgs (@("logs") + @($args))
