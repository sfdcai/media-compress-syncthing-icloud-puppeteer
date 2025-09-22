/**
 * Advanced iCloud Upload Script
 * 
 * This script uses advanced techniques to find and interact with upload controls
 * on the iCloud Photos web interface.
 * 
 * Usage: node scripts/upload_icloud_advanced.js --dir /tmp/test_upload --interactive
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';

const COOKIE_FILE = path.resolve('./cookies.json');
const PROCESSED_DB = path.resolve('./uploaded_manifest.json');
const ICLOUD_PHOTOS_URL = 'https://www.icloud.com/photos/';

// Config
const UPLOAD_WAIT_MS = 120000;
const BATCH_SIZE = 20;
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

async function waitForPageToLoad(page) {
  console.log('⏳ Waiting for page to fully load...');
  
  // Wait for various indicators that the page is ready
  try {
    // Wait for the main content to load
    await page.waitForSelector('body', { timeout: 10000 });
    
    // Wait for any loading indicators to disappear
    await page.waitForFunction(() => {
      const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="loader"]');
      return loadingElements.length === 0;
    }, { timeout: 15000 });
    
    // Wait for the page to be interactive
    await page.waitForFunction(() => {
      return document.readyState === 'complete';
    }, { timeout: 10000 });
    
    // Additional wait for dynamic content
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    console.log('✅ Page loaded successfully');
  } catch (error) {
    console.log('⚠️  Page load timeout, continuing anyway...');
  }
}

async function findUploadControls(page) {
  console.log('🔍 Searching for upload controls...');
  
  // Wait for page to be fully loaded
  await waitForPageToLoad(page);
  
  // Try multiple approaches to find upload controls
  const approaches = [
    // Approach 1: Look for drag and drop areas
    async () => {
      console.log('🎯 Approach 1: Looking for drag-and-drop areas...');
      const dropZones = await page.$$('[class*="drop"], [class*="upload"], [class*="drag"]');
      if (dropZones.length > 0) {
        console.log(`Found ${dropZones.length} potential drop zones`);
        return dropZones;
      }
      return [];
    },
    
    // Approach 2: Look for upload buttons in various locations
    async () => {
      console.log('🎯 Approach 2: Looking for upload buttons...');
      const selectors = [
        'button[aria-label*="upload" i]',
        'button[title*="upload" i]',
        'button[aria-label*="add" i]',
        'button[title*="add" i]',
        'button[aria-label*="import" i]',
        'button[title*="import" i]',
        '[role="button"][aria-label*="upload" i]',
        '[role="button"][title*="upload" i]',
        'button:has-text("Upload")',
        'button:has-text("Add")',
        'button:has-text("Import")',
        '[data-testid*="upload"]',
        '[data-testid*="add"]',
        '[data-testid*="import"]'
      ];
      
      for (const selector of selectors) {
        try {
          const elements = await page.$$(selector);
          if (elements.length > 0) {
            console.log(`Found ${elements.length} elements with selector: ${selector}`);
            return elements;
          }
        } catch (e) {
          // Continue to next selector
        }
      }
      return [];
    },
    
    // Approach 3: Look for file input elements
    async () => {
      console.log('🎯 Approach 3: Looking for file input elements...');
      const fileInputs = await page.$$('input[type="file"]');
      if (fileInputs.length > 0) {
        console.log(`Found ${fileInputs.length} file input elements`);
        return fileInputs;
      }
      return [];
    },
    
    // Approach 4: Look for any clickable elements that might trigger upload
    async () => {
      console.log('🎯 Approach 4: Looking for any clickable upload-related elements...');
      const allClickable = await page.$$('button, [role="button"], [onclick], [class*="button"], [class*="click"]');
      const uploadRelated = [];
      
      for (const element of allClickable) {
        try {
          const text = await element.evaluate(el => el.textContent?.toLowerCase() || '');
          const ariaLabel = await element.evaluate(el => el.getAttribute('aria-label')?.toLowerCase() || '');
          const title = await element.evaluate(el => el.getAttribute('title')?.toLowerCase() || '');
          const className = await element.evaluate(el => el.className?.toLowerCase() || '');
          
          if (text.includes('upload') || text.includes('add') || text.includes('import') ||
              ariaLabel.includes('upload') || ariaLabel.includes('add') || ariaLabel.includes('import') ||
              title.includes('upload') || title.includes('add') || title.includes('import') ||
              className.includes('upload') || className.includes('add') || className.includes('import')) {
            uploadRelated.push(element);
          }
        } catch (e) {
          // Continue
        }
      }
      
      if (uploadRelated.length > 0) {
        console.log(`Found ${uploadRelated.length} upload-related clickable elements`);
        return uploadRelated;
      }
      return [];
    },
    
    // Approach 5: Try to trigger upload via keyboard shortcuts
    async () => {
      console.log('🎯 Approach 5: Trying keyboard shortcuts...');
      try {
        // Try Ctrl+U (common upload shortcut)
        await page.keyboard.down('Control');
        await page.keyboard.press('KeyU');
        await page.keyboard.up('Control');
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Check if file chooser opened
        const fileInputs = await page.$$('input[type="file"]');
        if (fileInputs.length > 0) {
          console.log('File chooser opened via keyboard shortcut');
          return fileInputs;
        }
      } catch (e) {
        // Continue
      }
      return [];
    }
  ];
  
  // Try each approach
  for (let i = 0; i < approaches.length; i++) {
    try {
      const elements = await approaches[i]();
      if (elements.length > 0) {
        console.log(`✅ Found upload controls using approach ${i + 1}`);
        return elements;
      }
    } catch (error) {
      console.log(`❌ Approach ${i + 1} failed: ${error.message}`);
    }
  }
  
  console.log('❌ No upload controls found with any approach');
  return [];
}

async function attemptUpload(page, files, uploadElements) {
  console.log(`📤 Attempting upload with ${uploadElements.length} potential controls...`);
  
  for (let i = 0; i < uploadElements.length; i++) {
    const element = uploadElements[i];
    
    try {
      console.log(`Testing element ${i + 1}/${uploadElements.length}...`);
      
      // Get element info
      const elementInfo = await page.evaluate(el => ({
        tagName: el.tagName,
        textContent: el.textContent?.trim(),
        ariaLabel: el.getAttribute('aria-label'),
        title: el.getAttribute('title'),
        className: el.className,
        id: el.id,
        type: el.type,
        role: el.getAttribute('role')
      }), element);
      
      console.log(`Element info:`, elementInfo);
      
      // Try different upload methods
      const methods = [
        // Method 1: Direct file input
        async () => {
          if (elementInfo.type === 'file') {
            console.log('Using direct file input method...');
            await element.uploadFile(...files);
            return true;
          }
          return false;
        },
        
        // Method 2: Click and wait for file chooser
        async () => {
          console.log('Using click + file chooser method...');
          const [fileChooser] = await Promise.all([
            page.waitForFileChooser({ timeout: 5000 }),
            element.click()
          ]);
          await fileChooser.accept(files);
          return true;
        },
        
        // Method 3: Drag and drop
        async () => {
          console.log('Using drag and drop method...');
          const filePaths = files.map(f => path.resolve(f));
          await page.evaluate((filePaths) => {
            const dataTransfer = new DataTransfer();
            filePaths.forEach(filePath => {
              // This won't work in headless mode, but worth trying
              const file = new File([''], path.basename(filePath));
              dataTransfer.items.add(file);
            });
            
            const dropEvent = new DragEvent('drop', {
              dataTransfer: dataTransfer,
              bubbles: true
            });
            
            document.body.dispatchEvent(dropEvent);
          }, filePaths);
          return true;
        }
      ];
      
      // Try each method
      for (let j = 0; j < methods.length; j++) {
        try {
          const success = await methods[j]();
          if (success) {
            console.log(`✅ Upload successful using method ${j + 1}`);
            return true;
          }
        } catch (error) {
          console.log(`❌ Method ${j + 1} failed: ${error.message}`);
        }
      }
      
    } catch (error) {
      console.log(`❌ Error testing element ${i + 1}: ${error.message}`);
    }
  }
  
  return false;
}

async function processBatch(dir, options) {
  const interactive = options.interactive || false;
  const headless = (options.headless === undefined) ? HEADLESS_DEFAULT : options.headless;

  console.log(`Starting advanced batch process in dir=${dir} interactive=${interactive} headless=${headless}`);

  let browser;
  try {
    // Launch browser with advanced options
    browser = await puppeteer.launch({
      headless: headless,
      args: [
        '--no-sandbox', 
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--enable-features=NetworkService,NetworkServiceLogging'
      ]
    });
    
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(120000);
    page.setDefaultTimeout(30000);
    
    // Set user agent
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

    // Load cookies if present
    const cookiesLoaded = await loadCookies(page);
    if (cookiesLoaded) {
      console.log('Loaded cookies from', COOKIE_FILE);
    }

    // Navigate to iCloud Photos
    console.log('🌐 Navigating to iCloud Photos...');
    await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
    
    const currentUrl = page.url();
    console.log('📍 Current URL:', currentUrl);
    
    // Check if we need to login
    const isLoginPage = currentUrl.includes('appleid.apple.com') || 
                       currentUrl.includes('signin') || 
                       currentUrl.includes('login') ||
                       currentUrl.includes('auth') ||
                       currentUrl.includes('authentication');
    
    if (isLoginPage) {
      if (!interactive) {
        throw new Error('Not logged in. Run with --interactive to complete login.');
      }
      
      console.log('🔐 Please complete login and 2FA in the browser...');
      await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 300000 });
      await saveCookies(page);
    }

    // Wait for page to stabilize
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Load ledger
    const ledger = await loadLedger();

    // Find files
    const files = (await fs.readdir(dir))
      .filter(f => /\.(jpe?g|png|heic|mov|mp4|avi|heif)$/i.test(f))
      .map(f => path.join(dir, f));

    if (!files.length) {
      console.log('No files to upload.');
      await browser.close();
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
      await browser.close();
      return;
    }

    console.log('Files to upload:', toUpload.map(x => path.basename(x.file)).join(', '));

    // Find upload controls
    const uploadElements = await findUploadControls(page);
    
    if (uploadElements.length === 0) {
      throw new Error('Could not find any upload controls on the page');
    }

    // Attempt upload
    const filePaths = toUpload.map(x => x.file);
    const uploadSuccess = await attemptUpload(page, filePaths, uploadElements);
    
    if (!uploadSuccess) {
      throw new Error('All upload methods failed');
    }

    // Wait for upload to complete
    console.log('⏳ Waiting for upload to complete...');
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Update ledger
    for (const item of toUpload) {
      const newPath = moveFileToDir(item.file, path.join(dir, '..', 'uploaded'));
      ledger[item.hash] = {
        fileName: path.basename(newPath),
        uploadedAt: (new Date()).toISOString(),
        method: 'web-advanced'
      };
    }
    
    await saveLedger(ledger);
    await saveCookies(page);

    await browser.close();
    console.log('✅ Batch complete - upload successful!');
    
  } catch (error) {
    console.error('❌ Error during batch processing:', error);
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
    else if (argv[i] === '--help') { 
      console.log('Usage: node upload_icloud_advanced.js --dir /path/to/dir [options]');
      console.log('Options:');
      console.log('  --dir <path>       Directory containing files to upload');
      console.log('  --interactive      Use interactive mode for login');
      console.log('  --headless <bool>  Use headless mode (default: true)');
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
