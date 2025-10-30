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
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

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
const UPLOAD_WAIT_MS = 300000; // wait up to 5 minutes for uploads to appear
const BATCH_SIZE = 20; // change as needed
const MAX_RETRIES = 3;
const HEADLESS_DEFAULT = true;
const SUPPORTED_VIDEO_EXTENSIONS = /\.(mp4|mov|m4v|mpg|mpeg|mpe|mp2|mpv|avi|mkv|webm)$/i;

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
  let lastCount = beforeCount;

  while (Date.now() - start < timeoutMs) {
    try {
      const { count, pendingUploads } = await page.evaluate(() => {
        const candidateNodes = document.querySelectorAll('[role="grid"] [role="gridcell"], .photoTile, .photo-item, [data-testid*="tile"]');
        const uploadIndicators = document.querySelectorAll('[data-testid*="upload"], [class*="upload"], [aria-live="polite"]');
        return {
          count: candidateNodes ? candidateNodes.length : document.querySelectorAll('img').length,
          pendingUploads: uploadIndicators ? uploadIndicators.length : 0,
        };
      });

      if (count !== lastCount) {
        console.log(`Gallery tile count: ${count} (was ${lastCount}), pending indicators: ${pendingUploads}`);
        lastCount = count;
      }

      if (count >= beforeCount + expectedIncrease) {
        console.log('Detected expected increase in gallery items.');
        return true;
      }

      if (selectors?.waitSelectors?.uploadComplete) {
        const completeVisible = await page.$eval(selectors.waitSelectors.uploadComplete, () => true).catch(() => false);
        if (completeVisible && pendingUploads === 0 && count >= beforeCount) {
          console.log('Upload completion indicator detected.');
          return true;
        }
      }
    } catch (error) {
      console.log('Gallery polling error, retrying:', error.message);
    }

    await new Promise(r => setTimeout(r, 2000));
  }

  return false;
}

async function getGalleryCount(page) {
  try {
    const count = await page.evaluate(() => {
      const gridCandidates = document.querySelectorAll('[role="grid"] [role="gridcell"], .photoTile, .photo-item, [data-testid*="tile"]');
      if (gridCandidates && gridCandidates.length) {
        return gridCandidates.length;
      }
      return document.querySelectorAll('img').length;
    });
    return count || 0;
  } catch (error) {
    console.log('Failed to determine gallery count:', error.message);
    return 0;
  }
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

async function waitForManualConfirmation(message) {
  try {
    const rl = readline.createInterface({ input, output });
    await rl.question(`${message}\n`);
    rl.close();
  } catch (error) {
    console.log('Could not prompt for keyboard confirmation automatically:', error.message);
    console.log('Waiting for Ctrl+C instead.');
    await new Promise(resolve => {
      const handler = () => {
        process.off('SIGINT', handler);
        resolve();
      };
      process.on('SIGINT', handler);
    });
  }
}

async function diagnoseUploadControls(page) {
  console.log('--- Upload control diagnostics ---');

  const probeSelectors = new Set([
    'pierce/ui-button.UploadButton',
    'pierce/ui-button[aria-label="Upload"]',
    'pierce/ui-toolbar-button[name="upload"]',
    'pierce/[data-testid="upload-button"]',
    'pierce/button[aria-label="Upload"]',
    'pierce/button[data-testid*="upload"]',
    ...(selectors?.uploadButtonSelectors ?? []),
    'pierce/input[type="file"][multiple]',
    'pierce/input[type="file"]',
    'input[type="file"]'
  ]);

  for (const selector of probeSelectors) {
    try {
      const handle = await page.$(selector);
      if (!handle) {
        console.log(`❌ ${selector} — not found`);
        continue;
      }

      const info = await handle.evaluate(el => ({
        tag: el.tagName,
        id: el.id || null,
        classes: el.className || null,
        ariaLabel: el.getAttribute('aria-label'),
        title: el.getAttribute('title'),
        text: (el.innerText || '').trim() || null,
        outerHTML: (el.outerHTML || '').slice(0, 280)
      }));
      const visible = await handle.evaluate(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length));
      console.log(`✅ ${selector} — tag=${info.tag} visible=${visible}`);
      if (info.id) console.log(`    id=${info.id}`);
      if (info.classes) console.log(`    class=${info.classes}`);
      if (info.ariaLabel) console.log(`    aria-label=${info.ariaLabel}`);
      if (info.title) console.log(`    title=${info.title}`);
      if (info.text) console.log(`    text=${info.text}`);
      console.log(`    snippet=${info.outerHTML}`);
      await handle.dispose();
    } catch (error) {
      console.log(`⚠️ ${selector} — error: ${error.message}`);
    }
  }

  try {
    const fileInputs = await page.evaluate(() => {
      const results = [];
      const queue = [];
      const visited = new WeakSet();
      if (typeof document !== 'undefined') {
        queue.push(document);
      }

      while (queue.length) {
        const node = queue.shift();
        if (!node || visited.has(node)) continue;
        visited.add(node);

        if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node;
          if (el.tagName === 'INPUT' && el.type === 'file') {
            results.push({
              multiple: !!el.multiple,
              accept: el.getAttribute('accept'),
              id: el.id || null,
              classes: el.className || null,
              ariaLabel: el.getAttribute('aria-label'),
              snippet: (el.outerHTML || '').slice(0, 280)
            });
          }
          if (el.children && el.children.length) {
            queue.push(...Array.from(el.children));
          }
          if (el.shadowRoot) {
            queue.push(el.shadowRoot);
          }
        } else if ((typeof Document !== 'undefined' && node instanceof Document) ||
                   (typeof ShadowRoot !== 'undefined' && node instanceof ShadowRoot)) {
          queue.push(...Array.from(node.children || []));
        }
      }

      return results;
    });

    if (fileInputs.length) {
      console.log('Discovered file inputs:');
      fileInputs.forEach((inputInfo, index) => {
        console.log(`  [${index}] multiple=${inputInfo.multiple} accept=${inputInfo.accept || 'any'}`);
        if (inputInfo.id) console.log(`      id=${inputInfo.id}`);
        if (inputInfo.classes) console.log(`      class=${inputInfo.classes}`);
        if (inputInfo.ariaLabel) console.log(`      aria-label=${inputInfo.ariaLabel}`);
        console.log(`      snippet=${inputInfo.snippet}`);
      });
    } else {
      console.log('No <input type="file"> elements discovered during traversal.');
    }
  } catch (error) {
    console.log('File input traversal failed:', error.message);
  }

  console.log('--- End of diagnostics ---');
}

