/**
 * Manual iCloud Upload Button Debugger
 * 
 * This script opens iCloud Photos in a visible browser and helps you
 * manually find the upload button by clicking elements and showing details.
 * 
 * Usage: node scripts/debug_icloud_upload.js
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';

const COOKIE_FILE = path.resolve('./cookies.json');
const ICLOUD_PHOTOS_URL = 'https://www.icloud.com/photos/';

async function loadCookies(page) {
  if (!await fs.pathExists(COOKIE_FILE)) return false;
  const cookies = await fs.readJson(COOKIE_FILE);
  await page.setCookie(...cookies);
  return true;
}

async function saveCookies(page) {
  const cookies = await page.cookies();
  await fs.writeJson(COOKIE_FILE, cookies, { spaces: 2 });
  console.log('Saved cookies to', COOKIE_FILE);
}

async function debugUploadButton() {
  console.log('🔍 Starting iCloud Upload Button Debugger...');
  console.log('This will open a visible browser window for manual inspection.');
  console.log('Press Ctrl+C to exit when done.\n');

  const browser = await puppeteer.launch({
    headless: false, // Always visible for debugging
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

  // Load cookies if present
  const cookiesLoaded = await loadCookies(page);
  if (cookiesLoaded) {
    console.log('✅ Loaded cookies from', COOKIE_FILE);
  }

  try {
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
      console.log('🔐 Login required. Please complete login and 2FA in the browser window.');
      console.log('⏳ Waiting for authentication to complete...');
      
      await page.waitForNavigation({ 
        waitUntil: 'networkidle2', 
        timeout: 300000 // 5 minutes
      });
      
      console.log('✅ Authentication completed! Saving cookies...');
      await saveCookies(page);
    }

    // Wait for page to stabilize
    await new Promise(resolve => setTimeout(resolve, 3000));

    console.log('\n🔍 Analyzing page elements...');
    
    // Get all clickable elements
    const elements = await page.evaluate(() => {
      const clickableSelectors = [
        'button', 'div[role="button"]', 'span[role="button"]', 'a[role="button"]',
        '[onclick]', '[class*="button"]', '[class*="upload"]', '[class*="add"]',
        '[class*="import"]', '[class*="plus"]', 'input[type="file"]'
      ];
      
      const allElements = [];
      
      clickableSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach((el, index) => {
          const rect = el.getBoundingClientRect();
          const isVisible = rect.width > 0 && rect.height > 0 && 
                           window.getComputedStyle(el).visibility !== 'hidden' &&
                           window.getComputedStyle(el).display !== 'none';
          
          allElements.push({
            selector: selector,
            index: index,
            tagName: el.tagName,
            textContent: el.textContent?.trim() || '',
            ariaLabel: el.getAttribute('aria-label') || '',
            title: el.getAttribute('title') || '',
            className: el.className || '',
            id: el.id || '',
            dataTestId: el.getAttribute('data-testid') || '',
            visible: isVisible,
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          });
        });
      });
      
      return allElements;
    });

    console.log(`\n📊 Found ${elements.length} clickable elements:`);
    console.log('=' .repeat(80));
    
    elements.forEach((el, i) => {
      if (el.visible) {
        console.log(`\n${i + 1}. ${el.tagName} (${el.selector})`);
        console.log(`   Text: "${el.textContent}"`);
        console.log(`   Aria Label: "${el.ariaLabel}"`);
        console.log(`   Title: "${el.title}"`);
        console.log(`   Class: "${el.className}"`);
        console.log(`   ID: "${el.id}"`);
        console.log(`   Data Test ID: "${el.dataTestId}"`);
        console.log(`   Position: (${el.x}, ${el.y}) Size: ${el.width}x${el.height}`);
      }
    });

    console.log('\n🎯 MANUAL TESTING INSTRUCTIONS:');
    console.log('1. Look at the browser window that opened');
    console.log('2. Try to find the upload button manually');
    console.log('3. Right-click on potential upload buttons and select "Inspect Element"');
    console.log('4. Look for elements with classes or attributes related to upload/add/import');
    console.log('5. Check if there are any hidden file input elements');
    console.log('6. Look for drag-and-drop areas');
    
    console.log('\n🔧 TESTING FILE CHOOSER:');
    console.log('Try clicking on different elements in the browser to see if any open a file chooser.');
    console.log('If you find one that works, note its details above.');
    
    console.log('\n⏹️  Press Ctrl+C to close the browser and exit.');
    
    // Keep the browser open for manual inspection
    await new Promise(() => {}); // This will keep the script running indefinitely
    
  } catch (error) {
    console.error('❌ Error during debugging:', error);
  } finally {
    await browser.close();
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n👋 Closing browser and exiting...');
  process.exit(0);
});

debugUploadButton().catch(console.error);
