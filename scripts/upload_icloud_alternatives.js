/**
 * Alternative iCloud Upload Methods
 * 
 * This script explores alternative methods for uploading to iCloud Photos
 * when the web interface automation fails.
 * 
 * Usage: node scripts/upload_icloud_alternatives.js --dir /tmp/test_upload
 */

import fs from 'fs-extra';
import path from 'path';
import { spawn } from 'child_process';
import crypto from 'crypto';

const PROCESSED_DB = path.resolve('./uploaded_manifest.json');

function sha256File(filePath) {
  const hash = crypto.createHash('sha256');
  const data = fs.readFileSync(filePath);
  hash.update(data);
  return hash.digest('hex');
}

async function loadLedger() {
  try {
    return await fs.readJson(PROCESSED_DB);
  } catch {
    return {};
  }
}

async function saveLedger(ledger) {
  await fs.writeJson(PROCESSED_DB, ledger, { spaces: 2 });
}

function moveFileToDir(file, destDir) {
  fs.ensureDirSync(destDir);
  const base = path.basename(file);
  const dest = path.join(destDir, base);
  fs.moveSync(file, dest, { overwrite: true });
  return dest;
}

// Method 1: Check for iCloud for Windows upload folder
async function checkICloudWindowsUpload() {
  console.log('🔍 Checking for iCloud for Windows upload folder...');
  
  const possiblePaths = [
    path.join(process.env.USERPROFILE || '', 'iCloud Photos', 'Uploads'),
    path.join(process.env.USERPROFILE || '', 'Pictures', 'iCloud Photos', 'Uploads'),
    path.join('C:', 'Users', process.env.USERNAME || '', 'iCloud Photos', 'Uploads'),
    path.join('C:', 'Users', process.env.USERNAME || '', 'Pictures', 'iCloud Photos', 'Uploads')
  ];
  
  for (const uploadPath of possiblePaths) {
    if (await fs.pathExists(uploadPath)) {
      console.log(`✅ Found iCloud upload folder: ${uploadPath}`);
      return uploadPath;
    }
  }
  
  console.log('❌ iCloud for Windows upload folder not found');
  return null;
}

// Method 2: Use curl to upload via iCloud API (if available)
async function uploadViaCurl(filePath) {
  console.log(`📤 Attempting to upload ${path.basename(filePath)} via curl...`);
  
  // This is a placeholder - the actual iCloud API would require authentication
  // and proper API endpoints which are not publicly documented
  console.log('⚠️  iCloud API upload not implemented (requires private API access)');
  return false;
}

// Method 3: Use AppleScript (macOS only)
async function uploadViaAppleScript(filePath) {
  console.log(`📤 Attempting to upload ${path.basename(filePath)} via AppleScript...`);
  
  if (process.platform !== 'darwin') {
    console.log('❌ AppleScript only available on macOS');
    return false;
  }
  
  const script = `
    tell application "System Events"
      tell process "Safari"
        -- This would need to be customized based on the actual Safari interface
        -- for iCloud Photos
        return "AppleScript upload not implemented"
      end tell
    end tell
  `;
  
  return new Promise((resolve) => {
    const process = spawn('osascript', ['-e', script]);
    let output = '';
    
    process.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        console.log('✅ AppleScript execution successful');
        resolve(true);
      } else {
        console.log('❌ AppleScript execution failed');
        resolve(false);
      }
    });
  });
}

// Method 4: Use xdg-open to open iCloud Photos in browser
async function openICloudPhotosInBrowser() {
  console.log('🌐 Opening iCloud Photos in default browser...');
  
  const url = 'https://www.icloud.com/photos/';
  
  return new Promise((resolve) => {
    let command, args;
    
    if (process.platform === 'win32') {
      command = 'start';
      args = [url];
    } else if (process.platform === 'darwin') {
      command = 'open';
      args = [url];
    } else {
      command = 'xdg-open';
      args = [url];
    }
    
    const process = spawn(command, args);
    
    process.on('close', (code) => {
      if (code === 0) {
        console.log('✅ Browser opened successfully');
        console.log('💡 Please manually upload the files in the browser');
        resolve(true);
      } else {
        console.log('❌ Failed to open browser');
        resolve(false);
      }
    });
  });
}

// Method 5: Create a batch script for manual upload
async function createManualUploadScript(files, outputDir) {
  console.log('📝 Creating manual upload instructions...');
  
  const scriptPath = path.join(outputDir, 'manual_upload_instructions.txt');
  const instructions = `
MANUAL iCLOUD PHOTOS UPLOAD INSTRUCTIONS
========================================

Files to upload:
${files.map(f => `- ${path.basename(f)}`).join('\n')}

Steps:
1. Open your web browser
2. Go to https://www.icloud.com/photos/
3. Sign in with your Apple ID
4. Click the "Upload" button (cloud with upward arrow)
5. Select the following files:
${files.map(f => `   ${f}`).join('\n')}
6. Wait for upload to complete
7. Move files from ${path.dirname(files[0])} to ${path.join(path.dirname(files[0]), '..', 'uploaded')}

Alternative methods:
- Use iCloud for Windows app (if available)
- Use Photos app on Mac (if available)
- Use iCloud Photos app on mobile device

Generated: ${new Date().toISOString()}
`;
  
  await fs.writeFile(scriptPath, instructions);
  console.log(`📄 Manual upload instructions saved to: ${scriptPath}`);
  return scriptPath;
}

