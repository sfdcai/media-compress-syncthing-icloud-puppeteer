/**
 * upload_icloud.js
 *
 * Usage:
 * 1) First run (interactive to complete Apple MFA):
 *    node upload_icloud.js --dir /path/to/batches --interactive
 *
 * 2) Subsequent runs (headless, automated):
 *    node upload_icloud.js --dir /path/to/batches
 *
 * The script expects folder structure:
 *  /path/to/batches/incoming/*.jpg
 *  It processes files up to BATCH_SIZE, uploads them, verifies, then moves to `uploaded/` or `failed/`.
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';

const COOKIE_FILE = path.resolve('./cookies.json');
const PROCESSED_DB = path.resolve('./uploaded_manifest.json'); // local ledger
const SELECTORS_FILE = path.resolve('./scripts/icloud_selectors.json');

// Load selectors from external file
let selectors;
try {
  selectors = JSON.parse(fs.readFileSync(SELECTORS_FILE, 'utf8'));
} catch (error) {
  console.error('Error loading selectors file:', error);
  process.exit(1);
}

// Config
const ICLOUD_PHOTOS_URL = 'https://www.icloud.com/photos/';
const UPLOAD_WAIT_MS = 120000; // wait up to 2 minutes for uploads to appear
const BATCH_SIZE = 20; // change as needed
const MAX_RETRIES = 3;
const HEADLESS_DEFAULT = true;

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

async function saveCookies(page) {
  const cookies = await page.cookies();
  await fs.writeJson(COOKIE_FILE, cookies, { spaces: 2 });
  console.log('Saved cookies to', COOKIE_FILE);
}

async function loadCookies(page) {
  if (!await fs.pathExists(COOKIE_FILE)) return false;
  const cookies = await fs.readJson(COOKIE_FILE);
  await page.setCookie(...cookies);
  return true;
}

function moveFileToDir(file, destDir) {
  fs.ensureDirSync(destDir);
  const base = path.basename(file);
  const dest = path.join(destDir, base);
  fs.moveSync(file, dest, { overwrite: true });
  return dest;
}

async function waitForUploadCountIncrease(page, beforeCount, expectedIncrease, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    // Count thumbnails - selector may need adjustment over time
    const count = await page.evaluate(() => {
      // Attempt to count photo tiles; site structure may change.
      // This is a heuristic: count nodes that resemble photo items.
      const grid = document.querySelectorAll('[role="grid"] img, .photoTile, .photo-item, .thumb');
      return grid ? grid.length : document.querySelectorAll('img').length;
    }).catch(() => 0);
    console.log(`Current gallery count: ${count}, waiting for ${beforeCount + expectedIncrease}`);
    if (count >= beforeCount + expectedIncrease) return true;
    await new Promise(r => setTimeout(r, 2000));
  }
  return false;
}

async function getGalleryCount(page) {
  // Heuristic: count likely photo thumbnails
  const count = await page.evaluate(() => {
    const gridCandidates = document.querySelectorAll('[role="grid"] img, .photoTile, .photo-item, .thumb');
    return gridCandidates ? gridCandidates.length : document.querySelectorAll('img').length;
  });
  return count || 0;
}

async function openICloudPhotos(page, interactive) {
  await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
  // If Apple login page detected, interactive must be true for MFA
  if (page.url().includes('appleid.apple.com') || page.url().includes('signin')) {
    if (!interactive) {
      throw new Error('Not logged in. Run once with --interactive to complete Apple login & MFA.');
    }
    console.log('On Apple login page — please complete login and 2FA in the opened browser.');
    // Wait for user to finish authentication
    await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 300000 }); // 5 min to login
    console.log('Login navigation completed, saving cookies.');
    await saveCookies(page);
  } else {
    // try to check if page loaded into Photos interface
    // Wait a bit for UI to stabilize
    await page.waitForTimeout(2000);
  }
}

async function findFileInputAndUpload(page, files) {
  // Common approach: find <input type="file"> and set files
  // iCloud Photos hides this inside a menu — simpler is to open the Upload dialog and use file chooser.
  // We'll try both methods.
  try {
    // Attempt 1: click upload button and waitForFileChooser
    const uploadButtonSelectors = selectors.uploadButtonSelectors;

    for (const sel of uploadButtonSelectors) {
      const el = await page.$(sel);
      if (!el) continue;
      try {
        const [fileChooser] = await Promise.all([
          page.waitForFileChooser({ timeout: 5000 }),
          el.click().catch(() => {})
        ]);
        if (fileChooser) {
          await fileChooser.accept(files);
          return true;
        }
      } catch (e) {
        // maybe no file chooser; fallthrough
      }
    }

    // Attempt 2: directly find input[type=file] and upload
    const fileInputs = await page.$$('input[type=file]');
    if (fileInputs.length) {
      await fileInputs[0].uploadFile(...files);
      return true;
    }

    // Attempt 3: use a direct script to create an input element and set files (rare)
    await page.evaluate(async (paths) => {
      // not possible to set real File objects in page context without file chooser
      return false;
    }, files);
  } catch (err) {
    console.warn('Upload attempt failed:', err.message);
  }
  return false;
}

async function processBatch(dir, options) {
  const interactive = options.interactive || false;
  const headless = (options.headless === undefined) ? HEADLESS_DEFAULT : options.headless;

  console.log(`Starting batch process in dir=${dir} interactive=${interactive} headless=${headless}`);

  // open browser
  const browser = await puppeteer.launch({
    headless: headless,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  page.setDefaultNavigationTimeout(120000);

  // load cookies if present
  const cookiesLoaded = await loadCookies(page);
  if (cookiesLoaded) {
    console.log('Loaded cookies from', COOKIE_FILE);
  }

  await openICloudPhotos(page, interactive);

  // after navigation to photos, wait for UI
  await page.waitForTimeout(3000);

  // Load ledger (uploaded hashes)
  const ledger = await loadLedger();

  // find files in dir
  const files = (await fs.readdir(dir))
    .filter(f => /\.(jpe?g|png|heic|mov|mp4|avi|heif)$/i.test(f))
    .map(f => path.join(dir, f));

  if (!files.length) {
    console.log('No files to upload.');
    await browser.close();
    return;
  }

  // prepare batch slice
  const batch = files.slice(0, Math.min(BATCH_SIZE, files.length));

  // filter out known files by checksum
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
    await browser.close();
    return;
  }

  console.log('Files to upload:', toUpload.map(x => path.basename(x.file)).join(', '));

  // Get gallery count before upload (for verification)
  const beforeCount = await getGalleryCount(page);
  console.log('Gallery count before upload:', beforeCount);

  // Attempt upload via file chooser
  const filePaths = toUpload.map(x => x.file);
  const successUpload = await findFileInputAndUpload(page, filePaths);
  if (!successUpload) {
    await browser.close();
    throw new Error('Could not find upload control on iCloud Photos page. Selectors may need updating.');
  }

  // Wait and verify
  const ok = await waitForUploadCountIncrease(page, beforeCount, filePaths.length, UPLOAD_WAIT_MS);
  if (!ok) {
    console.error('Upload verification failed (timed out). You should inspect browser session and adjust selectors/timeouts.');
    // move to failed folder
    for (const t of toUpload) {
      moveFileToDir(t.file, path.join(dir, '..', 'failed'));
    }
    await browser.close();
    return;
  }

  console.log('Upload seems to have succeeded. Moving files to uploaded folder and record ledger.');

  // Move files and update ledger
  for (const t of toUpload) {
    const newPath = moveFileToDir(t.file, path.join(dir, '..', 'uploaded'));
    ledger[t.hash] = {
      fileName: path.basename(newPath),
      uploadedAt: (new Date()).toISOString()
    };
  }
  await saveLedger(ledger);

  // Save cookies (refresh session)
  await saveCookies(page);

  await browser.close();
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
    else if (argv[i] === '--help') { console.log('Usage: node upload_icloud.js --dir /path/to/dir [--interactive]'); return; }
  }
  if (!args.dir) {
    console.error('Missing --dir argument. Example: --dir /home/user/uploads/incoming');
    return;
  }
  // Ensure directories for result movement exist
  fs.ensureDirSync(path.join(args.dir, '..', 'uploaded'));
  fs.ensureDirSync(path.join(args.dir, '..', 'failed'));
  fs.ensureDirSync(path.join(args.dir, '..', 'skipped'));

  await processBatch(args.dir, { interactive: !!args.interactive, headless: args.headless });
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(2);
});
