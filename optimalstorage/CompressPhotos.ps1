# Photo Processing Script

# Define paths and constants
$SourcePath = "C:\path\to\your\photos"  # Folder with your photos
$DestPath = "\\192.168.1.4\photos"  # Destination on NAS
$ImageMagickPath = "C:\path\to\magick.exe"  # Path to ImageMagick
$DatabasePath = "C:\path\to\PhotoCompression.db"  # SQLite database path for photos
$PhotoResizePercentage = 50  # Resize percentage
$MaxRetries = 3  # Number of retries for file operations
$LogPath = "C:\path\to\photo_compression_log.txt"  # Log file for photo processing

# Ensure ImageMagick and directories exist
if (-not (Test-Path $ImageMagickPath)) { throw "ImageMagick not found at $ImageMagickPath." }
if (-not (Test-Path $SourcePath)) { throw "Source path $SourcePath does not exist." }
if (-not (Test-Path $DestPath)) { throw "Destination path $DestPath does not exist." }

# Initialize SQLite database for photos
function InitializePhotoDatabase {
    if (-not (Test-Path $DatabasePath)) {
        $db = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$DatabasePath;Version=3;")
        $db.Open()
        $sqlCmd = $db.CreateCommand()
        $sqlCmd.CommandText = @"
        CREATE TABLE IF NOT EXISTS PhotoCompression (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FileName TEXT,
            OriginalSize INTEGER,
            CompressedSize INTEGER,
            CompressionDate DATETIME
        );
"@
        $sqlCmd.ExecuteNonQuery()
        $db.Close()
    }
}

# Logging function to display progress and log errors
function LogMessage {
    param (
        [string]$message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp - $message"
    Add-Content -Path $LogPath -Value $logEntry
    Write-Host $message
}

# Function to log photo size in SQLite database
function LogPhotoSize {
    param (
        [string]$fileName,
        [int64]$originalSize,
        [int64]$compressedSize
    )
    try {
        $db = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$DatabasePath;Version=3;")
        $db.Open()
        $sqlCmd = $db.CreateCommand()
        $sqlCmd.CommandText = "INSERT INTO PhotoCompression (FileName, OriginalSize, CompressedSize, CompressionDate) VALUES ('$fileName', $originalSize, $compressedSize, datetime('now'))"
        $sqlCmd.ExecuteNonQuery()
        $db.Close()
        LogMessage "Logged photo $fileName to database."
    } catch {
        LogMessage "Failed to log $fileName to database: $_"
    }
}

# Retry logic
function Retry-Operation {
    param (
        [scriptblock]$Operation,
        [int]$MaxRetries
    )
    $retryCount = 0
    while ($retryCount -lt $MaxRetries) {
        try {
            Invoke-Command -ScriptBlock $Operation
            return
        } catch {
            $retryCount++
            LogMessage "Error encountered: $_. Retrying ($retryCount/$MaxRetries)..."
            Start-Sleep -Seconds 2
        }
    }
    throw "Operation failed after $MaxRetries retries."
}

# Function to resize photos
function ResizePhotos {
    param (
        [int]$MaxFilesToProcess
    )

    $photoFiles = Get-ChildItem -Path $SourcePath -Filter *.jpg,*.jpeg,*.png -Recurse | Select-Object -First $MaxFilesToProcess
    LogMessage "Found $($photoFiles.Count) photos to process."

    foreach ($photo in $photoFiles) {
        $originalSize = (Get-Item $photo.FullName).Length
        $outputPath = Join-Path $DestPath $photo.Name

        LogMessage "Resizing photo: $($photo.FullName)..."
        
        # Resize photo and preserve metadata
        $resizeCmd = "$ImageMagickPath `"$($photo.FullName)`" -resize $PhotoResizePercentage% -quality 85 `"$outputPath`""
        Retry-Operation -Operation { Invoke-Expression $resizeCmd } -MaxRetries $MaxRetries

        if (Test-Path $outputPath) {
            $compressedSize = (Get-Item $outputPath).Length
            LogPhotoSize -fileName $photo.Name -originalSize $originalSize -compressedSize $compressedSize
            LogMessage "Resized photo saved to: $outputPath"
        } else {
            LogMessage "Failed to resize photo: $($photo.FullName)"
        }
    }
}

# Initialize and run photo resizing
InitializePhotoDatabase
LogMessage "Starting photo resizing process..."
ResizePhotos -MaxFilesToProcess 10  # Process 10 files per run
LogMessage "Photo resizing process completed."
