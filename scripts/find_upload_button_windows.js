/**
 * Windows Upload Button Finder
 * 
 * This script runs on Windows and helps identify the correct selectors
 * for the iCloud Photos upload button. It will open a visible browser
 * and provide detailed information about all elements on the page.
 * 
 * Usage: node scripts/find_upload_button_windows.js
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
  console.log('✅ Saved cookies to', COOKIE_FILE);
}

async function takeScreenshot(page, filename) {
  try {
    await page.screenshot({ 
      path: filename, 
      fullPage: true,
      type: 'png'
    });
    console.log(`📸 Screenshot saved: ${filename}`);
  } catch (error) {
    console.log(`❌ Failed to take screenshot: ${error.message}`);
  }
}

async function findUploadButtonOnWindows() {
  console.log('🖥️  Windows Upload Button Finder');
  console.log('=' .repeat(50));
  console.log('This will open a visible browser window for you to inspect.');
  console.log('Please complete login if needed, then look for the upload button.');
  console.log('');

  const browser = await puppeteer.launch({
    headless: false, // Always visible on Windows
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

  try {
    // Load cookies if present
    const cookiesLoaded = await loadCookies(page);
    if (cookiesLoaded) {
      console.log('✅ Loaded cookies from', COOKIE_FILE);
    }

    console.log('🌐 Navigating to iCloud Photos...');
    await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
    
    const currentUrl = page.url();
    console.log('📍 Current URL:', currentUrl);
    
    // Take initial screenshot
    await takeScreenshot(page, 'icloud_photos_initial.png');
    
    // Check if we need to login
    const isLoginPage = currentUrl.includes('appleid.apple.com') || 
                       currentUrl.includes('signin') || 
                       currentUrl.includes('login') ||
                       currentUrl.includes('auth') ||
                       currentUrl.includes('authentication');
    
    if (isLoginPage) {
      console.log('🔐 Login page detected.');
      console.log('Please complete login and 2FA in the browser window.');
      console.log('Press Enter here when you reach the Photos interface...');
      
      // Wait for user to complete login
      await new Promise(resolve => {
        process.stdin.once('data', () => {
          resolve();
        });
      });
      
      await saveCookies(page);
    }

    // Wait for page to stabilize
    console.log('⏳ Waiting for page to stabilize...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Take screenshot after login
    await takeScreenshot(page, 'icloud_photos_after_login.png');

    console.log('\n🔍 Analyzing page for upload controls...');
    
    // Get comprehensive page analysis
    const pageAnalysis = await page.evaluate(() => {
      // Get all possible elements that could be upload controls
      const allElements = [];
      
      // Get all clickable elements
      const clickableSelectors = [
        'button', 'input[type="button"]', 'input[type="submit"]',
        'div[role="button"]', 'span[role="button"]', 'a[role="button"]',
        '[onclick]', '[class*="button"]', '[class*="btn"]',
        '[class*="upload"]', '[class*="add"]', '[class*="import"]',
        '[class*="plus"]', '[class*="create"]', '[class*="new"]',
        'input[type="file"]', 'label[for]', '[draggable="true"]'
      ];
      
      clickableSelectors.forEach(selector => {
        try {
          const elements = document.querySelectorAll(selector);
          elements.forEach((el, index) => {
            const rect = el.getBoundingClientRect();
            const computedStyle = window.getComputedStyle(el);
            
            const isVisible = rect.width > 0 && rect.height > 0 && 
                             computedStyle.visibility !== 'hidden' &&
                             computedStyle.display !== 'none' &&
                             computedStyle.opacity !== '0';
            
            const elementInfo = {
              selector: selector,
              index: index,
              tagName: el.tagName,
              textContent: el.textContent?.trim() || '',
              innerHTML: el.innerHTML?.trim() || '',
              ariaLabel: el.getAttribute('aria-label') || '',
              title: el.getAttribute('title') || '',
              className: el.className || '',
              id: el.id || '',
              dataTestId: el.getAttribute('data-testid') || '',
              type: el.type || '',
              role: el.getAttribute('role') || '',
              draggable: el.getAttribute('draggable') || '',
              visible: isVisible,
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              zIndex: computedStyle.zIndex,
              position: computedStyle.position,
              display: computedStyle.display,
              visibility: computedStyle.visibility,
              opacity: computedStyle.opacity,
              backgroundColor: computedStyle.backgroundColor,
              color: computedStyle.color
            };
            
            allElements.push(elementInfo);
          });
        } catch (e) {
          // Skip invalid selectors
        }
      });
      
      // Get page metadata
      const pageInfo = {
        title: document.title,
        url: window.location.href,
        bodyClasses: document.body.className,
        hasFileInput: document.querySelector('input[type="file"]') !== null,
        totalElements: document.querySelectorAll('*').length,
        totalButtons: document.querySelectorAll('button').length,
        totalInputs: document.querySelectorAll('input').length,
        totalDivs: document.querySelectorAll('div').length,
        totalSpans: document.querySelectorAll('span').length,
        totalLinks: document.querySelectorAll('a').length
      };
      
      return {
        pageInfo,
        elements: allElements.sort((a, b) => {
          // Sort by visibility first, then by position
          if (a.visible !== b.visible) return b.visible - a.visible;
          return a.y - b.y;
        })
      };
    });

    // Display page information
    console.log('\n📊 PAGE ANALYSIS:');
    console.log('=' .repeat(60));
    console.log(`Title: ${pageAnalysis.pageInfo.title}`);
    console.log(`URL: ${pageAnalysis.pageInfo.url}`);
    console.log(`Body Classes: ${pageAnalysis.pageInfo.bodyClasses}`);
    console.log(`Total Elements: ${pageAnalysis.pageInfo.totalElements}`);
    console.log(`Buttons: ${pageAnalysis.pageInfo.totalButtons}`);
    console.log(`Inputs: ${pageAnalysis.pageInfo.totalInputs}`);
    console.log(`File Inputs: ${pageAnalysis.pageInfo.hasFileInput ? 'YES' : 'NO'}`);

    // Display visible clickable elements
    const visibleElements = pageAnalysis.elements.filter(el => el.visible);
    console.log(`\n🎯 VISIBLE CLICKABLE ELEMENTS (${visibleElements.length}):`);
    console.log('=' .repeat(60));
    
    visibleElements.forEach((el, i) => {
      console.log(`\n${i + 1}. ${el.tagName.toUpperCase()}`);
      console.log(`   Selector: ${el.selector}`);
      console.log(`   Text: "${el.textContent}"`);
      console.log(`   Aria Label: "${el.ariaLabel}"`);
      console.log(`   Title: "${el.title}"`);
      console.log(`   Class: "${el.className}"`);
      console.log(`   ID: "${el.id}"`);
      console.log(`   Data Test ID: "${el.dataTestId}"`);
      console.log(`   Type: "${el.type}"`);
      console.log(`   Role: "${el.role}"`);
      console.log(`   Position: (${el.x}, ${el.y}) Size: ${el.width}x${el.height}`);
      console.log(`   Display: ${el.display} Visibility: ${el.visibility} Opacity: ${el.opacity}`);
      
      if (el.innerHTML && el.innerHTML.length < 200) {
        console.log(`   HTML: ${el.innerHTML}`);
      }
    });

    // Generate potential selectors
    console.log('\n🔧 POTENTIAL UPLOAD SELECTORS:');
    console.log('=' .repeat(60));
    
    const uploadCandidates = visibleElements.filter(el => {
      const text = el.textContent.toLowerCase();
      const aria = el.ariaLabel.toLowerCase();
      const title = el.title.toLowerCase();
      const className = el.className.toLowerCase();
      const id = el.id.toLowerCase();
      
      return text.includes('upload') || text.includes('add') || text.includes('import') ||
             aria.includes('upload') || aria.includes('add') || aria.includes('import') ||
             title.includes('upload') || title.includes('add') || title.includes('import') ||
             className.includes('upload') || className.includes('add') || className.includes('import') ||
             id.includes('upload') || id.includes('add') || id.includes('import');
    });

    if (uploadCandidates.length > 0) {
      console.log('\n🎯 LIKELY UPLOAD CANDIDATES:');
      uploadCandidates.forEach((el, i) => {
        console.log(`\n${i + 1}. ${el.tagName}${el.id ? '#' + el.id : ''}${el.className ? '.' + el.className.split(' ').join('.') : ''}`);
        console.log(`   Text: "${el.textContent}"`);
        console.log(`   Aria: "${el.ariaLabel}"`);
        console.log(`   Suggested Selector: ${generateSelector(el)}`);
      });
    } else {
      console.log('\n❌ No obvious upload candidates found.');
      console.log('💡 Look for:');
      console.log('   - Plus (+) buttons');
      console.log('   - Cloud upload icons');
      console.log('   - Generic buttons without specific text');
      console.log('   - Hidden file inputs');
      console.log('   - Drag-and-drop areas');
    }

    // Save detailed analysis to file
    const analysisFile = 'windows_icloud_analysis.json';
    await fs.writeJson(analysisFile, pageAnalysis, { spaces: 2 });
    console.log(`\n💾 Detailed analysis saved to: ${analysisFile}`);

    console.log('\n🎯 MANUAL INSPECTION INSTRUCTIONS:');
    console.log('1. Look at the browser window that opened');
    console.log('2. Try to find the upload button manually');
    console.log('3. Right-click on potential upload buttons and select "Inspect Element"');
    console.log('4. Look for elements with classes or attributes related to upload/add/import');
    console.log('5. Check if there are any hidden file input elements');
    console.log('6. Look for drag-and-drop areas');
    
    console.log('\n🔧 TESTING FILE CHOOSER:');
    console.log('Try clicking on different elements in the browser to see if any open a file chooser.');
    console.log('If you find one that works, note its details above.');
    
    console.log('\n⏹️  Press Enter to close the browser and exit...');
    
    // Keep the browser open for manual inspection
    await new Promise(resolve => {
      process.stdin.once('data', () => {
        resolve();
      });
    });
    
  } catch (error) {
    console.error('❌ Error during analysis:', error);
  } finally {
    console.log('🔄 Closing browser...');
    await browser.close();
  }
}

function generateSelector(element) {
  if (element.id) {
    return `#${element.id}`;
  }
  
  if (element.dataTestId) {
    return `[data-testid="${element.dataTestId}"]`;
  }
  
  if (element.className) {
    const classes = element.className.split(' ').filter(c => c.length > 0);
    if (classes.length > 0) {
      return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
    }
  }
  
  if (element.ariaLabel) {
    return `${element.tagName.toLowerCase()}[aria-label="${element.ariaLabel}"]`;
  }
  
  if (element.title) {
    return `${element.tagName.toLowerCase()}[title="${element.title}"]`;
  }
  
  return `${element.tagName.toLowerCase()}:nth-child(${element.index + 1})`;
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n👋 Closing browser and exiting...');
  process.exit(0);
});

findUploadButtonOnWindows().catch(console.error);
