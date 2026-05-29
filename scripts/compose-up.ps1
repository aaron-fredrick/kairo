# Start a compose profile (short names supported — see scripts/README.md).
#   .\scripts\compose-up.ps1 local
#   .\scripts\compose-up.ps1 distributed --scale app-backend=2
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Profile
)

. "$PSScriptRoot\lib\Compose-Lib.ps1"
$composeArgs = @("up", "--build") + @($args)
Invoke-Compose -Profile $Profile -ComposeArgs $composeArgs
