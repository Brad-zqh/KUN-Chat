param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$logRoot = Join-Path $env:LOCALAPPDATA "KUN-Chat"
$logFile = Join-Path $logRoot "github-sync.log"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

function Write-SyncLog([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Invoke-Git([string[]]$GitArgs) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $RepoRoot @GitArgs 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "git $($GitArgs -join ' ') failed: $($output -join ' ')"
    }
    return @($output)
}

function Get-AheadBehind {
    $counts = (Invoke-Git @("rev-list", "--left-right", "--count", "main...origin/main"))[0] -split "\s+"
    return [pscustomobject]@{ Ahead = [int]$counts[0]; Behind = [int]$counts[1] }
}

function Test-StagedSecrets([string[]]$Files) {
    $credentialPattern = '(?im)^\s*(MINIMAX_API_KEY|DEEPSEEK_API_KEY|CARTESIA_API_KEY|GOOGLE_API_KEY|DEEPGRAM_API_KEY|LIVEKIT_API_SECRET|MINIMAX_VOICE_ID(?:_KUNKUN|_FENGGE)?)\s*=\s*(?!your-|devkey\s*$|secret\s*$|在本机填写\s*$|\s*$)[^#\r\n]+'
    $tokenPattern = '(?i)(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})'
    foreach ($file in $Files) {
        if ($file -match '\.(png|jpg|jpeg|gif|ico|woff2?)$') { continue }
        $content = (& git -C $RepoRoot show ":$file" 2>$null | Out-String)
        if ($content -match $credentialPattern -or $content -match $tokenPattern) {
            throw "credential-shaped value detected in staged file: $file"
        }
    }
}

$mutex = [Threading.Mutex]::new($false, "Local\KUNChatGitHubSync")
if (-not $mutex.WaitOne(0)) {
    Write-SyncLog "Skipped: another sync is already running."
    exit 0
}

try {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ".git"))) {
        throw "Not a Git repository: $RepoRoot"
    }

    Invoke-Git @("fetch", "origin", "main") | Out-Null
    $state = Get-AheadBehind
    $dirty = @((Invoke-Git @("status", "--porcelain"))).Count -gt 0

    if ($state.Behind -gt 0 -and $dirty) {
        throw "Remote changed while local files are dirty; manual conflict review required."
    }
    if ($state.Behind -gt 0 -and $state.Ahead -eq 0) {
        Invoke-Git @("pull", "--ff-only", "origin", "main") | Out-Null
        Write-SyncLog "Pulled $($state.Behind) remote commit(s)."
    } elseif ($state.Behind -gt 0 -and $state.Ahead -gt 0) {
        $rebaseOutput = & git -C $RepoRoot rebase origin/main 2>&1
        if ($LASTEXITCODE -ne 0) {
            & git -C $RepoRoot rebase --abort 2>$null | Out-Null
            throw "Automatic rebase conflicted; it was aborted. $($rebaseOutput -join ' ')"
        }
    }

    $allowedPaths = @(
        ".env.example", ".gitignore", ".github", "LICENSE", "NOTICE",
        "README.md", "pyproject.toml", "uv.lock", "assets/voice_samples/README.md",
        "docs/kunkun", "scripts", "tests", "web", "worker"
    )
    foreach ($path in $allowedPaths) {
        if (Test-Path -LiteralPath (Join-Path $RepoRoot $path)) {
            Invoke-Git @("add", "-A", "--", $path) | Out-Null
        }
    }

    $stagedFiles = @(Invoke-Git @("diff", "--cached", "--name-only", "--diff-filter=ACMR"))
    $allStaged = @(Invoke-Git @("diff", "--cached", "--name-only"))
    if ($allStaged.Count -gt 0) {
        $forbidden = @($allStaged | Where-Object {
            ($_ -ne ".env.example") -and (
                $_ -match '(^|/)(\.env($|\.)|data|logs?|audio|models|checkpoints)(/|$)' -or
                $_ -match '(?i)\.(sqlite3?|wav|m4a|mp3|opus|webm|mp4|mov|safetensors|ckpt|pt|pth|pem|key)$' -or
                $_ -match '(?i)web/assets/.*photo'
            )
        })
        if ($forbidden.Count -gt 0) {
            throw "Forbidden private/runtime files were staged: $($forbidden -join ', ')"
        }
        Test-StagedSecrets $stagedFiles

        $diffCheck = & git -C $RepoRoot diff --cached --check 2>&1
        if ($LASTEXITCODE -ne 0) { throw "git diff --check failed: $($diffCheck -join ' ')" }

        $pythonCandidates = @(
            (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
            "D:\OneDrive\LLMs\talk-to-fengge\.venv\Scripts\python.exe"
        )
        $python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $python) { throw "No tested Python environment is available." }
        $tests = @(
            "tests.test_local_stt", "tests.test_persona", "tests.test_public_quota",
            "tests.test_rag_store", "tests.test_runtime_env", "tests.test_tts_text"
        )
        & $python -m unittest @tests
        if ($LASTEXITCODE -ne 0) { throw "Tests failed; nothing was committed or pushed." }

        $message = "chore: sync local KUN Chat " + (Get-Date -Format "yyyy-MM-dd HH:mm")
        Invoke-Git @("commit", "-m", $message) | Out-Null
        Write-SyncLog "Committed $($allStaged.Count) changed file(s)."
    }

    Invoke-Git @("fetch", "origin", "main") | Out-Null
    $state = Get-AheadBehind
    if ($state.Behind -gt 0 -and $state.Ahead -gt 0) {
        $rebaseOutput = & git -C $RepoRoot rebase origin/main 2>&1
        if ($LASTEXITCODE -ne 0) {
            & git -C $RepoRoot rebase --abort 2>$null | Out-Null
            throw "Remote changed during sync; automatic rebase was aborted. $($rebaseOutput -join ' ')"
        }
        $state = Get-AheadBehind
    }
    if ($state.Ahead -gt 0 -and $state.Behind -eq 0) {
        Invoke-Git @("push", "origin", "main") | Out-Null
        Write-SyncLog "Pushed $($state.Ahead) commit(s) to origin/main."
    } elseif ($state.Ahead -eq 0 -and $state.Behind -eq 0) {
        Write-SyncLog "Already synchronized."
    } else {
        throw "Repository could not be synchronized automatically (ahead=$($state.Ahead), behind=$($state.Behind))."
    }
} catch {
    Write-SyncLog "ERROR: $($_.Exception.Message)"
    exit 1
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
