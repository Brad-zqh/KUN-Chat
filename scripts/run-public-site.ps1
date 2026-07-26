param(
    [ValidateSet("build", "dev", "test", "lint")]
    [string]$Command = "build"
)

$ErrorActionPreference = "Stop"
$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\public-site")).Path
$dependencyRoot = "D:\LocalDevDeps\OneDriveMirror\LLMs\KUN-Chat\public-site"
$workspaceRoot = Join-Path $dependencyRoot "workspace"
$nodeModules = Join-Path $dependencyRoot "node_modules"
$npm = "C:\Program Files\nodejs\npm.cmd"

if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
    throw "External node_modules is missing: $nodeModules"
}
if (-not (Test-Path -LiteralPath $npm -PathType Leaf)) {
    throw "npm.cmd was not found: $npm"
}
if (-not $workspaceRoot.StartsWith("D:\LocalDevDeps\OneDriveMirror\LLMs\KUN-Chat\public-site\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to synchronize an unexpected workspace path: $workspaceRoot"
}

New-Item -ItemType Directory -Force -Path $workspaceRoot | Out-Null
$excludeDirectories = @(
    ".git", ".vinext", ".wrangler", "dist", "node_modules"
)
$robocopyArgs = @(
    $sourceRoot, $workspaceRoot, "/MIR", "/R:2", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/XD"
) + $excludeDirectories
& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "Source synchronization failed with robocopy exit code $LASTEXITCODE"
}

Push-Location $workspaceRoot
try {
    & $npm run $Command
    if ($LASTEXITCODE -ne 0) {
        throw "npm run $Command failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
