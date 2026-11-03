$ErrorActionPreference = "Stop"

$project = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $project "runtime\windows-x64"
$work = Join-Path $project "build\dotnet-publish\windows-x64"
$runtimeProject = Join-Path $project "src\DocumentationMesh.Runtime\DocumentationMesh.Runtime.csproj"
$executable = Join-Path $dist "documentation-mesh.exe"

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw "The .NET 8 SDK is required to build the Windows x64 runtime."
}

Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $executable -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $dist "version-manifest.json") -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $dist -Force | Out-Null

dotnet publish $runtimeProject `
    --configuration Release `
    --runtime win-x64 `
    --self-contained true `
    --output $work `
    --nologo `
    -p:PublishSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:EnableCompressionInSingleFile=true `
    -p:DebugType=None `
    -p:DebugSymbols=false

$published = Join-Path $work "documentation-mesh.exe"
if (-not (Test-Path -LiteralPath $published)) {
    throw "Runtime build did not produce $published"
}

Copy-Item -LiteralPath $published -Destination $executable -Force
& $executable --version
$hash = (Get-FileHash -Algorithm SHA256 $executable).Hash.ToLowerInvariant()
$manifest = [ordered]@{
    name = "documentation-mesh-runtime"
    version = "0.1.0"
    platform = "windows-x64"
    executable = "documentation-mesh.exe"
    sha256 = $hash
    builtAt = (Get-Date).ToUniversalTime().ToString("o")
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dist "version-manifest.json") -Encoding utf8NoBOM
Get-Item $executable, (Join-Path $dist "version-manifest.json") | Select-Object FullName, Length
