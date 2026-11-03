param(
    [int]$Port = 8741,
    [switch]$Transcription,
    [switch]$Workflow,
    [switch]$SetupOnly,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required. Install Python, then run this script again.' }
    & $python -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $python -c "import clipfarm, fastapi, uvicorn, cv2, imageio_ffmpeg"
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if ($Transcription) {
    & $python -c "import faster_whisper" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install -e '.[transcribe]'
        if ($LASTEXITCODE -ne 0) { throw 'Optional transcription installation failed.' }
    }
}
if ($Workflow) {
    & $python -c "import importlib.metadata as m; assert not any(d.metadata['Name'] == 'opencv-python-headless' for d in m.distributions()), 'Stop ClipFarm, uninstall opencv-python-headless, then reinstall the declared dependencies; do not mix cv2 providers.'"
    if ($LASTEXITCODE -ne 0) { throw 'Incompatible legacy OpenCV installation. Follow the error above before continuing.' }
    & $python -c "import rapidocr, onnxruntime, faster_whisper" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install -e '.[workflow]'
        if ($LASTEXITCODE -ne 0) { throw 'Optional workflow dependency installation failed.' }
    }
}
if ($SetupOnly) { exit 0 }
$arguments = @('-m', 'clipfarm', '--port', "$Port")
if (-not $NoBrowser) { $arguments += '--open' }
& $python @arguments
exit $LASTEXITCODE
