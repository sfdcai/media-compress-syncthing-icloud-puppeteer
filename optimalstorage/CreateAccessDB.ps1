function Create-AccessDatabase {
    param (
        [string]$dbPath,
        [string]$tableName
    )

    try {
        # Ensure the directory exists
        $directory = [System.IO.Path]::GetDirectoryName($dbPath)
        if (-not (Test-Path -Path $directory)) {
            throw "The directory '$directory' does not exist."
        }

        # Load the Access interop assembly
        Add-Type -AssemblyName "Microsoft.Office.Interop.Access"

        # Create a new Access application instance
        $accessApp = New-Object -ComObject Access.Application

        # Create a new database
        $accessApp.NewCurrentDatabase($dbPath)

        # SQL to create a new table
        $createTableSQL = @"
        CREATE TABLE $tableName (
            ID AUTOINCREMENT PRIMARY KEY,
            FileName TEXT(255),
            FilePath TEXT(255),
            DateProcessed DATETIME,
            OldSize TEXT(50),
            NewSize TEXT(50),
            Metadata TEXT
        )
"@

        # Execute the SQL to create the table
        $accessApp.DoCmd.RunSQL($createTableSQL)

        # Close the Access application
        $accessApp.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($accessApp) | Out-Null

        Write-Output "Database and table created successfully."
    }
    catch {
        Write-Error "An error occurred: $_"
    }
}

# Example usage
Create-AccessDatabase -dbPath "C:\Users\Amit\Desktop\Github\optimalstorage\database.accdb" -tableName "FileStorage"