async function locateUploadButton(page) {
  const candidates = [
    'pierce/ui-button.UploadButton',
    'pierce/ui-button[aria-label="Upload"]',
    'pierce/ui-toolbar-button[name="upload"]',
    'pierce/[data-testid="upload-button"]',
    'pierce/button[aria-label="Upload"]',
    'pierce/button[data-testid*="upload"]',
  ];

  for (const selector of candidates) {
    try {
      const handle = await page.waitForSelector(selector, { timeout: 2500 });
      if (handle) {
        const visible = await handle.evaluate(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length));
        if (visible) {
          console.log(`Found upload button using selector: ${selector}`);
          return { handle, selector };
        }
        await handle.dispose();
      }
    } catch (_) {
      // try next selector
    }
  }

  if (selectors?.uploadButtonSelectors?.length) {
    for (const selector of selectors.uploadButtonSelectors) {
      try {
        const handle = await page.$(selector);
        if (handle) {
          const visible = await handle.evaluate(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length));
          if (visible) {
            console.log(`Found upload button using fallback selector: ${selector}`);
            return { handle, selector };
          }
          await handle.dispose();
        }
      } catch (_) {
        // continue
      }
    }
  }

  return null;
}

async function locateUploadInput(page) {
  const directSelectors = [
    'pierce/input[type="file"][multiple]',
    'pierce/input[type="file"]',
    'input[type="file"]',
  ];

  for (const selector of directSelectors) {
    try {
      const handle = await page.waitForSelector(selector, { timeout: 2000 });
      if (handle) {
        console.log(`Resolved file input using selector: ${selector}`);
        return { handle, origin: selector };
      }
    } catch (_) {
      // try next
    }
  }

  try {
    const handle = await page.evaluateHandle(() => {
      const visited = new WeakSet();
      const queue = [];
      if (document) queue.push(document);

      while (queue.length) {
        const node = queue.shift();
        if (!node || visited.has(node)) continue;
        visited.add(node);

        if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node;
          if (el.tagName === 'INPUT' && el.type === 'file') {
            return el;
          }

          if (el.children && el.children.length) {
            queue.push(...Array.from(el.children));
          }

          if (el.shadowRoot) {
            queue.push(el.shadowRoot);
          }
        } else if ((typeof Document !== 'undefined' && node instanceof Document) ||
                   (typeof ShadowRoot !== 'undefined' && node instanceof ShadowRoot)) {
          queue.push(...Array.from(node.children || []));
        }
      }

      return null;
    });

    const elementHandle = handle.asElement();
    if (elementHandle) {
      console.log('Resolved file input using shadow DOM traversal.');
      return { handle: elementHandle, origin: 'shadow-root-traversal' };
    }
    await handle.dispose();
  } catch (error) {
    console.log('Shadow DOM traversal failed:', error.message);
  }

  return null;
}