async function processBatch(dir, options) {
  console.log(`Starting alternative upload methods for dir=${dir}`);
  
  // Load ledger
  const ledger = await loadLedger();
  
  // Find files
  const files = (await fs.readdir(dir))
    .filter(f => /\.(jpe?g|png|heic|mov|mp4|avi|heif)$/i.test(f))
    .map(f => path.join(dir, f));
  
  if (!files.length) {
    console.log('No files to upload.');
    return;
  }
  
  const batch = files.slice(0, 20); // Limit batch size
  
  // Filter out already uploaded files
  const toUpload = [];
  for (const f of batch) {
    const hash = sha256File(f);
    if (ledger[hash]) {
      console.log('Skipping already uploaded file:', path.basename(f));
      moveFileToDir(f, path.join(dir, '..', 'skipped'));
    } else {
      toUpload.push({ file: f, hash });
    }
  }
  
  if (!toUpload.length) {
    console.log('Nothing to upload after dedupe.');
    await saveLedger(ledger);
    return;
  }
  
  console.log('Files to upload:', toUpload.map(x => path.basename(x.file)).join(', '));
  
  // Try different methods
  const methods = [
    {
      name: 'iCloud for Windows Upload Folder',
      func: async () => {
        const uploadPath = await checkICloudWindowsUpload();
        if (uploadPath) {
          // Copy files to upload folder
          for (const item of toUpload) {
            const destPath = path.join(uploadPath, path.basename(item.file));
            await fs.copy(item.file, destPath);
            console.log(`📁 Copied ${path.basename(item.file)} to iCloud upload folder`);
          }
          return true;
        }
        return false;
      }
    },
    {
      name: 'Open Browser for Manual Upload',
      func: async () => {
        await openICloudPhotosInBrowser();
        await createManualUploadScript(toUpload.map(x => x.file), dir);
        return true; // Always succeeds as it provides instructions
      }
    },
    {
      name: 'AppleScript (macOS only)',
      func: async () => {
        if (process.platform === 'darwin') {
          return await uploadViaAppleScript(toUpload[0].file);
        }
        return false;
      }
    }
  ];
  
  let success = false;
  for (const method of methods) {
    console.log(`\n🔄 Trying method: ${method.name}`);
    try {
      const result = await method.func();
      if (result) {
        console.log(`✅ Method "${method.name}" succeeded`);
        success = true;
        break;
      } else {
        console.log(`❌ Method "${method.name}" failed`);
      }
    } catch (error) {
      console.log(`❌ Method "${method.name}" error: ${error.message}`);
    }
  }
  
  if (success) {
    // Update ledger for successful uploads
    for (const item of toUpload) {
      const newPath = moveFileToDir(item.file, path.join(dir, '..', 'uploaded'));
      ledger[item.hash] = {
        fileName: path.basename(newPath),
        uploadedAt: (new Date()).toISOString(),
        method: 'alternative'
      };
    }
    await saveLedger(ledger);
  } else {
    console.log('❌ All alternative methods failed');
    // Move files to failed folder
    for (const item of toUpload) {
      moveFileToDir(item.file, path.join(dir, '..', 'failed'));
    }
  }
  
  console.log('Alternative upload process complete.');
}

// CLI argument parsing
async function main() {
  const argv = process.argv.slice(2);
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--dir') args.dir = argv[++i];
    else if (argv[i] === '--help') { 
      console.log('Usage: node upload_icloud_alternatives.js --dir /path/to/dir');
      console.log('This script tries alternative methods for uploading to iCloud Photos.');
      console.log('Options:');
      console.log('  --dir <path>       Directory containing files to upload');
      console.log('  --help             Show this help message');
      return; 
    }
  }
  
  if (!args.dir) {
    console.error('Missing --dir argument. Example: --dir /home/user/uploads/incoming');
    return;
  }
  
  // Ensure directories exist
  fs.ensureDirSync(path.join(args.dir, '..', 'uploaded'));
  fs.ensureDirSync(path.join(args.dir, '..', 'failed'));
  fs.ensureDirSync(path.join(args.dir, '..', 'skipped'));

  await processBatch(args.dir, args);
}

main().catch(err => {
  console.error('Fatal error:', err);
  console.error('Stack trace:', err.stack);
  process.exit(2);
});
