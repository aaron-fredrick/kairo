# Stop a compose profile.
#   .\scripts\compose-down.ps1 local
param(
    [Parameter(Position = 0)]
    [string]$Profile = "local"
)

. "$PSScriptRoot\lib\Compose-Lib.ps1"
$composeArgs = @("down") + @($args)
Invoke-Compose -Profile $Profile -ComposeArgs $composeArgs
