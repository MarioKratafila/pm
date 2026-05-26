$ErrorActionPreference = 'Stop'

Write-Host 'Stopping container...'
docker stop pm-app-container | Out-Null

Write-Host 'Removing container...'
docker rm pm-app-container | Out-Null

Write-Host 'Stopped pm-app-container.'
