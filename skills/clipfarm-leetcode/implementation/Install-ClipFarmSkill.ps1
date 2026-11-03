param([switch]$Force)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'skills\clipfarm-leetcode\SKILL.md'
$directory = Join-Path $HOME '.copilot\skills\clipfarm-leetcode'
$destination = Join-Path $directory 'SKILL.md'
$content = [System.IO.File]::ReadAllText($source).Replace('__CLIPFARM_ROOT__', $PSScriptRoot)
if ((Test-Path -LiteralPath $destination) -and -not $Force) {
    if ([System.IO.File]::ReadAllText($destination) -ne $content) {
        throw "A different personal skill exists at $destination. Inspect it, then use -Force only if it should be replaced."
    }
} else {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    [System.IO.File]::WriteAllText($destination, $content, [System.Text.UTF8Encoding]::new($false))
}
Write-Output "Installed: $destination"
Write-Output 'In an existing Copilot CLI session, run /skills reload.'
Write-Output 'Then: Use the /clipfarm-leetcode skill for VIDEO_PATH. The transcript is generated automatically.'
