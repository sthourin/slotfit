<#
.SYNOPSIS
    Restores the SlotFit development environment on a new machine from the
    transition bundle staged alongside this script.

.DESCRIPTION
    Runs the procedure documented in RESTORE.md:
      1. Clones the repo and checks out the working branch
      2. Drops the gitignored config and personal data files into place
      3. Starts the PostgreSQL container and restores the database dump
      4. Verifies the restored row counts against the dump-time figures
      5. Recreates the empty e2e database
      6. Rebuilds the backend venv and web node_modules

    Safe to re-run. Existing files are never overwritten and a database that
    already holds data is never restored over, unless -Force is supplied.

.PARAMETER RepoPath
    Where the repo lives (or will be cloned). Default C:\projects\slotfit.

.PARAMETER Force
    Overwrite existing config files and restore over a non-empty database.

.PARAMETER Yes
    Skip the confirmation prompt.

.EXAMPLE
    .\Restore-SlotFit.ps1

.EXAMPLE
    .\Restore-SlotFit.ps1 -RepoPath D:\src\slotfit -SkipDeps
#>

[CmdletBinding()]
param(
    [string] $RepoPath = 'C:\projects\slotfit',
    # Everything was merged to main and feat/hevy-staple-seeding was deleted on
    # 2026-09-05. Checking that branch out now fails outright.
    [string] $Branch   = 'main',
    [switch] $SkipClone,
    [switch] $SkipFiles,
    [switch] $SkipDatabase,
    [switch] $SkipDeps,
    [switch] $Force,
    [switch] $Yes
)

$ErrorActionPreference = 'Stop'

$Bundle    = $PSScriptRoot
$RepoUrl   = 'https://github.com/sthourin/slotfit.git'
$Container = 'slotfit-db'
$DumpFile  = Join-Path $Bundle 'slotfit-db-2026-09-05.dump'
$MemoryDir = Join-Path $env:USERPROFILE '.claude\projects\c--projects-slotfit\memory'

# Alembic revision the dump was taken at. After restoring, `alembic current`
# must report this and `alembic upgrade head` must be a no-op; anything else
# means the dump and the checkout have drifted.
$ExpectedRevision = 'a3d81b6e4f27'

# Row counts captured when the dump was taken, used to verify the restore.
#
# These verify the restore was faithful to THE DUMP, not that the dump was
# current. A stale dump passes this check cleanly. Whenever a fresh dump is
# taken, update both this block and the matching table in RESTORE.md, or the
# next restore will silently certify old data as correct.
$Expected = [ordered]@{
    exercises           = 3267
    workout_sessions    = 228
    workout_exercises   = 932
    workout_sets        = 2959
    training_sessions   = 6
    round_entries       = 17
    entry_sets          = 15
    bodyweight_readings = 14
    day_plans           = 2
    movement_patterns   = 10
    staple_exercises    = 57
    users               = 12
}

$script:Warnings = @()

