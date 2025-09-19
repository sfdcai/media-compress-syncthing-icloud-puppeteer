# Video Processing Script

# Define paths and constants
$SourcePath = "C:\path\to\your\videos"  # Folder with your videos
$DestPath = "\\192.168.1.4\videos"  # Destination on NAS
$FFmpegPath = "C:\path\to\ffmpeg.exe"  # Path to FFmpeg
$DatabasePath = "C:\path\to\VideoCompression.db"  # SQLite database path for videos
$CompressionQuality = 23  # FFmpeg compression quality
$MaxRetries = 3  # Number of retries for file operations
$LogPath = "C:\path\to\video_compression_log.txt"  # Log file for video processing

# Ensure FFmpeg and directories exist
if (-not (Test-Path $FFmpegPath)) { throw "FFmpeg not found at $FFmpegPath." }
if (-not (Test-Path $SourcePath)) { throw "Source path $SourcePath does not exist." }
if (-not (Test-Path $DestPath)) { throw "Destination path $DestPath does not exist." }

# Initialize SQLite database for videos
function InitializeVideoDatabase {
    if (-not (Test-Path $DatabasePath)) {
        $db = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$DatabasePath;Version=3;")
        $db.Open()
        $sqlCmd = $db.CreateCommand()
        $sqlCmd.CommandText = @"
        CREATE TABLE IF NOT EXISTS VideoCompression (
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

# Function to log video size in SQLite database
function LogVideoSize {
    param (
        [string]$fileName,
        [int64]$originalSize,
        [int64]$compressedSize
    )
    try {
        $db = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$DatabasePath;Version=3;")
        $db.Open()
        $sqlCmd = $db.CreateCommand()
        $sqlCmd.CommandText = "INSERT INTO VideoCompression (FileName, OriginalSize, CompressedSize, CompressionDate) VALUES ('$fileName', $originalSize, $compressedSize, datetime('now'))"
        $sqlCmd.ExecuteNonQuery()
        $db.Close()
        LogMessage "Logged video $fileName to database."
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

# Function to compress videos
function CompressVideos {
    param (
        [int]$MaxFilesToProcess
    )

    $videoFiles = Get-ChildItem -Path $SourcePath -Filter *.mp4 -Recurse | Select-Object -First $MaxFilesToProcess
    LogMessage "Found $($videoFiles.Count) videos to process."

    foreach ($video in $videoFiles) {
        $originalSize = (Get-Item $video.FullName).Length
        $outputPath = Join-Path $DestPath $video.Name

        LogMessage "Compressing video: $($video.FullName)..."
        
        # Compress video to 1080p using FFmpeg
        $ffmpegCmd = "$FFmpegPath -i `"$($video.FullName)`" -vf scale=1920:-1 -c:v libx264 -crf $CompressionQuality `"$outputPath`""
        Retry-Operation -Operation { Invoke-Expression $ffmpegCmd } -MaxRetries $MaxRetries

        if (Test-Path $outputPath) {
            $compressedSize = (Get-Item $outputPath).Length
            LogVideoSize -fileName $video.Name -originalSize $originalSize -compressedSize $compressedSize
            LogMessage "Compressed video saved to: $outputPath"
        } else {
            LogMessage "Failed to compress video: $($video.FullName)"
        }
    }
}

# Initialize and run video compression
InitializeVideoDatabase
LogMessage "Starting video compression process..."
CompressVideos -MaxFilesToProcess 10  # Process 10 files per run
LogMessage "Video compression process completed."
