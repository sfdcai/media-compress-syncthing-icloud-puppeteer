/**
 * Fixed iCloud Upload Script
 * 
 * This script uses the correct selectors found from Windows inspection
 * to upload files to iCloud Photos.
 * 
 * Usage: node scripts/upload_icloud_fixed.js --dir /tmp/test_upload --interactive
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
  console.log('✅ Saved cookies to', COOKIE_FILE);
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

async function findUploadButton(page) {
  console.log('🔍 Looking for upload button...');
  
  // Wait for page to be fully loaded
  await waitForPageToLoad(page);
  
  // Try the specific selectors we found from Windows inspection
  const selectors = [
    'ui-button.UploadButton',
    'ui-button[aria-label="Upload"]',
    'ui-button[title="Upload"]',
    'ui-button[class*="UploadButton"]',
    'ui-button.push.primary.PhotosButton.ToolbarButton.AppToolbarButton.UploadButton',
    'button[aria-label="Upload"]',
    'button[title="Upload"]',
    'input[type="file"]'
  ];
  
  for (const selector of selectors) {
    try {
      console.log(`🎯 Trying selector: ${selector}`);
      const elements = await page.$$(selector);
      
      if (elements.length > 0) {
        console.log(`✅ Found ${elements.length} element(s) with selector: ${selector}`);
        
        // Get element info for debugging
        for (let i = 0; i < elements.length; i++) {
          const element = elements[i];
          const elementInfo = await page.evaluate(el => ({
            tagName: el.tagName,
            textContent: el.textContent?.trim(),
            ariaLabel: el.getAttribute('aria-label'),
            title: el.getAttribute('title'),
            className: el.className,
            id: el.id,
            type: el.type,
            role: el.getAttribute('role'),
            visible: el.offsetWidth > 0 && el.offsetHeight > 0
          }), element);
          
          console.log(`Element ${i + 1} info:`, elementInfo);
          
          if (elementInfo.visible) {
            return { element, selector, info: elementInfo };
          }
        }
      }
    } catch (error) {
      console.log(`❌ Selector ${selector} failed: ${error.message}`);
    }
  }
  
  console.log('❌ No upload button found with any selector');
  return null;
}

async function attemptUpload(page, files, uploadButton) {
  console.log(`📤 Attempting upload with ${files.length} files...`);
  
  const { element, selector, info } = uploadButton;
  
  try {
    // Method 1: If it's a file input, use it directly
    if (info.type === 'file') {
      console.log('📁 Using direct file input method...');
      await element.uploadFile(...files);
      console.log('✅ Files uploaded via direct file input');
      return true;
    }
    
    // Method 2: Click the button and wait for file chooser
    console.log('🖱️  Using click + file chooser method...');
    
    // Set up file chooser listener
    const [fileChooser] = await Promise.all([
      page.waitForFileChooser({ timeout: 10000 }),
      element.click()
    ]);
    
    console.log('📂 File chooser opened, selecting files...');
    await fileChooser.accept(files);
    console.log('✅ Files selected in file chooser');
    
    // Wait a moment for the upload to start
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return true;
    
  } catch (error) {
    console.log(`❌ Upload failed: ${error.message}`);
    return false;
  }
}

async function processBatch(dir, options) {
  const interactive = options.interactive || false;
  const headless = (options.headless === undefined) ? HEADLESS_DEFAULT : options.headless;

  console.log(`Starting fixed batch process in dir=${dir} interactive=${interactive} headless=${headless}`);

  let browser;
  try {
    // Launch browser with optimized options
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
        '--disable-features=VizDisplayCompositor'
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
      console.log('✅ Loaded cookies from', COOKIE_FILE);
    }

    // Navigate to iCloud Photos
    console.log('🌐 Navigating to iCloud Photos...');
    await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
    
    const currentUrl = page.url();
    console.log('📍 Current URL:', currentUrl);
    
    // Check if we need to login
    const loginIndicators = await page.evaluate(() => {
      const signInButton = document.querySelector('button:contains("Sign In"), [aria-label*="Sign In"], [title*="Sign In"]');
      const loginForm = document.querySelector('form[action*="signin"], form[action*="login"]');
      const appleIdLogin = window.location.href.includes('appleid.apple.com');
      const signInText = document.body.textContent.toLowerCase().includes('sign in');
      
      return {
        hasSignInButton: !!signInButton,
        hasLoginForm: !!loginForm,
        isAppleIdPage: appleIdLogin,
        hasSignInText: signInText,
        currentUrl: window.location.href
      };
    });
    
    const needsLogin = loginIndicators.isAppleIdPage || 
                      loginIndicators.hasSignInButton || 
                      loginIndicators.hasLoginForm ||
                      loginIndicators.hasSignInText;
    
    console.log('🔍 Login check:', loginIndicators);
    
    if (needsLogin) {
      if (!interactive) {
        throw new Error('Not logged in. Run with --interactive to complete login.');
      }
      
      console.log('🔐 Login required. Please complete login and 2FA in the browser...');
      console.log('⏳ Waiting for you to complete login (timeout: 5 minutes)...');
      
      try {
        await page.waitForFunction(() => {
          const signInButton = document.querySelector('button:contains("Sign In"), [aria-label*="Sign In"], [title*="Sign In"]');
          const loginForm = document.querySelector('form[action*="signin"], form[action*="login"]');
          const appleIdLogin = window.location.href.includes('appleid.apple.com');
          const signInText = document.body.textContent.toLowerCase().includes('sign in');
          
          return !signInButton && !loginForm && !appleIdLogin && !signInText;
        }, { timeout: 300000 });
        
        console.log('✅ Login completed successfully');
        await saveCookies(page);
      } catch (error) {
        console.log('⚠️  Login timeout or detection failed, continuing anyway...');
        await saveCookies(page);
      }
    } else {
      console.log('✅ Already logged in or on Photos page');
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

    // Find upload button
    const uploadButton = await findUploadButton(page);
    
    if (!uploadButton) {
      throw new Error('Could not find upload button on the page');
    }

    // Attempt upload
    const filePaths = toUpload.map(x => x.file);
    const uploadSuccess = await attemptUpload(page, filePaths, uploadButton);
    
    if (!uploadSuccess) {
      throw new Error('Upload failed');
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
        method: 'web-fixed'
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
      console.log('Usage: node upload_icloud_fixed.js --dir /path/to/dir [options]');
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
