param(
    [string]$VideoSourceDir = "C:\Media\Videos\Working",
    [string]$PhotoSourceDir = "C:\Media\Photos\Working",
    [string]$RawPhotoDir = "\\192.168.1.4\media\photos\raw",
    [string]$VideoDbPath = "C:\Media\VideoCompression.db",
    [string]$PhotoDbPath = "C:\Media\PhotoCompression.db",
    [int]$CompressionIntervalYears = 2,
    [int]$InitialResizePercentage = 80,   # Initial photo compression
    [int]$SubsequentResizePercentage = 90, # Further compression for older photos
    [int]$InitialVideoResolution = 1080,  # Initial video resolution for first compression
    [int]$SubsequentVideoResolution = 720, # Subsequent video resolution for progressive compression
    [int]$VideoCompressionQuality = 23,  # H264 compression quality for videos
    [int]$MaxFilesToProcess = 10         # Max files to process per run
)

# Function to ensure the SQLite DB for videos exists
function Initialize-VideoDatabase {
    if (-not (Test-Path $VideoDbPath)) {
        sqlite3 $VideoDbPath "CREATE TABLE IF NOT EXISTS Videos (FileName TEXT PRIMARY KEY, OriginalSize INT, CompressedSize INT, LastCompressedDate TEXT, TimesCompressed INT);"
    }
}

# Function to ensure the SQLite DB for photos exists
function Initialize-PhotoDatabase {
    if (-not (Test-Path $PhotoDbPath)) {
        sqlite3 $PhotoDbPath "CREATE TABLE IF NOT EXISTS Photos (FileName TEXT PRIMARY KEY, OriginalSize INT, CompressedSize INT, LastCompressedDate TEXT, TimesCompressed INT);"
    }
}

# Function to get file metadata and calculate file age in years
function Get-FileAgeInYears {
    param([string]$file)
    $fileInfo = Get-Item $file
    $fileAge = ((Get-Date) - $fileInfo.LastWriteTime).Days / 365
    return [math]::Floor($fileAge)
}

# Function to compress video files using FFmpeg
function Compress-Videos {
    Initialize-VideoDatabase
    $videos = Get-ChildItem -Path $VideoSourceDir -Filter *.mp4 -ErrorAction Stop | Select-Object -First $MaxFilesToProcess

    foreach ($video in $videos) {
        $filePath = $video.FullName
        $fileName = $video.Name
        $fileAgeYears = Get-FileAgeInYears $filePath

        # Query the database to check if the file was previously compressed
        $query = "SELECT * FROM Videos WHERE FileName = '$fileName';"
        $result = sqlite3 $VideoDbPath $query

        if (-not $result) {
            # First-time compression: 4K to 1080p
            $outputPath = Join-Path $VideoSourceDir ("Compressed_" + $fileName)
            ffmpeg -i "$filePath" -vf scale=1920:$InitialVideoResolution -c:v libx264 -crf $VideoCompressionQuality "$outputPath" -y

            # Get file sizes for logging
            $originalSize = (Get-Item $filePath).Length
            $compressedSize = (Get-Item $outputPath).Length

            # Insert compressed video metadata into the database
            $insert = "INSERT INTO Videos (FileName, OriginalSize, CompressedSize, LastCompressedDate, TimesCompressed) VALUES ('$fileName', $originalSize, $compressedSize, '$(Get-Date)', 1);"
            sqlite3 $VideoDbPath $insert

            Write-Host "First-time compression for video $fileName completed."
        }
        else {
            # The file was compressed before, check the age for further compression
            if ($fileAgeYears -ge $CompressionIntervalYears) {
                # Further compress the file to a lower resolution (e.g., 720p)
                $outputPath = Join-Path $VideoSourceDir ("Progressive_Compressed_" + $fileName)
                ffmpeg -i "$filePath" -vf scale=1280:$SubsequentVideoResolution -c:v libx264 -crf $VideoCompressionQuality "$outputPath" -y

                # Get updated size
                $compressedSize = (Get-Item $outputPath).Length

                # Update the database
                $update = "UPDATE Videos SET CompressedSize = $compressedSize, LastCompressedDate = '$(Get-Date)', TimesCompressed = TimesCompressed + 1 WHERE FileName = '$fileName';"
                sqlite3 $VideoDbPath $update

                Write-Host "Further compressed video $fileName to $SubsequentVideoResolution p."
            } else {
                Write-Host "Video $fileName does not need further compression yet."
            }
        }
    }
}

# Function to compress image files using progressive compression
function Compress-Photos {
    Initialize-PhotoDatabase
    $photos = Get-ChildItem -Path $PhotoSourceDir -Filter *.jpg -ErrorAction Stop | Select-Object -First $MaxFilesToProcess

    foreach ($photo in $photos) {
        $filePath = $photo.FullName
        $fileName = $photo.Name

        # Check file age
        $fileAgeYears = Get-FileAgeInYears $filePath

        # Query the database to check if the file was previously compressed
        $query = "SELECT * FROM Photos WHERE FileName = '$fileName';"
        $result = sqlite3 $PhotoDbPath $query

        if (-not $result) {
            # First-time compression: Copy original to raw folder and compress the working copy
            $rawFilePath = Join-Path $RawPhotoDir $fileName
            Copy-Item $filePath $rawFilePath

            # Compress the image using ImageMagick
            magick convert "$filePath" -resize "$InitialResizePercentage%" "$filePath"

            # Get sizes for logging
            $originalSize = (Get-Item $rawFilePath).Length
            $compressedSize = (Get-Item $filePath).Length

            # Insert into the database
            $insert = "INSERT INTO Photos (FileName, OriginalSize, CompressedSize, LastCompressedDate, TimesCompressed) VALUES ('$fileName', $originalSize, $compressedSize, '$(Get-Date)', 1);"
            sqlite3 $PhotoDbPath $insert

            Write-Host "First-time compression for photo $fileName completed."
        }
        else {
            # The file was compressed before, check the age for further compression
            if ($fileAgeYears -ge $CompressionIntervalYears) {
                # Further compress the file
                magick convert "$filePath" -resize "$SubsequentResizePercentage%" "$filePath"

                # Get updated size
                $compressedSize = (Get-Item $filePath).Length

                # Update the database
                $update = "UPDATE Photos SET CompressedSize = $compressedSize, LastCompressedDate = '$(Get-Date)', TimesCompressed = TimesCompressed + 1 WHERE FileName = '$fileName';"
                sqlite3 $PhotoDbPath $update

                Write-Host "Further compressed photo $fileName by $SubsequentResizePercentage%."
            } else {
                Write-Host "Photo $fileName does not need further compression yet."
            }
        }
    }
}

# Main execution: Run video and photo compression
Compress-Videos
Compress-Photos

Write-Host "Media compression completed."
