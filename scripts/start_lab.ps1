$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
New-Item -ItemType Directory -Force -Path .approvaltrace | Out-Null
python -m approvaltrace.cli capture-api --root .approvaltrace