async function triggerUploadInput(page, files) {
  const inputResult = await locateUploadInput(page);
  if (inputResult) {
    const { handle, origin } = inputResult;
    try {
      console.log(`Uploading files using input located from ${origin}`);
      if (typeof handle.setInputFiles === 'function') {
        await handle.setInputFiles(files);
      } else if (typeof handle.uploadFile === 'function') {
        await handle.uploadFile(...files);
      } else {
        throw new Error('Resolved upload input does not support file selection APIs');
      }
      await page.evaluate(el => {
        const trigger = (eventName) => {
          const event = new Event(eventName, { bubbles: true, composed: true });
          el.dispatchEvent(event);
        };
        trigger('input');
        trigger('change');
      }, handle);
      console.log('Files queued via upload input.');
      await handle.dispose();
      return true;
    } catch (error) {
      console.log('Failed to interact with resolved input:', error.message);
      await handle.dispose().catch(() => {});
    }
  }
  return false;
}

async function findFileInputAndUpload(page, files) {
  console.log('Attempting to find upload control...');

  try {
    if (await triggerUploadInput(page, files)) {
      return true;
    }

    const uploadButton = await locateUploadButton(page);
    if (uploadButton) {
      console.log(`Clicking upload button discovered via ${uploadButton.selector}`);
      await uploadButton.handle.click({ delay: 50 }).catch(error => {
        console.log('Failed to click upload button directly:', error.message);
      });
      await new Promise(resolve => setTimeout(resolve, 1000));
      await uploadButton.handle.dispose().catch(() => {});

      if (await triggerUploadInput(page, files)) {
        return true;
      }
    } else {
      console.log('Upload button not found via configured selectors.');
    }

    console.log('Unable to locate functional upload mechanism.');
    return false;
  } catch (err) {
    console.error('Upload attempt failed:', err.message);
    return false;
  }
}

async function processBatch(dir, options) {
  const interactive = options.interactive || false;
  const inspectUpload = options.inspectUpload || false;
  const headless = (options.headless === undefined)
    ? (interactive ? false : HEADLESS_DEFAULT)
    : options.headless;

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

  if (inspectUpload) {
    await diagnoseUploadControls(page);
    await saveCookies(page);
    if (interactive) {
      await waitForManualConfirmation('Diagnostics complete. Press ENTER when you are done inspecting the Photos UI.');
    }
    await browser.close();
    console.log('Inspection finished. No files were uploaded.');
    return;
  }

  // Load ledger (uploaded hashes)
  const ledger = await loadLedger();

  // find files in dir
  const dirEntries = await fs.readdir(dir, { withFileTypes: true });
  const files = dirEntries
    .filter(entry => entry.isFile() && SUPPORTED_VIDEO_EXTENSIONS.test(entry.name))
    .map(entry => path.join(dir, entry.name));

  if (!files.length) {
    console.log('No video files to upload.');
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
    else if (argv[i] === '--inspect-upload') args.inspectUpload = true;
    else if (argv[i] === '--help') { console.log('Usage: node upload_icloud.js --dir /path/to/dir [--interactive]'); return; }
  }
  if (!args.dir) {
    console.error('Missing --dir argument. Example: --dir /home/user/uploads/incoming');
    return;
  }

  if (args.inspectUpload && args.headless === undefined) {
    args.headless = false;
  }
  // Ensure directories for result movement exist
  fs.ensureDirSync(path.join(args.dir, '..', 'uploaded'));
  fs.ensureDirSync(path.join(args.dir, '..', 'failed'));
  fs.ensureDirSync(path.join(args.dir, '..', 'skipped'));

  await processBatch(args.dir, {
    interactive: !!args.interactive,
    headless: args.headless,
    inspectUpload: !!args.inspectUpload
  });
}

main().catch(err => {
  console.error('Fatal error:', err);
  console.error('Stack trace:', err.stack);
  process.exit(2);
});
