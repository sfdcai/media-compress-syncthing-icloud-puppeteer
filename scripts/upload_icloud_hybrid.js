/**
 * Hybrid iCloud Upload Script
 * 
 * This script tries the web interface first, and falls back to icloudpd if that fails.
 * 
 * Usage: node scripts/upload_icloud_hybrid.js --dir /tmp/test_upload
 */

import { spawn } from 'child_process';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';

const PROCESSED_DB = path.resolve('./uploaded_manifest.json');
const ICLOUDPD_PATH = '/opt/media-pipeline/venv/bin/icloudpd';

// Config
const BATCH_SIZE = 20;
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

async function uploadWithICloudPD(filePath) {
  return new Promise((resolve, reject) => {
    console.log(`📤 Uploading ${path.basename(filePath)} using icloudpd (fallback method)...`);
    
    const args = [
      '--upload-only',
      '--directory', path.dirname(filePath),
      '--include-video',
      '--include-photo',
      '--no-progress-bar',
      '--auto-delete'
    ];
    
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
        console.log(`✅ Successfully uploaded ${path.basename(filePath)} via icloudpd`);
        resolve({ success: true, method: 'icloudpd', stdout, stderr });
      } else {
        console.error(`❌ Failed to upload ${path.basename(filePath)} via icloudpd: ${stderr}`);
        resolve({ success: false, method: 'icloudpd', stdout, stderr, code });
      }
    });
    
    process.on('error', (error) => {
      console.error(`❌ Error uploading ${path.basename(filePath)} via icloudpd: ${error.message}`);
      reject(error);
    });
  });
}

async function processBatch(dir, options) {
  console.log(`Starting hybrid batch process in dir=${dir}`);
  
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
  
  const batch = files.slice(0, Math.min(BATCH_SIZE, files.length));
  
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
  
  // Try web interface first (import the web upload function)
  console.log('🌐 Attempting web interface upload...');
  try {
    const { processBatch: webProcessBatch } = await import('./upload_icloud.js');
    await webProcessBatch(dir, { ...options, interactive: false, headless: true });
    console.log('✅ Web interface upload successful');
    return;
  } catch (error) {
    console.log('❌ Web interface upload failed:', error.message);
    console.log('🔄 Falling back to icloudpd method...');
  }
  
  // Fallback to icloudpd
  if (!await fs.pathExists(ICLOUDPD_PATH)) {
    console.error(`❌ icloudpd not found at ${ICLOUDPD_PATH}`);
    console.error('Both web interface and icloudpd methods failed.');
    return;
  }
  
  const results = [];
  for (const item of toUpload) {
    try {
      const result = await uploadWithICloudPD(item.file);
      results.push({ file: item.file, result });
      
      if (result.success) {
        const newPath = moveFileToDir(item.file, path.join(dir, '..', 'uploaded'));
        ledger[item.hash] = {
          fileName: path.basename(newPath),
          uploadedAt: (new Date()).toISOString(),
          method: result.method
        };
      } else {
        moveFileToDir(item.file, path.join(dir, '..', 'failed'));
      }
    } catch (error) {
      console.error(`Error processing ${path.basename(item.file)}:`, error.message);
      moveFileToDir(item.file, path.join(dir, '..', 'failed'));
    }
  }
  
  await saveLedger(ledger);
  
  const successful = results.filter(r => r.result.success).length;
  const failed = results.length - successful;
  
  console.log(`\n📊 Upload Summary (${results[0]?.result.method || 'unknown'} method):`);
  console.log(`✅ Successful: ${successful}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📁 Total processed: ${results.length}`);
  
  console.log('Batch complete.');
}

// CLI argument parsing
async function main() {
  const argv = process.argv.slice(2);
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--dir') args.dir = argv[++i];
    else if (argv[i] === '--interactive') args.interactive = true;
    else if (argv[i] === '--headless') args.headless = argv[++i] === 'true';
    else if (argv[i] === '--help') { 
      console.log('Usage: node upload_icloud_hybrid.js --dir /path/to/dir [options]');
      console.log('Options:');
      console.log('  --dir <path>       Directory containing files to upload');
      console.log('  --interactive      Use interactive mode for web interface');
      console.log('  --headless <bool>  Use headless mode for web interface');
      console.log('  --help             Show this help message');
      console.log('');
      console.log('This script tries web interface first, then falls back to icloudpd.');
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