function Write-Step { param([string] $Message) Write-Host "`n== $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string] $Message) Write-Host "   $Message" -ForegroundColor Green }
function Write-Skip { param([string] $Message) Write-Host "   skipped: $Message" -ForegroundColor DarkGray }

function Write-Warn {
    param([string] $Message)
    Write-Host "   warning: $Message" -ForegroundColor Yellow
    $script:Warnings += $Message
}

function Assert-Native {
    param([string] $What)
    if ($LASTEXITCODE -ne 0) { throw "$What failed with exit code $LASTEXITCODE" }
}

function Test-Tool {
    param([string] $Name)
    return [bool] (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Copy-BundleFile {
    param([string] $Source, [string] $Destination)

    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Warn "missing from bundle: $(Split-Path $Source -Leaf)"
        return
    }

    $parent = Split-Path $Destination -Parent
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
        $same = (Get-FileHash -LiteralPath $Source).Hash -eq (Get-FileHash -LiteralPath $Destination).Hash
        if ($same) {
            Write-Skip "$Destination (already identical)"
        } else {
            Write-Warn "$Destination exists and differs - left alone, re-run with -Force to overwrite"
        }
        return
    }

    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Write-Ok "$Destination"
}

function Get-Scalar {
    param([string] $Database, [string] $Sql)
    $out = docker exec $Container psql -U postgres -d $Database -Atc $Sql 2>&1
    return ($out | Out-String).Trim()
}


# --------------------------------------------------------------- preflight --

Write-Step 'Preflight'

if (-not (Test-Path -LiteralPath $DumpFile)) {
    throw "Database dump not found at $DumpFile. Run this script from inside the bundle directory."
}
Write-Ok "bundle: $Bundle"

$missing = @()
foreach ($tool in @('git', 'docker')) {
    if (-not (Test-Tool $tool)) { $missing += $tool }
}
if ($missing.Count -gt 0) {
    throw "Required tool(s) not on PATH: $($missing -join ', '). Install them, then re-run."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker is installed but the daemon is not responding. Start Docker Desktop, then re-run.'
}
Write-Ok 'git and docker available, daemon responding'

if (-not $SkipDeps -and -not (Test-Tool 'python')) {
    Write-Warn 'python not on PATH - dependency step will be skipped'
    $SkipDeps = $true
}

Write-Host ''
Write-Host 'Plan:' -ForegroundColor White
Write-Host "  repo         $RepoPath (branch $Branch)"
if ($SkipClone)    { Write-Host '  clone        skip' }        else { Write-Host "  clone        $RepoUrl" }
if ($SkipFiles)    { Write-Host '  config/data  skip' }        else { Write-Host '  config/data  env files, hevy export, vscode settings, claude memory' }
if ($SkipDatabase) { Write-Host '  database     skip' }        else { Write-Host "  database     restore $(Split-Path $DumpFile -Leaf) into container $Container" }
if ($SkipDeps)     { Write-Host '  deps         skip' }        else { Write-Host '  deps         backend venv + pip, web npm install' }
Write-Host "  force        $($Force.IsPresent)"

if (-not $Yes) {
    $answer = Read-Host "`nProceed? [y/N]"
    if ($answer -notmatch '^[Yy]') { Write-Host 'Aborted.'; return }
}


# ------------------------------------------------------------------- clone --

Write-Step 'Repository'

if ($SkipClone) {
    Write-Skip 'clone (-SkipClone)'
    if (-not (Test-Path -LiteralPath $RepoPath)) {
        throw "-SkipClone was given but $RepoPath does not exist"
    }
}
elseif (Test-Path -LiteralPath (Join-Path $RepoPath '.git')) {
    Write-Skip "clone - $RepoPath is already a git repo"
}
else {
    if ((Test-Path -LiteralPath $RepoPath) -and
        (Get-ChildItem -LiteralPath $RepoPath -Force | Select-Object -First 1)) {
        throw "$RepoPath exists and is not empty, but is not a git repo. Move it aside or pass -SkipClone."
    }
    git clone $RepoUrl $RepoPath
    Assert-Native 'git clone'
    Write-Ok "cloned into $RepoPath"
}

Push-Location $RepoPath
try {
    $current = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($current -ne $Branch) {
        git checkout $Branch
        Assert-Native "git checkout $Branch"
    }
    $head = (git rev-parse --short HEAD).Trim()
    $now  = (git rev-parse --abbrev-ref HEAD).Trim()
    Write-Ok "on branch $now at $head"
}
finally { Pop-Location }


# ----------------------------------------------------------- config + data --

Write-Step 'Config and personal data'

if ($SkipFiles) {
    Write-Skip '-SkipFiles'
}
else {
    Copy-BundleFile (Join-Path $Bundle 'slotfit-.env')                 (Join-Path $RepoPath '.env')
    Copy-BundleFile (Join-Path $Bundle 'slotfit-.env.e2e')             (Join-Path $RepoPath '.env.e2e')
    Copy-BundleFile (Join-Path $Bundle 'slotfit-vscode-settings.json') (Join-Path $RepoPath '.vscode\settings.json')

    $hevySrc = Join-Path $Bundle 'hevy-data'
    if (Test-Path -LiteralPath $hevySrc) {
        foreach ($f in Get-ChildItem -LiteralPath $hevySrc -Filter '*.json') {
            Copy-BundleFile $f.FullName (Join-Path $RepoPath "hevy\data\$($f.Name)")
        }
    } else {
        Write-Warn 'hevy-data\ missing from bundle'
    }

    $memSrc = Join-Path $Bundle 'claude-memory'
    if (Test-Path -LiteralPath $memSrc) {
        foreach ($f in Get-ChildItem -LiteralPath $memSrc -Filter '*.md') {
            Copy-BundleFile $f.FullName (Join-Path $MemoryDir $f.Name)
        }
    } else {
        Write-Warn 'claude-memory\ missing from bundle'
    }
}


# ---------------------------------------------------------------- database --

if ($SkipDatabase) {
    Write-Step 'Database'
    Write-Skip '-SkipDatabase'
}
else {
    Write-Step 'PostgreSQL container'

    $composeDir = Join-Path $RepoPath 'backend'
    if (-not (Test-Path -LiteralPath (Join-Path $composeDir 'docker-compose.yml'))) {
        throw "docker-compose.yml not found in $composeDir"
    }

    Push-Location $composeDir
    try {
        docker compose up -d
        Assert-Native 'docker compose up'
    }
    finally { Pop-Location }

    Write-Host '   waiting for postgres to accept connections' -NoNewline
    $ready = $false
    foreach ($i in 1..60) {
        docker exec $Container pg_isready -U postgres *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 2
    }
    Write-Host ''
    if (-not $ready) { throw "Container $Container did not become ready within 120 seconds." }
    Write-Ok "container $Container ready"

    Write-Step 'Database restore'

    # compose creates the database on first volume init only; make sure it is there.
    if (-not (Get-Scalar 'postgres' "SELECT 1 FROM pg_database WHERE datname='slotfit';")) {
        docker exec $Container psql -U postgres -c 'CREATE DATABASE slotfit;' | Out-Null
        Assert-Native 'CREATE DATABASE slotfit'
        Write-Ok 'created empty database slotfit'
    }

    $tableCount = [int] (Get-Scalar 'slotfit' "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r';")

    if ($tableCount -gt 0 -and -not $Force) {
        Write-Warn "database slotfit already has $tableCount tables - not restoring over it. Re-run with -Force to replace its contents."
    }
    else {
        docker cp $DumpFile "${Container}:/tmp/slotfit-restore.dump"
        Assert-Native 'docker cp'

        # --clean only matters when replacing an existing schema.
        if ($tableCount -gt 0) {
            docker exec $Container pg_restore -U postgres -d slotfit --clean --if-exists --no-owner /tmp/slotfit-restore.dump
        } else {
            docker exec $Container pg_restore -U postgres -d slotfit --no-owner /tmp/slotfit-restore.dump
        }
        # pg_restore exits non-zero on warnings too; the row-count check below is the real verdict.
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "pg_restore exited $LASTEXITCODE - see messages above; verifying row counts"
        }

        docker exec $Container rm -f /tmp/slotfit-restore.dump | Out-Null
        Write-Ok 'dump applied'

        Write-Step 'Verifying restored data'
        $bad = @()
        foreach ($table in $Expected.Keys) {
            $want = $Expected[$table]
            $got  = Get-Scalar 'slotfit' "SELECT count(*) FROM $table;"
            if ($got -match '^\d+$' -and [int] $got -eq $want) {
                Write-Host ("   {0,-20} {1,6}  ok" -f $table, $got) -ForegroundColor Green
            } else {
                Write-Host ("   {0,-20} {1,6}  expected {2}" -f $table, $got, $want) -ForegroundColor Red
                $bad += $table
            }
        }
        if ($bad.Count -gt 0) {
            throw "Row counts do not match the dump for: $($bad -join ', '). The restore is incomplete."
        }
        Write-Ok 'all row counts match the dump'

        # Schema version, checked separately from the row counts: a dump can
        # carry the right rows at the wrong revision, and the mismatch only
        # surfaces later as a confusing Alembic error.
        $rev = Get-Scalar 'slotfit' "SELECT version_num FROM alembic_version;"
        if ($rev -eq $ExpectedRevision) {
            Write-Ok "alembic revision $rev"
        } else {
            Write-Warn "alembic revision is '$rev', expected '$ExpectedRevision' - run 'alembic current' and reconcile before using this database"
        }
    }

    # e2e database: intentionally not dumped, created empty here.
    Write-Step 'E2E database'
    if (Get-Scalar 'postgres' "SELECT 1 FROM pg_database WHERE datname='slotfit_e2e';") {
        Write-Skip 'slotfit_e2e already exists'
    } else {
        docker exec $Container psql -U postgres -c 'CREATE DATABASE slotfit_e2e;' | Out-Null
        Assert-Native 'CREATE DATABASE slotfit_e2e'
        Write-Ok 'created empty slotfit_e2e - run migrations against it with E2E_DATABASE_URL set'
    }
}


