# command to run this
# powershell -ExecutionPolicy Bypass -File compressold.ps1 -numFilesToProcess 3
# This script is used to compress old media files to save space. It compresses 4k videos to 1080p, 720p, 480p based on the age of the media.
# It also corrects the metadata and GPS data for the media files.
# The script uses ffmpeg and exiftool to compress and correct the metadata of the media files.
# The script also logs the compression data to a CSV file for future reference.
# The script also backs up the 4k media files to a remote location before compressing them.
# The script uses the following tools:
# 1. ffmpeg - https://ffmpeg.org/
# 2. exiftool - https://exiftool.org/
# 3. mp4extract -
# 4. mp4edit -

param (
    [int]$numFilesToProcess = 3
)

Clear-Host
Write-Host ------------Setting up the environment-------------------------------------------------------------------
$icloud = "C:\Users\Amit\Desktop\Github\optimalstorage\test\"
#$icloud = "C:\Users\Amit\Pictures\iCloud Photos\Photos"
$filelist = Get-ChildItem $icloud -Include *.MOV,*.mp4 -Recurse | Select-Object -First $numFilesToProcess
$remoteFilePath = 'C:\Users\Amit\Desktop\Github\optimalstorage\backup\'
#$remoteFilePath = '\\192.168.68.81\Amit\RawVideos' 
#net use $remoteFilePath /user:admin Apple@123#
$num = $filelist | measure
$filecount = $num.count
Write-Host ------------Environment setup Complete------------------------------------------------------------------- 

# Path to the CSV file
$csvPath = "C:\Users\Amit\Desktop\Github\optimalstorage\file_storage.csv"

# Function to create the CSV file if it doesn't exist
function Create-CSVFile {
    param (
        [string]$csvPath
    )

    if (-not (Test-Path -Path $csvPath)) {
        Write-Host "CSV file does not exist. Creating CSV file..."
        "FileName,FilePath,DateProcessed,OldSize,NewSize,Resolution" | Out-File -FilePath $csvPath
        Write-Host "CSV file created successfully."
    } else {
        Write-Host "CSV file already exists. Skipping creation."
    }
}

# Function to insert data into the CSV file
function Insert-CompressionData {
    param (
        [string]$csvPath,
        [string]$fileName,
        [string]$filePath,
        [string]$oldSize,
        [string]$newSize,
        [string]$resolution,
        [datetime]$dateProcessed
    )

    try {
        $data = "$fileName,$filePath,$dateProcessed,$oldSize,$newSize,$resolution"
        Add-Content -Path $csvPath -Value $data
        Write-Output "Data inserted successfully."
    }
    catch {
        Write-Error "An error occurred: $_"
    }
}

# Function to add content to a file with retry mechanism
function Add-ContentWithRetry {
    param (
        [string]$path,
        [string]$value,
        [int]$maxRetries = 5,
        [int]$delaySeconds = 2
    )

    $retryCount = 0
    while ($retryCount -lt $maxRetries) {
        try {
            Add-Content -Path $path -Value $value
            Write-Output "Content added successfully."
            return
        }
        catch {
            Write-Host "Failed to write to $path. Retrying in $delaySeconds seconds..."
            Start-Sleep -Seconds $delaySeconds
            $retryCount++
        }
    }
    Write-Error "Failed to write to $path after $maxRetries attempts."
}

# Create the CSV file if it doesn't exist
Create-CSVFile -csvPath $csvPath

