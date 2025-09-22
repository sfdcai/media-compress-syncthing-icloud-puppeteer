/**
 * iCloud Upload Script using icloudpd
 * 
 * This script uses the icloudpd command-line tool to upload photos to iCloud,
 * which is more reliable than automating the web interface.
 * 
 * Usage: node scripts/upload_icloud_icloudpd.js --dir /tmp/test_upload
 */

import { spawn } from 'child_process';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';

const PROCESSED_DB = path.resolve('./uploaded_manifest.json'); // local ledger
const ICLOUDPD_PATH = '/opt/media-pipeline/venv/bin/icloudpd';

// Config
const BATCH_SIZE = 20; // change as needed
const MAX_RETRIES = 3;

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

async function uploadFileWithICloudPD(filePath, options = {}) {
  return new Promise((resolve, reject) => {
    console.log(`📤 Uploading ${path.basename(filePath)} using icloudpd...`);
    
    // icloudpd upload command
    const args = [
      '--upload-only',
      '--directory', path.dirname(filePath),
      '--include-video',
      '--include-photo',
      '--no-progress-bar',
      '--auto-delete' // Remove from local after successful upload
    ];
    
    // Add authentication options if provided
    if (options.username) args.push('--username', options.username);
    if (options.password) args.push('--password', options.password);
    if (options.cookieDirectory) args.push('--cookie-directory', options.cookieDirectory);
    
    const process = spawn(ICLOUDPD_PATH, args, {
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    
    process.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    process.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        console.log(`✅ Successfully uploaded ${path.basename(filePath)}`);
        resolve({ success: true, stdout, stderr });
      } else {
        console.error(`❌ Failed to upload ${path.basename(filePath)}: ${stderr}`);
        resolve({ success: false, stdout, stderr, code });
      }
    });
    
    process.on('error', (error) => {
      console.error(`❌ Error uploading ${path.basename(filePath)}: ${error.message}`);
      reject(error);
    });
  });
}

async function processBatch(dir, options) {
  console.log(`Starting batch process in dir=${dir}`);
  
  // Load ledger (uploaded hashes)
  const ledger = await loadLedger();
  
  // Find files in dir
  const files = (await fs.readdir(dir))
    .filter(f => /\.(jpe?g|png|heic|mov|mp4|avi|heif)$/i.test(f))
    .map(f => path.join(dir, f));
  
  if (!files.length) {
    console.log('No files to upload.');
    return;
  }
  
  // Prepare batch slice
  const batch = files.slice(0, Math.min(BATCH_SIZE, files.length));
  
  // Filter out known files by checksum
  const toUpload = [];
  for (const f of batch) {
    const hash = sha256File(f);
    if (ledger[hash]) {
      console.log('Skipping already uploaded file:', path.basename(f));
      // Move to uploaded folder immediately
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
  
  // Upload files using icloudpd
  const results = [];
  for (const item of toUpload) {
    try {
      const result = await uploadFileWithICloudPD(item.file, options);
      results.push({ file: item.file, result });
      
      if (result.success) {
        // Move to uploaded folder and update ledger
        const newPath = moveFileToDir(item.file, path.join(dir, '..', 'uploaded'));
        ledger[item.hash] = {
          fileName: path.basename(newPath),
          uploadedAt: (new Date()).toISOString(),
          method: 'icloudpd'
        };
      } else {
        // Move to failed folder
        moveFileToDir(item.file, path.join(dir, '..', 'failed'));
      }
    } catch (error) {
      console.error(`Error processing ${path.basename(item.file)}:`, error.message);
      // Move to failed folder
      moveFileToDir(item.file, path.join(dir, '..', 'failed'));
    }
  }
  
  // Save updated ledger
  await saveLedger(ledger);
  
  // Summary
  const successful = results.filter(r => r.result.success).length;
  const failed = results.length - successful;
  
  console.log(`\n📊 Upload Summary:`);
  console.log(`✅ Successful: ${successful}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📁 Total processed: ${results.length}`);
  
  if (failed > 0) {
    console.log(`\n❌ Failed uploads:`);
    results.filter(r => !r.result.success).forEach(r => {
      console.log(`   - ${path.basename(r.file)}: ${r.result.stderr}`);
    });
  }
  
  console.log('Batch complete.');
}

// CLI argument parsing
async function main() {
  const argv = process.argv.slice(2);
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--dir') args.dir = argv[++i];
    else if (argv[i] === '--username') args.username = argv[++i];
    else if (argv[i] === '--password') args.password = argv[++i];
    else if (argv[i] === '--cookie-directory') args.cookieDirectory = argv[++i];
    else if (argv[i] === '--help') { 
      console.log('Usage: node upload_icloud_icloudpd.js --dir /path/to/dir [options]');
      console.log('Options:');
      console.log('  --dir <path>           Directory containing files to upload');
      console.log('  --username <email>     iCloud username (optional, uses saved auth)');
      console.log('  --password <password>  iCloud password (optional, uses saved auth)');
      console.log('  --cookie-directory <path>  Directory for authentication cookies');
      console.log('  --help                 Show this help message');
      return; 
    }
  }
  
  if (!args.dir) {
    console.error('Missing --dir argument. Example: --dir /home/user/uploads/incoming');
    return;
  }
  
  // Ensure directories for result movement exist
  fs.ensureDirSync(path.join(args.dir, '..', 'uploaded'));
  fs.ensureDirSync(path.join(args.dir, '..', 'failed'));
  fs.ensureDirSync(path.join(args.dir, '..', 'skipped'));
  
  // Check if icloudpd is available
  if (!await fs.pathExists(ICLOUDPD_PATH)) {
    console.error(`❌ icloudpd not found at ${ICLOUDPD_PATH}`);
    console.error('Please ensure the Python virtual environment is properly set up.');
    return;
  }
  
  await processBatch(args.dir, args);
}

main().catch(err => {
  console.error('Fatal error:', err);
  console.error('Stack trace:', err.stack);
  process.exit(2);
});
