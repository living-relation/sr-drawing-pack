param($n)
if (-not $env:SRDP_ROOT) { throw "Set SRDP_ROOT to your sr-drawing-pack clone" }
Set-Location (Join-Path $env:SRDP_ROOT "research\_local\logs")
Remove-Item "$n.out" -EA SilentlyContinue
Start-Process python -ArgumentList "fx.py","$n.py" -RedirectStandardOutput "$n.out" -RedirectStandardError "$n.err" -WindowStyle Hidden
