# install-lz.ps1
# LZ Knowledge System — Windows installer
# Run from INSIDE the lz-knowledge directory:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   (first time only)
#   .\install-lz.ps1

$SkillDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Install-To {
    param(
        [string]$Name,
        [string]$SkillsDir,
        [string]$MdFile
    )

    # Create skills directory and copy skill
    New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
    $dest = Join-Path $SkillsDir "lz-knowledge"
    if (Test-Path $dest) {
        Remove-Item -Recurse -Force $dest
    }
    Copy-Item -Recurse -Force $SkillDir $dest

    # Create md file if it doesn't exist
    $mdDir = Split-Path -Parent $MdFile
    New-Item -ItemType Directory -Force -Path $mdDir | Out-Null
    if (-not (Test-Path $MdFile)) {
        New-Item -ItemType File -Path $MdFile | Out-Null
    }

    # Check if already installed
    $content = Get-Content $MdFile -Raw -ErrorAction SilentlyContinue
    if ($content -match "LZ Knowledge System") {
        Write-Host "  ⚠️  Already installed in $MdFile — skipping"
    } else {
        $blurb = @"


---
## LZ Knowledge System
Skill: $dest\SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
"@
        Add-Content -Path $MdFile -Value $blurb
        Write-Host "  ✅ $Name → $MdFile"
    }
}

Write-Host ""
Write-Host "🔧 Installing LZ Knowledge System..."
Write-Host ""

Install-To "Claude Code" "$env:USERPROFILE\.claude\skills"  "$env:USERPROFILE\.claude\CLAUDE.md"
Install-To "Codex CLI"   "$env:USERPROFILE\.codex\skills"   "$env:USERPROFILE\.codex\AGENTS.md"
Install-To "Gemini CLI"  "$env:USERPROFILE\.gemini\skills"  "$env:USERPROFILE\.gemini\GEMINI.md"

Write-Host ""
Write-Host "🎉 Done! Start any session and type /lz-readproject to begin."
Write-Host ""