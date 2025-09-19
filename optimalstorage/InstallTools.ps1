# PowerShell script to install FFmpeg, ImageMagick, SQLite, Bento4 (mp4edit) and set environment variables

# Define paths for installation
$FFmpegPath = "C:\tools\ffmpeg"           # Path where FFmpeg will be installed
$ImageMagickPath = "C:\tools\imagemagick"  # Path where ImageMagick will be installed
$SQLitePath = "C:\tools\sqlite"            # Path where SQLite will be installed
$Bento4Path = "C:\tools\bento4"            # Path where Bento4 (mp4edit) will be installed
$DownloadPath = "C:\tools\downloads"       # Temporary download folder

# Ensure the directories exist
New-Item -ItemType Directory -Path $FFmpegPath -Force
New-Item -ItemType Directory -Path $ImageMagickPath -Force
New-Item -ItemType Directory -Path $SQLitePath -Force
New-Item -ItemType Directory -Path $Bento4Path -Force
New-Item -ItemType Directory -Path $DownloadPath -Force

# Function to log output
function LogMessage {
    param (
        [string]$message
    )
    Write-Host "[INFO] $message"
}

# Function to download a file from a URL
function Download-File {
    param (
        [string]$url,
        [string]$outputPath
    )
    try {
        Invoke-WebRequest -Uri $url -OutFile $outputPath
        LogMessage "Downloaded $url to $outputPath"
    } catch {
        LogMessage "Error downloading $url: $_"
    }
}

# Function to extract zip files
function Extract-Zip {
    param (
        [string]$zipPath,
        [string]$destinationPath
    )
    try {
        Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
        [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $destinationPath)
        LogMessage "Extracted $zipPath to $destinationPath"
    } catch {
        LogMessage "Failed to extract $zipPath: $_"
    }
}

# Function to set system environment variables
function Set-SystemPath {
    param (
        [string]$newPath
    )
    $envPath = [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::Machine)
    if ($envPath -notlike "*$newPath*") {
        [System.Environment]::SetEnvironmentVariable('Path', "$envPath;$newPath", [System.EnvironmentVariableTarget]::Machine)
        LogMessage "Added $newPath to system PATH."
    } else {
        LogMessage "$newPath already exists in system PATH."
    }
}

# Install FFmpeg
function Install-FFmpeg {
    $ffmpegZipUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z"
    $ffmpegZip = Join-Path $DownloadPath "ffmpeg.7z"
    Download-File -url $ffmpegZipUrl -outputPath $ffmpegZip
    LogMessage "Installing FFmpeg..."
    # Extract and install FFmpeg (requires 7-Zip)
    Start-Process "7z.exe" -ArgumentList "x `"$ffmpegZip`" -o`"$FFmpegPath`"" -Wait
    Set-SystemPath -newPath "$FFmpegPath\bin"
    LogMessage "FFmpeg installed."
}

# Install ImageMagick
function Install-ImageMagick {
    $imageMagickUrl = "https://imagemagick.org/download/binaries/ImageMagick-7.1.0-64bit.zip"
    $imageMagickZip = Join-Path $DownloadPath "imagemagick.zip"
    Download-File -url $imageMagickUrl -outputPath $imageMagickZip
    Extract-Zip -zipPath $imageMagickZip -destinationPath $ImageMagickPath
    Set-SystemPath -newPath "$ImageMagickPath"
    LogMessage "ImageMagick installed."
}

# Install SQLite
function Install-SQLite {
    $sqliteUrl = "https://www.sqlite.org/2023/sqlite-tools-win32-x86-3420000.zip"
    $sqliteZip = Join-Path $DownloadPath "sqlite.zip"
    Download-File -url $sqliteUrl -outputPath $sqliteZip
    Extract-Zip -zipPath $sqliteZip -destinationPath $SQLitePath
    Set-SystemPath -newPath "$SQLitePath"
    LogMessage "SQLite installed."
}

# Install Bento4 (mp4edit)
function Install-Bento4 {
    $bento4Url = "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-639.x86_64-microsoft-win32.zip"
    $bento4Zip = Join-Path $DownloadPath "bento4.zip"
    Download-File -url $bento4Url -outputPath $bento4Zip
    Extract-Zip -zipPath $bento4Zip -destinationPath $Bento4Path
    Set-SystemPath -newPath "$Bento4Path"
    LogMessage "Bento4 (mp4edit) installed."
}

# Verify the installation
function Verify-Installation {
    try {
        ffmpeg -version
        magick -version
        sqlite3 --version
        mp4edit --version
        LogMessage "All tools successfully installed and available in the system PATH."
    } catch {
        LogMessage "Error verifying installation: $_"
    }
}

# Main script execution
Install-FFmpeg
Install-ImageMagick
Install-SQLite
Install-Bento4
Verify-Installation
