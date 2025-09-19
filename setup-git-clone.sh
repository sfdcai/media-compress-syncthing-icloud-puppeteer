#!/bin/bash

# Exit immediately if a command fails
set -e

# Function to check if git is installed
check_git() {
    if command -v git >/dev/null 2>&1; then
        echo "Git is installed. Updating..."
        sudo apt update
        sudo apt install --only-upgrade -y git
    else
        echo "Git is not installed. Installing..."
        sudo apt update
        sudo apt install -y git
    fi
}

# Function to clone repo
clone_repo() {
    REPO_URL="https://github.com/sfdcai/media-compress-syncthing-icloud-puppeteer"
    FOLDER_NAME="media-compress-syncthing-icloud-puppeteer"

    if [ -d "$FOLDER_NAME" ]; then
        echo "Repository already exists. Pulling latest changes..."
        cd "$FOLDER_NAME"
        git pull
    else
        echo "Cloning repository..."
        git clone "$REPO_URL"
        cd "$FOLDER_NAME"
    fi
}

# Run functions
check_git
clone_repo

# Show current directory
echo "Current directory: $(pwd)"
