$ErrorActionPreference = "Stop"

if (-not (Test-Path "venv")) {
    py -m venv venv
}

& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

python manage.py check

Write-Host ""
Write-Host "Backend dependencies are installed and Django checks passed."
Write-Host "Because this project is designed to reuse your EXISTING PostgreSQL trevorio database,"
Write-Host "the setup script intentionally does NOT run makemigrations or migrate."
Write-Host ""
Write-Host "Useful checks:"
Write-Host "  python manage.py showmigrations accounts"
Write-Host "  python manage.py showmigrations data_sources"
Write-Host "  python manage.py check_trevor_schema"
Write-Host ""
Write-Host "Start server:"
Write-Host "  python manage.py runserver"
