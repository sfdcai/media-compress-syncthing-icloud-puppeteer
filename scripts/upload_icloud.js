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
  console.log('Navigating to iCloud Photos...');
  await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
  
  const currentUrl = page.url();
  console.log('Current URL after navigation:', currentUrl);
  
  // Check for various login/authentication pages
  const isLoginPage = currentUrl.includes('appleid.apple.com') || 
                     currentUrl.includes('signin') || 
                     currentUrl.includes('login') ||
                     currentUrl.includes('auth') ||
                     currentUrl.includes('authentication');
  
  if (isLoginPage) {
    console.log('Detected login/authentication page');
    
    if (!interactive) {
      console.log('Not in interactive mode. Please run with --interactive flag to complete login.');
      throw new Error('Not logged in. Run once with --interactive to complete Apple login & MFA.');
    }
    
    console.log('Interactive mode enabled. Please complete login and 2FA in the opened browser.');
    console.log('Waiting for authentication to complete (up to 5 minutes)...');
    
    try {
      // Wait for navigation away from login page
      await page.waitForNavigation({ 
        waitUntil: 'networkidle2', 
        timeout: 300000 // 5 minutes
      });
      
      const newUrl = page.url();
      console.log('Navigation completed. New URL:', newUrl);
      
      // Check if we're still on a login page
      const stillOnLoginPage = newUrl.includes('appleid.apple.com') || 
                              newUrl.includes('signin') || 
                              newUrl.includes('login') ||
                              newUrl.includes('auth') ||
                              newUrl.includes('authentication');
      
      if (stillOnLoginPage) {
        console.log('Still on login page. Authentication may have failed or timed out.');
        throw new Error('Authentication failed or timed out. Please try again.');
      }
      
      console.log('Authentication successful! Saving cookies...');
      await saveCookies(page);
      
    } catch (error) {
      if (error.name === 'TimeoutError') {
        console.log('Authentication timed out after 5 minutes.');
        throw new Error('Authentication timed out. Please try again with --interactive flag.');
      }
      throw error;
    }
  } else {
    console.log('Already logged in or on Photos page. Waiting for UI to stabilize...');
    // Wait a bit for UI to stabilize
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

async function findFileInputAndUpload(page, files) {
  console.log('Attempting to find upload control...');
  
  try {
    // First, let's see what's available on the page
    const availableElements = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button')).map(btn => ({
        tagName: btn.tagName,
        textContent: btn.textContent?.trim(),
        ariaLabel: btn.getAttribute('aria-label'),
        title: btn.getAttribute('title'),
        className: btn.className,
        id: btn.id,
        dataTestId: btn.getAttribute('data-testid')
      }));
      
      const inputs = Array.from(document.querySelectorAll('input')).map(input => ({
        tagName: input.tagName,
        type: input.type,
        className: input.className,
        id: input.id,
        dataTestId: input.getAttribute('data-testid')
      }));
      
      return { buttons, inputs };
    });
    
    console.log('Available buttons:', availableElements.buttons.length);
    console.log('Available inputs:', availableElements.inputs.length);
    
    // Log detailed button information for debugging
    console.log('\n=== DETAILED BUTTON ANALYSIS ===');
    availableElements.buttons.forEach((btn, i) => {
      console.log(`\nButton ${i}:`);
      console.log(`  Text: "${btn.textContent}"`);
      console.log(`  Aria Label: "${btn.ariaLabel}"`);
      console.log(`  Title: "${btn.title}"`);
      console.log(`  Class: "${btn.className}"`);
      console.log(`  ID: "${btn.id}"`);
      console.log(`  Data Test ID: "${btn.dataTestId}"`);
    });
    console.log('\n=== END BUTTON ANALYSIS ===\n');

    // Attempt 1: Try to find and click upload button with file chooser
    const uploadButtonSelectors = selectors.uploadButtonSelectors;
    console.log(`Trying ${uploadButtonSelectors.length} upload button selectors...`);

    for (let i = 0; i < uploadButtonSelectors.length; i++) {
      const sel = uploadButtonSelectors[i];
      console.log(`Trying selector ${i + 1}/${uploadButtonSelectors.length}: ${sel}`);
      
      const elements = await page.$$(sel);
      if (elements.length > 0) {
        console.log(`Found ${elements.length} element(s) with selector: ${sel}`);
        
        for (let j = 0; j < elements.length; j++) {
          const el = elements[j];
          try {
            // Get element details
            const elementInfo = await page.evaluate(el => ({
              textContent: el.textContent?.trim(),
              ariaLabel: el.getAttribute('aria-label'),
              title: el.getAttribute('title'),
              className: el.className,
              visible: el.offsetParent !== null
            }), el);
            
            console.log(`Element ${j + 1} info:`, elementInfo);
            
            if (elementInfo.visible) {
              console.log(`Attempting to click element ${j + 1}...`);
              
              const [fileChooser] = await Promise.all([
                page.waitForFileChooser({ timeout: 10000 }),
                el.click()
              ]);
              
              if (fileChooser) {
                console.log('File chooser opened, accepting files...');
                await fileChooser.accept(files);
                console.log('Files accepted successfully!');
                return true;
              }
            }
          } catch (e) {
            console.log(`Failed to click element ${j + 1}:`, e.message);
          }
        }
      }
    }

    // Attempt 2: directly find input[type=file] and upload
    console.log('Trying direct file input upload...');
    const fileInputs = await page.$$('input[type=file]');
    if (fileInputs.length) {
      console.log(`Found ${fileInputs.length} file input(s)`);
      await fileInputs[0].uploadFile(...files);
      console.log('Files uploaded via direct input!');
      return true;
    }

    // Attempt 3: Try clicking any clickable element to see if it opens file chooser
    console.log('Trying fallback method: clicking any clickable element...');
    const allClickableElements = await page.$$('button, div[role="button"], span[role="button"], a[role="button"], [onclick]');
    console.log(`Found ${allClickableElements.length} clickable elements`);
    
    for (let i = 0; i < Math.min(allClickableElements.length, 10); i++) {
      const element = allClickableElements[i];
      try {
        const elementInfo = await page.evaluate(el => ({
          tagName: el.tagName,
          textContent: el.textContent?.trim(),
          className: el.className,
          id: el.id,
          visible: el.offsetParent !== null
        }), element);
        
        if (elementInfo.visible) {
          console.log(`Trying clickable element ${i + 1}: ${elementInfo.tagName} - "${elementInfo.textContent}" - ${elementInfo.className}`);
          
          try {
            const [fileChooser] = await Promise.all([
              page.waitForFileChooser({ timeout: 3000 }),
              element.click()
            ]);
            
            if (fileChooser) {
              console.log('File chooser opened via fallback method!');
              await fileChooser.accept(files);
              console.log('Files accepted successfully!');
              return true;
            }
          } catch (e) {
            // No file chooser opened, continue to next element
          }
        }
      } catch (e) {
        // Element not clickable, continue
      }
    }

    console.log('No upload method worked');
    return false;
  } catch (err) {
    console.error('Upload attempt failed:', err.message);
    return false;
  }
}

async function processBatch(dir, options) {
  const interactive = options.interactive || false;
  const headless = (options.headless === undefined) ? HEADLESS_DEFAULT : options.headless;

  console.log(`Starting batch process in dir=${dir} interactive=${interactive} headless=${headless}`);

  let browser;
  try {
    // open browser
    browser = await puppeteer.launch({
      headless: headless,
      args: [
        '--no-sandbox', 
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ]
    });
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(120000);
    page.setDefaultTimeout(30000);

  // load cookies if present
  const cookiesLoaded = await loadCookies(page);
  if (cookiesLoaded) {
    console.log('Loaded cookies from', COOKIE_FILE);
  }

  await openICloudPhotos(page, interactive);

  // after navigation to photos, wait for UI
  await new Promise(resolve => setTimeout(resolve, 3000));

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
  } catch (error) {
    console.error('Error during batch processing:', error);
    if (browser) {
      try {
        await browser.close();
      } catch (closeError) {
        console.error('Error closing browser:', closeError);
      }
    }
    throw error;
  }
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
  console.error('Stack trace:', err.stack);
  process.exit(2);
});
