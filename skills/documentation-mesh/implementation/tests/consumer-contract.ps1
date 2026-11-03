$ErrorActionPreference = "Stop"

$project = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $project "runtime\windows-x64\documentation-mesh.exe"
$source = Join-Path $project "tests\fixtures\corpus"
$workspace = Join-Path $project "build\consumer-contract"
$config = Join-Path $workspace "config.json"
$output = Join-Path $workspace "output"

if (-not (Test-Path -LiteralPath $runtime)) {
    throw "Packaged runtime not found: $runtime"
}

Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue

$version = (& $runtime --version | Out-String).Trim()
if ($version -ne "documentation-mesh 0.1.0") {
    throw "Unexpected runtime version: $version"
}

& $runtime init --source $source --workspace $workspace --force | Out-Null
$first = (& $runtime build --config $config --validate | Out-String) | ConvertFrom-Json
if ($first.statistics.documentCount -ne 3 -or $first.statistics.cacheReparsed -ne 3 -or $first.statistics.cacheReused -ne 0) {
    throw "Initial packaged build did not parse the expected fixture corpus."
}

$index = Join-Path $output "documentation-index.json"
$validation = (& $runtime validate --index $index | Out-String) | ConvertFrom-Json
if (-not $validation.valid) {
    throw "Packaged validation did not report success."
}

$second = (& $runtime build --config $config --validate | Out-String) | ConvertFrom-Json
if ($second.statistics.documentCount -ne 3 -or $second.statistics.cacheReused -ne 3 -or $second.statistics.cacheReparsed -ne 0) {
    throw "Packaged cache refresh did not reuse all unchanged fixture documents."
}

$required = @(
    $index,
    (Join-Path $output "documentation-mesh.html"),
    (Join-Path $output "DOCUMENTATION-MESH.md"),
    (Join-Path $output "build-cache.json")
)
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required output is missing: $path"
    }
}

$html = Get-Content -LiteralPath (Join-Path $output "documentation-mesh.html") -Raw
if ($html -notmatch "window\.DOCUMENTATION_MESH_INDEX=" -or $html -notmatch "ForceGraph") {
    throw "Offline dashboard assets were not embedded in the packaged output."
}

[ordered]@{
    version = $version
    firstBuild = $first.statistics
    validation = $validation.valid
    refreshBuild = $second.statistics
    outputs = $required
} | ConvertTo-Json -Depth 5
