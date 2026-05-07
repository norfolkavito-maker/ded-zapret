$ErrorActionPreference = "Stop"

Write-Host "== Agent verification started =="

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

Write-Host "== Environment =="
Write-Host "PWD: $(Get-Location)"

if (Test-CommandExists "git") {
    git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "== Git status =="
        git status --short
    } else {
        Write-Host "Not inside a git repository; skipping git status."
    }
}

Write-Host "== Dangerous pattern scan (warnings only) =="
$patterns = @(
    "shell=True",
    "extractall(",
    "C:\Users\",
    "token=",
    "password=",
    "uuid=",
    "subscription"
)

foreach ($p in $patterns) {
    $matches = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "\\.git|node_modules|venv|\.venv|__pycache__" } |
        Select-String -SimpleMatch -Pattern $p -ErrorAction SilentlyContinue |
        Select-Object -First 20

    if ($matches) {
        Write-Host "WARNING: pattern found: $p"
        $matches | ForEach-Object { Write-Host $_ }
    }
}

# Python project checks
if ((Test-Path "pyproject.toml") -or (Test-Path "requirements.txt") -or (Test-Path "setup.py") -or (Test-Path "tests")) {
    if (Test-CommandExists "python") {
        Write-Host "== Python version =="
        python --version

        Write-Host "== Python compile check =="
        python -m compileall .

        if (Test-Path "tests") {
            Write-Host "== Python unittest discovery =="
            python -m unittest discover -s tests -p "*_unittest.py"
        }

        $pyprojectMentionsPytest = $false
        if (Test-Path "pyproject.toml") {
            $pyprojectMentionsPytest = $null -ne (Select-String -Path "pyproject.toml" -Pattern "pytest" -ErrorAction SilentlyContinue)
        }
        if ((Test-Path "pytest.ini") -or $pyprojectMentionsPytest) {
            Write-Host "== Pytest =="
            python -m pytest -q
        }
    } else {
        Write-Host "Python not found; skipping Python checks."
    }
}

# Node project checks
if ((Test-Path "package.json") -and (Test-CommandExists "npm")) {
    Write-Host "== Node dependencies check =="
    if (Test-Path "package-lock.json") {
        npm ci
    } else {
        npm install
    }

    $packageJson = Get-Content "package.json" -Raw

    if ($packageJson -match '"lint"\s*:') {
        Write-Host "== npm run lint =="
        npm run lint
    }

    if ($packageJson -match '"test"\s*:') {
        Write-Host "== npm test =="
        npm test
    }

    if ($packageJson -match '"build"\s*:') {
        Write-Host "== npm run build =="
        npm run build
    }
}

# .NET project checks
if ((Get-ChildItem -Recurse -Filter "*.csproj" -ErrorAction SilentlyContinue | Select-Object -First 1) -and (Test-CommandExists "dotnet")) {
    Write-Host "== dotnet restore =="
    dotnet restore

    Write-Host "== dotnet build =="
    dotnet build --no-restore

    Write-Host "== dotnet test =="
    dotnet test --no-build
}

# Rust project checks
if ((Test-Path "Cargo.toml") -and (Test-CommandExists "cargo")) {
    Write-Host "== cargo test =="
    cargo test
}

Write-Host "== Agent verification passed =="
