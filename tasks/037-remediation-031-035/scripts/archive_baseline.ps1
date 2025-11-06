$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archivePath = "tasks\037-remediation-031-035\artifacts\baseline_archive_$timestamp"

# Create archive directory
New-Item -ItemType Directory -Force -Path $archivePath | Out-Null

# Archive PyMuPDF-dependent files
$pymupdfFiles = @(
    "libs\extraction\backend_pymupdf.py",
    "libs\ingestion\pdf_ingestor.py",
    "agents\extraction\pdf_extractor.py",
    "libs\extraction\backend_docling.py",
    "libs\chunking\structure_aware_chunker.py",
    "agents\retrieval\hybrid_retriever.py",
    "scripts\edgar_validate.py",
    "scripts\chunk_cli.py",
    "scripts\hybrid_cli.py",
    "tests\test_backend_pymupdf.py",
    "tests\test_pdf_ingestor.py",
    "tests\test_pdf_extractor.py"
)

foreach ($file in $pymupdfFiles) {
    if (Test-Path $file) {
        $destPath = Join-Path $archivePath $file
        $destDir = Split-Path $destPath -Parent
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item $file $destPath -Force
        Write-Output "Archived: $file"
    } else {
        Write-Output "Not found: $file"
    }
}

# Create archive manifest
$manifest = @{
    timestamp = $timestamp
    archived_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    purpose = "Baseline archive before PyMuPDF to Docling migration"
    task = "037-remediation-031-035"
    files_archived = @()
}

foreach ($file in $pymupdfFiles) {
    if (Test-Path $file) {
        $fileInfo = Get-Item $file
        $manifest.files_archived += @{
            path = $file
            size = $fileInfo.Length
            last_modified = $fileInfo.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        }
    }
}

$manifest | ConvertTo-Json -Depth 3 | Out-File "$archivePath\MANIFEST.json" -Encoding UTF8
Write-Output "`nArchive created at: $archivePath"
Write-Output "Manifest saved to: $archivePath\MANIFEST.json"
Write-Output "Total files archived: $($manifest.files_archived.Count)"