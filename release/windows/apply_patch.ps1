param(
    [Parameter(Position = 0)]
    [string]$SourcePath
)

$ErrorActionPreference = 'Stop'
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PatchFile = Join-Path $BaseDir 'Wizardry7_PSX_KOR.xdelta'
$ToolsDir = Join-Path $BaseDir 'tools'

$ExpectedSourceMd5 = '188d3ee5a2a2242a719f290ea595e5ec'
$ExpectedPatchedMd5 = '1654910b3c631c74780cc5b15c0f01fb'
$OutputBaseName = 'Wizardry7_PSX_KOR'

function Resolve-Tool([string]$Name) {
    $local = Join-Path $ToolsDir ($Name + '.exe')
    if (Test-Path -LiteralPath $local) {
        return $local
    }
    $cmd = Get-Command ($Name + '.exe') -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "필요한 도구를 찾을 수 없습니다: $Name.exe"
}

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    Write-Host ('> ' + $Exe + ' ' + ($Arguments -join ' ')) -ForegroundColor DarkGray
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "명령 실행 실패 (exit $LASTEXITCODE): $Exe"
    }
}

function Get-Md5([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm MD5).Hash.ToLowerInvariant()
}

function Assert-SourceBin([string]$Path) {
    $md5 = Get-Md5 $Path
    Write-Host "원본 BIN MD5: $md5"
    if ($md5 -ne $ExpectedSourceMd5) {
        throw "지원하지 않는 원본입니다. 필요한 BIN MD5는 $ExpectedSourceMd5 입니다."
    }
}

function Assert-PatchedBin([string]$Path) {
    $md5 = Get-Md5 $Path
    Write-Host "한국어 BIN MD5: $md5"
    if ($md5 -ne $ExpectedPatchedMd5) {
        throw "패치 결과 검증에 실패했습니다. 예상 MD5: $ExpectedPatchedMd5"
    }
}

function Write-KoreanCue([string]$Path, [string]$BinFileName) {
    $lines = @(
        ('FILE "' + $BinFileName + '" BINARY'),
        '  TRACK 01 MODE2/2352',
        '    INDEX 01 00:00:00'
    )
    [System.IO.File]::WriteAllLines($Path, $lines, [System.Text.Encoding]::ASCII)
}

if (-not $SourcePath) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'Wizardry VII 일본 PS1판 CHD 또는 BIN 선택'
    $dialog.Filter = 'PS1 이미지 (*.chd;*.bin)|*.chd;*.bin|CHD (*.chd)|*.chd|BIN (*.bin)|*.bin'
    $dialog.Multiselect = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-Host '취소했습니다.'
        exit 0
    }
    $SourcePath = $dialog.FileName
}

$SourcePath = [System.IO.Path]::GetFullPath($SourcePath)
if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
    throw "입력 파일이 없습니다: $SourcePath"
}
if (-not (Test-Path -LiteralPath $PatchFile -PathType Leaf)) {
    throw "패치 파일이 없습니다: $PatchFile"
}

$ext = [System.IO.Path]::GetExtension($SourcePath).ToLowerInvariant()
if ($ext -ne '.chd' -and $ext -ne '.bin') {
    throw 'CHD 또는 BIN 파일만 지원합니다.'
}

$xdelta = Resolve-Tool 'xdelta3'
$sourceDir = Split-Path -Parent $SourcePath
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ('wiz7_psx_kor_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    if ($ext -eq '.bin') {
        Write-Host 'BIN 입력을 감지했습니다.' -ForegroundColor Cyan
        Assert-SourceBin $SourcePath

        $outputBin = Join-Path $sourceDir ($OutputBaseName + '.bin')
        $outputCue = Join-Path $sourceDir ($OutputBaseName + '.cue')
        if (Test-Path -LiteralPath $outputBin) { Remove-Item -LiteralPath $outputBin -Force }
        if (Test-Path -LiteralPath $outputCue) { Remove-Item -LiteralPath $outputCue -Force }

        Invoke-Checked $xdelta @('-d', '-f', '-s', $SourcePath, $PatchFile, $outputBin)
        Assert-PatchedBin $outputBin
        Write-KoreanCue $outputCue ([System.IO.Path]::GetFileName($outputBin))

        Write-Host ''
        Write-Host '완료!' -ForegroundColor Green
        Write-Host "BIN: $outputBin"
        Write-Host "CUE: $outputCue"
        Write-Host 'DuckStation에서는 CUE 파일을 실행하세요.'
    }
    else {
        Write-Host 'CHD 입력을 감지했습니다.' -ForegroundColor Cyan
        $chdman = Resolve-Tool 'chdman'

        $tempCue = Join-Path $tempDir 'source.cue'
        $tempBin = Join-Path $tempDir 'source.bin'
        $patchedBin = Join-Path $tempDir ($OutputBaseName + '.bin')
        $patchedCue = Join-Path $tempDir ($OutputBaseName + '.cue')
        $outputChd = Join-Path $sourceDir ($OutputBaseName + '.chd')
        if (Test-Path -LiteralPath $outputChd) { Remove-Item -LiteralPath $outputChd -Force }

        Write-Host 'CHD에서 원본 BIN을 임시 추출합니다...'
        Invoke-Checked $chdman @('extractcd', '-i', $SourcePath, '-o', $tempCue, '-ob', $tempBin, '-f')
        Assert-SourceBin $tempBin

        Write-Host '한국어 xdelta 패치를 적용합니다...'
        Invoke-Checked $xdelta @('-d', '-f', '-s', $tempBin, $PatchFile, $patchedBin)
        Assert-PatchedBin $patchedBin
        Write-KoreanCue $patchedCue ([System.IO.Path]::GetFileName($patchedBin))

        Write-Host '한국어 CHD를 생성합니다...'
        Invoke-Checked $chdman @('createcd', '-i', $patchedCue, '-o', $outputChd, '-f')
        Invoke-Checked $chdman @('verify', '-i', $outputChd)

        Write-Host ''
        Write-Host '완료!' -ForegroundColor Green
        Write-Host "CHD: $outputChd"
        Write-Host 'DuckStation에서는 이 CHD 파일을 바로 실행하면 됩니다.'
    }
}
catch {
    Write-Host ''
    Write-Host ('오류: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
finally {
    if (Test-Path -LiteralPath $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