$i = 0;
Write-Host Get-Date -Format "MM_yyyy"
ForEach ($file in $filelist)
{
    $i++;
    $oldfile = $file.BaseName + $file.Extension;
    $newfile = $file.BaseName + ".mp4";
    $newfile2 = $file.BaseName + (Get-Date -Format "_E_MM_yyyy")+".mp4";
    $progress = ($i / $filecount) * 100
    $progress = [Math]::Round($progress,2)
    
    # Clear-Host
    Write-Host -------------------------------------------------------------------------------
    Write-Host Video Batch Encoding
    Write-Host "Processing - $oldfile"
    Write-Host "File $i of $filecount - $progress%"
    Write-Host "File Name: $oldfile"
    Write-Host "New File Name: $newfile"
    Write-Host "New File Name with Date: $newfile2"
    Write-Host ----------------- Checking if file is 4k --------------------------------------------------------------
    
    if (-not (Test-Path -Path $icloud\$oldfile)) {
        Write-Host "Error: File not found - $icloud\$oldfile"
        continue
    }

    $imgsize= exiftool.exe -imageheight $icloud\$oldfile | Select-String -Pattern '2160' -CaseSensitive -SimpleMatch
    $is4k = $false
    if ($imgsize -ne $null)
    {
        Write-Host $imgsize
        $a = $imgsize.ToString()
        $a = $a.Substring($a.length-4,4)
        if($a -contains 2160)
        {
            $is4k = $true
            Write-Host ------------------------- Media is 4k -------------------------------- 
        }
    }

    $fileDate = $null
    try {
        $fileDate = [datetime]::ParseExact($file.BaseName.Substring($file.BaseName.Length - 7), "MM_yyyy", $null)
        Write-Host "File Date: $fileDate"
    }
    catch {
        Write-Host "File name does not contain a valid date. Treating as a new file."
    }

    $isOlderThanYear = $false
    $isOlderThanTwoYears = $false
    $isOlderThanThreeYears = $false
    if ($fileDate -ne $null) {
        $isOlderThanYear = ($fileDate -lt (Get-Date).AddYears(-1))
        $isOlderThanTwoYears = ($fileDate -lt (Get-Date).AddYears(-2))
        $isOlderThanThreeYears = ($fileDate -lt (Get-Date).AddYears(-3))
        Write-Host "Is Older Than Year: $isOlderThanYear"
        Write-Host "Is Older Than Two Years: $isOlderThanTwoYears"
        Write-Host "Is Older Than Three Years: $isOlderThanThreeYears"
    }

    if ($is4k -or $isOlderThanYear -or $isOlderThanTwoYears -or $isOlderThanThreeYears)
    {
        Write-Host --------------------------Starting the process--------------------------- 
        if ($is4k -and $fileDate -eq $null)
        {
            Write-Host --------------------------Step 1 : Backing up the Media---------------------------
            Copy-Item -Path $icloud\$oldfile -Destination $remoteFilePath
            if (-not (Test-Path -Path $remoteFilePath\$oldfile -PathType Leaf))
            {
                Write-Host "Backup failed. Skipping file."
                continue
            }
            Write-Host "--------------------------Backup complete & verified---------------------------"
        }

        Write-Host --------------------------Step 2 : Starting Video compression--------------------------- 
        $resolution = ""
        if ($is4k -and $fileDate -eq $null)
        {
            $newfile = $file.BaseName + "_4k.mp4"
            $newfile2 = $file.BaseName + "_4k_" + (Get-Date -Format "_E_MM_yyyy")+".mp4"
            ffmpeg.exe -noautorotate -i $icloud\$oldfile -crf 25 -vf scale=-1:2160 -map_metadata 0 -codec:v libx264 -preset superfast $icloud\$newfile
            $resolution = "4k"
        }
        elseif ($isOlderThanThreeYears)
        {
            $newfile = $file.BaseName + "_480.mp4"
            $newfile2 = $file.BaseName + "_480_" + (Get-Date -Format "_E_MM_yyyy")+".mp4"
            ffmpeg.exe -noautorotate -i $icloud\$oldfile -crf 25 -vf scale=-1:480 -map_metadata 0 -codec:v libx264 -preset superfast $icloud\$newfile
            $resolution = "480"
        }
        elseif ($isOlderThanTwoYears)
        {
            $newfile = $file.BaseName + "_720.mp4"
            $newfile2 = $file.BaseName + "_720_" + (Get-Date -Format "_E_MM_yyyy")+".mp4"
            ffmpeg.exe -noautorotate -i $icloud\$oldfile -crf 25 -vf scale=-1:720 -map_metadata 0 -codec:v libx264 -preset superfast $icloud\$newfile
            $resolution = "720"
        }
        elseif ($isOlderThanYear)
        {
            $newfile = $file.BaseName + "_1080.mp4"
            $newfile2 = $file.BaseName + "_1080_" + (Get-Date -Format "_E_MM_yyyy")+".mp4"
            ffmpeg.exe -noautorotate -i $icloud\$oldfile -crf 25 -vf scale=-1:1080 -map_metadata 0 -codec:v libx264 -preset superfast $icloud\$newfile
            $resolution = "1080"
        }
        Write-Host --------------------------Step 2 : Complete---------------------------
        Write-Host --------------------------Step 3 : Correcting Dates for the media---------------------------
        exiftool.exe -api QuickTimeUTC -tagsfromfile $icloud\$oldfile -extractEmbedded -all:all -"*gps*" -time:all --FileAccessDate --FileInodeChangeDate -FileModifyDate -ext mp4 -overwrite_original "-CreateDate<CreationDate" $icloud\$newfile
        Write-Host --------------------------Step 3 : Complete---------------------------
        Write-Host --------------------------Step 4 : Corrrecting GPS data for media---------------------------  
        mp4extract moov/meta $icloud\$oldfile source-metadata
        mp4edit --insert moov:source-metadata $icloud\$newfile $icloud\$newfile2
        Write-Host --------------------------Step 4 : Complete---------------------------
        Write-Host --------------------------Updating analytics--------------------------- 
        $oldsize=((Get-Item -Path  $icloud\$oldfile).Length/1MB).ToString()
        $newsize=((Get-Item -Path  $icloud\$newfile2).Length/1MB).ToString()
        $a=$oldsize+','+$newsize+','+$oldfile 
        Add-ContentWithRetry -path $remoteFilePath\conversion.csv -value $a
        Write-Host --------------------------Step 4 : Complete---------------------------
        # Commenting out the deletion of old media
        # Write-Host --------------------------Step 5 : Deleting Old media---------------------------  
        # Remove-Item -Path $icloud\$oldfile
        # Remove-Item -Path $icloud\$newfile
        # Add-Content -Path C:\Users\Amit\Desktop\icloud_photos_downloader\tobedeleted.csv -Value $oldfile
        Write-Host --------------------------All Steps Completed Successfully---------------------------

        # Extract metadata
        $metadata = exiftool.exe $icloud\$oldfile

        # Insert data into the CSV file
        Insert-CompressionData -csvPath $csvPath -fileName $oldfile -filePath $icloud -oldSize $oldsize -newSize $newsize -resolution $resolution -dateProcessed (Get-Date) -metadata $metadata
    }
}
read-host “Press ENTER to continue...”