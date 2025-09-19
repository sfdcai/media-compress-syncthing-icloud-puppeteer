# Script: Setup-GitAndClone.ps1

# Function to check if Git is installed
function Check-Git {
    try {
        git --version > $null 2>&1
        return $true
    } catch {
        return $false
    }
}

# Function to install Git via winget
function Install-Git {
    Write-Host "Installing Git..."
    winget install --id Git.Git -e --source winget
}

# Function to update Git via winget
function Update-Git {
    Write-Host "Updating Git..."
    winget upgrade --id Git.Git -e --source winget
}

# Check if Git is installed
if (-not (Check-Git)) {
    Install-Git
} else {
    Write-Host "Git is already installed. Updating to the latest version..."
    Update-Git
}

# Define repository URL and folder
$repoURL = "https://github.com/sfdcai/media-compress-syncthing-icloud-puppeteer"
$folderName = "media-compress-syncthing-icloud-puppeteer"

# Clone the repository if it doesn't exist
if (-not (Test-Path $folderName)) {
    Write-Host "Cloning repository..."
    git clone $repoURL
} else {
    Write-Host "Repository already exists. Pulling latest changes..."
    Set-Location $folderName
    git pull
    Set-Location ..
}

# Change directory to the cloned repository
Set-Location $folderName
Write-Host "Changed directory to: $(Get-Location)"
