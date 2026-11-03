$ErrorActionPreference = "Stop"

$project = Split-Path -Parent $PSScriptRoot
$version = "0.1.0"
$dist = Join-Path $project "dist"
$runtime = Join-Path $project "runtime\windows-x64\documentation-mesh.exe"
$zip = Join-Path $dist "documentation-mesh-plugin-$version.zip"

if (-not (Test-Path -LiteralPath $runtime)) {
    throw "Build the self-contained runtime before packaging."
}

New-Item -ItemType Directory -Path $dist -Force | Out-Null
Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue

$exclude = @("node_modules", "build", "dist", ".git", "__pycache__")
$staging = Join-Path ([System.IO.Path]::GetTempPath()) "documentation-mesh-plugin-$([guid]::NewGuid().ToString('N'))"
try {
    New-Item -ItemType Directory -Path $staging | Out-Null
    Get-ChildItem -LiteralPath $project -Force | Where-Object { $_.Name -notin $exclude } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $staging -Recurse -Force
    }
    Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zip -CompressionLevel Optimal
} finally {
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}

$hash = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
"$hash  $(Split-Path -Leaf $zip)" | Set-Content -LiteralPath "$zip.sha256" -Encoding ascii
Get-Item $zip, "$zip.sha256" | Select-Object FullName, Length
