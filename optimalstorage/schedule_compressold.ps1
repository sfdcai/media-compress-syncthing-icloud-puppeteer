# Define the path to the compressold.ps1 script
$scriptPath = "C:\Users\Amit\Desktop\Github\optimalstorage\compressold.ps1"

# Define the number of files to process
$numFilesToProcess = 15

# Create the action to run the compressold.ps1 script
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File `"$scriptPath`" -numFilesToProcess $numFilesToProcess"

# Create the trigger to run the task daily at a specific time (e.g., 2:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# Define the task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the scheduled task
Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "DailyCompressOldFiles" -Description "Run compressold.ps1 daily to process 10 to 15 files"

Write-Host "Scheduled task 'DailyCompressOldFiles' created successfully."