# ------------------------------------------------------------------- deps --

Write-Step 'Dependencies'

if ($SkipDeps) {
    Write-Skip '-SkipDeps'
}
else {
    $backend = Join-Path $RepoPath 'backend'
    $venvPy  = Join-Path $backend 'venv\Scripts\python.exe'

    if (Test-Path -LiteralPath $venvPy) {
        Write-Skip 'backend\venv already exists'
    } else {
        Push-Location $backend
        try {
            python -m venv venv
            Assert-Native 'python -m venv'
        }
        finally { Pop-Location }
        Write-Ok 'created backend\venv'
    }

    & $venvPy -m pip install --upgrade pip --quiet
    & $venvPy -m pip install -r (Join-Path $backend 'requirements.txt')
    Assert-Native 'pip install -r requirements.txt'
    Write-Ok 'backend dependencies installed'

    if (Test-Tool 'npm') {
        Push-Location (Join-Path $RepoPath 'web')
        try {
            npm install
            Assert-Native 'npm install'
        }
        finally { Pop-Location }
        Write-Ok 'web dependencies installed'
    } else {
        Write-Warn 'npm not on PATH - run "npm install" in web\ manually'
    }
}


# ---------------------------------------------------------------- summary --

Write-Step 'Done'

if ($script:Warnings.Count -gt 0) {
    Write-Host "   completed with $($script:Warnings.Count) warning(s):" -ForegroundColor Yellow
    foreach ($w in $script:Warnings) { Write-Host "     - $w" -ForegroundColor Yellow }
} else {
    Write-Host '   completed with no warnings' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor White
Write-Host "  1. Backend:  cd $RepoPath\backend; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Write-Host "  2. Web:      cd $RepoPath\web; npm run dev"
Write-Host '  3. Delete slotfit-.env and slotfit-.env.e2e from the bundle - they hold live API keys.'
Write-Host ''
Write-Host 'The restored dump already contains the pattern and leverage seed data.'
Write-Host 'Only a from-scratch database needs: alembic upgrade head, then'
Write-Host 'python -m scripts.seed_patterns and python -m scripts.seed_leverage.'
