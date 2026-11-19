param($n)
Set-Location C:\projects\active\sr-drawing-pack\research\_local\logs
Remove-Item "$n.out" -EA SilentlyContinue
Start-Process python -ArgumentList "fx.py","$n.py" -RedirectStandardOutput "$n.out" -RedirectStandardError "$n.err" -WindowStyle Hidden
