$ErrorActionPreference = 'Stop'

Set-Location -Path $PSScriptRoot\..\

Write-Host 'Building frontend...'
Set-Location -Path .\frontend
npm install
npm run build

Set-Location -Path ..\

Write-Host 'Building Docker image...'
docker build -t pm-app .

Write-Host 'Starting container...'
docker run --rm -d -p 8000:8000 --name pm-app-container pm-app

Write-Host 'Application should be available at http://localhost:8000'
