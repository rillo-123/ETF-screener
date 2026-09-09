<#
Inspect or remove obsolete regenerable caches from this repository's old data
directories. Price copies are removed only after matching the migration hashes
on both disks. Without -Apply this command only reports candidate sizes.
#>
param([switch]$Apply, [switch]$RemoveVerifiedPriceCopies, [switch]$OnlyPriceCopies)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dataRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'data'))
$removed = 0
$bytes = [long]0
$candidates = 0

function Assert-LocalDataPath([string]$Path) {
    $resolved = [IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($dataRoot + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside repository data: $resolved"
    }
    if ((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing linked path: $resolved"
    }
    return $resolved
}

$directories = @('parquet', 'cache', 'cache/screen_requests',
    'cache/screen-indicators', 'cache/strategy_eval', 'cache/backtests', 'cache/indicators')
if ($OnlyPriceCopies) { $directories = @() }
foreach ($relative in $directories) {
    $directory = Join-Path $dataRoot $relative
    if (-not (Test-Path -LiteralPath $directory)) { continue }
    $directory = Assert-LocalDataPath $directory
    foreach ($file in [IO.DirectoryInfo]::new($directory).EnumerateFiles()) {
        $name = $file.Name
        if ($relative -in @('parquet', 'cache')) {
            if ($name -notmatch '_dsl_[0-9a-f]{8}_.*\.(parquet|pkl)$') { continue }
        } elseif ($name -notmatch '\.(parquet|pkl)$' -or $name.EndsWith('_data.parquet')) {
            continue
        }
        # EnumerateFiles returns direct children of the verified absolute root.
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        $candidates++
        $bytes += $file.Length
        if ($Apply) {
            $file.Delete()
            $removed++
            if ($removed % 10000 -eq 0) { Write-Output "Removed $removed derived files" }
        }
    }
}

if ($RemoveVerifiedPriceCopies) {
    $manifest = Get-Content -LiteralPath (Join-Path $dataRoot 'storage_migration.json') -Raw | ConvertFrom-Json
    $source = Assert-LocalDataPath $manifest.source
    $destination = [IO.Path]::GetFullPath($manifest.destination)
    if (-not (Test-Path -LiteralPath (Join-Path (Split-Path $destination) '.etf-screener-storage'))) {
        throw 'Destination storage marker is missing'
    }
    foreach ($record in $manifest.verified) {
        if ([IO.Path]::GetFileName($record.name) -ne $record.name) { throw 'Invalid manifest name' }
        $original = Join-Path $source $record.name
        if (-not (Test-Path -LiteralPath $original)) { continue }
        $original = Assert-LocalDataPath $original
        $copy = Join-Path $destination $record.name
        if ((Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash -ne $record.sha256 -or
            (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne $record.sha256) {
            throw "Price copy changed since migration: $($record.name)"
        }
        $candidates++
        $bytes += (Get-Item -LiteralPath $original).Length
        if ($Apply) { Remove-Item -LiteralPath $original; $removed++ }
    }
}
@{ candidates = $candidates; removed = $removed; bytes = $bytes; applied = [bool]$Apply } | ConvertTo-Json
