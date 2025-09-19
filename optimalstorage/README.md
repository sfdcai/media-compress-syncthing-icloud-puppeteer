Automated Software Installation, Video and Photo Processing, and Compression
============================================================================

This PowerShell project automates the installation of necessary tools for video and photo processing, including compression and storage management. It also includes scripts for encoding 4K videos to 1080p, resizing images, and storing metadata in a database. The script supports setting up your environment to process large volumes of media files and store them efficiently.

* * * * *

Table of Contents
-----------------

-   [Purpose](#purpose)
-   [Prerequisites](#prerequisites)
-   [Script Overview](#script-overview)
-   [Installation Steps](#installation-steps)
-   [Video Processing Script](#video-processing-script)
-   [Photo Processing Script](#photo-processing-script)
-   [Parameters and Configuration](#parameters-and-configuration)
-   [Error Handling](#error-handling)
-   [Troubleshooting](#troubleshooting)

* * * * *

Purpose
-------

This project is intended for users who need to:

1.  **Compress and resize video and photo files** on a regular basis.
2.  **Store compressed and raw media** files on a NAS or any external storage.
3.  **Log metadata** of original and processed media files into a database for future reference.
4.  **Automate** the media compression workflow using daily batch processing.

The project includes two PowerShell scripts:

-   **Video Processing Script**: Compresses videos by encoding 4K videos to 1080p using H264 encoding.
-   **Photo Processing Script**: Reduces the resolution of photos for more efficient storage.

The scripts use:

-   **FFmpeg** for video compression.
-   **ImageMagick** for image resizing.
-   **SQLite** for metadata logging.
-   **Bento4 (`mp4edit`)** for MP4 file manipulation and metadata cloning.

* * * * *

Prerequisites
-------------

Before running the script, ensure the following:

1.  **Windows OS**: Ensure you are running Windows 10, 11, or Server versions.
2.  **PowerShell**: Version 5.x or later.
3.  **Administrator Privileges**: The script modifies system-level configurations.
4.  **7-Zip**: Required for extracting `.7z` files. Download from [here](https://www.7-zip.org/).
5.  **A Network Attached Storage (NAS)**: You should have the NAS configured and accessible via a network path (e.g., `\\192.168.1.4\media`).

* * * * *

Script Overview
---------------

### Key Features:

-   **Software Installation**: The script installs and sets up the following tools:

    -   **FFmpeg**: For video encoding and compression.
    -   **ImageMagick**: For resizing and compressing images.
    -   **SQLite**: For logging file metadata in a local database.
    -   **Bento4 (`mp4edit`)**: For editing MP4 metadata.
-   **Media Processing**:

    -   **Video Compression**: The script processes videos by encoding 4K videos to 1080p using H264 compression.
    -   **Photo Compression**: Reduces the resolution and quality of images to a specified percentage, while retaining EXIF metadata.
-   **Storage Setup**: The processed files are saved in a NAS or specified external storage location.

-   **Metadata Logging**: A local SQLite database stores metadata such as the original file size, compressed file size, and paths for future reference.

* * * * *

Installation Steps
------------------

1.  **Download the Script**: Save the provided PowerShell script to your local system (e.g., `InstallTools.ps1`).

2.  **Open PowerShell as Administrator**:

    -   Press the `Windows` key, type `powershell`, and select **Run as Administrator**.
3.  **Change PowerShell Execution Policy** (if needed):

    powershell

    Copy code

    `Set-ExecutionPolicy RemoteSigned`

    This ensures you can run downloaded scripts.

4.  **Run the Installation Script**:

    powershell

    Copy code

    `.\InstallTools.ps1`

    The script will:

    -   Download and install FFmpeg, ImageMagick, SQLite, and Bento4.
    -   Add these tools to the system `PATH` so they can be accessed from the command line.
    -   Verify that all tools are correctly installed.
5.  **Verify Installation**: After the script completes, verify the installed tools by running:

    powershell

    Copy code

    `ffmpeg -version
    magick -version
    sqlite3 --version
    mp4edit --version`

* * * * *

Video Processing Script
-----------------------

This script compresses video files by encoding them to 1080p (H264) and clones the metadata using Bento4's `mp4edit`. It also logs the original and compressed file sizes in an SQLite database.

### Usage

1.  **Video Compression Script** (`CompressVideos.ps1`):

    powershell

    Copy code

    `.\CompressVideos.ps1 -MaxFilesToProcess 10 -CompressionQuality 23`

### Parameters:

-   **`-MaxFilesToProcess`**: The number of videos to process in a single run (e.g., 10).
-   **`-CompressionQuality`**: Specifies the quality level for H264 encoding (lower value = higher quality, default 23).

### Example Workflow:

1.  The script scans the source directory for video files.
2.  Compresses each 4K video to 1080p using FFmpeg.
3.  Retains video metadata using `mp4edit`.
4.  Stores the compressed videos in the destination directory (NAS).
5.  Logs the file names, original sizes, and compressed sizes in a local SQLite database (`VideoCompression.db`).

* * * * *

Photo Processing Script
-----------------------

This script resizes photos to reduce their resolution and file size while preserving the metadata (EXIF tags) and logs the changes in an SQLite database.

### Usage

1.  **Photo Compression Script** (`ResizePhotos.ps1`):

    powershell

    Copy code

    `.\ResizePhotos.ps1 -MaxFilesToProcess 20 -ResizePercentage 50`

### Parameters:

-   **`-MaxFilesToProcess`**: The number of photos to process per batch (e.g., 20).
-   **`-ResizePercentage`**: The percentage by which to reduce the image dimensions (e.g., 50%).

### Example Workflow:

1.  The script scans the source directory for image files (`*.jpg, *.png`).
2.  Resizes each image based on the provided percentage.
3.  Stores resized images in the destination directory (NAS).
4.  Logs the file names, original sizes, and resized file sizes in an SQLite database (`PhotoCompression.db`).

* * * * *

Parameters and Configuration
----------------------------

Both the **Video Processing** and **Photo Processing** scripts can be customized with the following parameters:

-   **Source Directory**: The folder containing the raw media files.
-   **Destination Directory**: The folder where processed files (videos or photos) will be saved. This should be the NAS or external storage path.
-   **MaxFilesToProcess**: The number of files to process in a single run (batch size).
-   **Compression Quality (for Videos)**: The H264 encoding quality setting.
-   **Resize Percentage (for Photos)**: The percentage to reduce the resolution of images.

### Example for Video Processing:

powershell

Copy code

`.\CompressVideos.ps1 -MaxFilesToProcess 10 -CompressionQuality 23`

### Example for Photo Processing:

powershell

Copy code

`.\ResizePhotos.ps1 -MaxFilesToProcess 20 -ResizePercentage 50`

* * * * *

Error Handling
--------------

The script implements error handling:

1.  **Retry Mechanism**: For each operation (e.g., downloading or processing a file), the script retries failed tasks up to 3 times.
2.  **Logging**: Errors are logged to the console for easy troubleshooting.
3.  **File Validation**: After processing each file, the script checks if the output file exists and logs an error if the process fails.

* * * * *

Troubleshooting
---------------

-   **Permissions**: Ensure PowerShell is running as Administrator to modify system variables and install software.
-   **Path Issues**: If the installed tools (FFmpeg, ImageMagick, etc.) aren't recognized after running the script, make sure the system `PATH` variable has been updated correctly. You may need to restart the system or open a new PowerShell session.
-   **NAS Connectivity**: Ensure the NAS is properly mounted and accessible over the network before running the scripts.

* * * * *

Future Enhancements
-------------------

-   **Compression Rate Control**: Add a user-specified compression rate for photos, not just resolution resizing.
-   **Support for More Formats**: Extend the script to handle more file formats (e.g., `.heic`, `.webp`).
-   **Automated Scheduling**: Use Windows Task Scheduler to automate the execution of these scripts at regular intervals (e.g., daily compression of new media files).


# Media Compression Script

This PowerShell script compresses both **videos** and **photos** from designated source directories. It supports **progressive compression**, meaning files that become older over time can be further compressed to save storage space.

## Features:
- **Video Compression**:
  - Initially compresses videos from 4K to 1080p.
  - After a specified number of years (default: 2 years), videos are further compressed to 720p.
  - Video metadata, including the original and compressed sizes, compression dates, and the number of compressions, is stored in an SQLite database (`VideoCompression.db`).

- **Photo Compression**:
  - Compresses photos by reducing their resolution.
  - First-time compression reduces the resolution to a specified percentage (default: 80%).
  - Older photos (default: 2 years old) are further compressed to an even lower resolution (default: 90% of the already compressed resolution).
  - Photo metadata is stored in an SQLite database (`PhotoCompression.db`).

- **Error Handling**: The script handles errors such as file read/write issues, database errors, and processing errors gracefully.

## Requirements:
- [FFmpeg](https://ffmpeg.org/) for video compression.
- [ImageMagick](https://imagemagick.org/) for image compression.
- [SQLite](https://sqlite.org/) for database management.
- [MP4Edit](https://www.bento4.com/documentation/mp4edit/) (optional) for advanced MP4 metadata handling.

## How to Use:

1. **Install Required Software**:
   - Install FFmpeg, ImageMagick, and SQLite as described in the installation script.
   
2. **Setup Script Parameters**:
   - You can modify the default parameters such as the source directories for videos and photos, the NAS storage location, and compression quality directly in the script.

3. **Running the Script**:
   - Execute the script using PowerShell:
     ```bash
     powershell.exe -File MediaCompression.ps1 -MaxFilesToProcess 10
     ```

4. **Customize Settings**:
   - Parameters like `CompressionIntervalYears`, `InitialResizePercentage`, `SubsequentResizePercentage`, `InitialVideoResolution`, and `VideoCompressionQuality` can be adjusted based on your storage requirements.

5. **Schedule the Script**:
   - You can use Windows Task Scheduler to run the script periodically (e.g., daily or weekly) to keep your media files compressed.

6. **Database**:
   - The script uses SQLite databases (`VideoCompression.db` and `PhotoCompression.db`) to store information about compressed files, their original and compressed sizes, compression dates, and the number of compressions performed.

## Example Usage:

```bash
powershell.exe -File MediaCompression.ps1 -MaxFilesToProcess 10 -InitialResizePercentage 80 -SubsequentResizePercentage 90 -VideoCompressionQuality 23

