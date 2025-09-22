/**
 * Headless iCloud Upload Button Debugger
 * 
 * This script runs in headless mode and provides detailed analysis
 * of the iCloud Photos page to help find upload controls.
 * 
 * Usage: node scripts/debug_icloud_headless.js
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

async function debugUploadButtonHeadless() {
  console.log('🔍 Starting Headless iCloud Upload Button Debugger...');
  console.log('This will analyze the page and provide detailed element information.\n');

  const browser = await puppeteer.launch({
    headless: true, // Headless mode for server environments
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
  
  // Set viewport for consistent screenshots
  await page.setViewport({ width: 1920, height: 1080 });
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
    
    // Check if we need to login
    const isLoginPage = currentUrl.includes('appleid.apple.com') || 
                       currentUrl.includes('signin') || 
                       currentUrl.includes('login') ||
                       currentUrl.includes('auth') ||
                       currentUrl.includes('authentication');
    
    if (isLoginPage) {
      console.log('🔐 Login page detected. Cannot proceed in headless mode.');
      console.log('💡 Please run the main script with --interactive first to complete login.');
      return;
    }

    // Wait for page to stabilize
    console.log('⏳ Waiting for page to stabilize...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Take initial screenshot
    await takeScreenshot(page, 'icloud_photos_page.png');

    console.log('\n🔍 Analyzing page structure...');
    
    // Get comprehensive page analysis
    const pageAnalysis = await page.evaluate(() => {
      // Get all possible clickable elements
      const clickableSelectors = [
        'button', 'input[type="button"]', 'input[type="submit"]',
        'div[role="button"]', 'span[role="button"]', 'a[role="button"]',
        '[onclick]', '[class*="button"]', '[class*="btn"]',
        '[class*="upload"]', '[class*="add"]', '[class*="import"]',
        '[class*="plus"]', '[class*="create"]', '[class*="new"]',
        'input[type="file"]', 'label[for]'
      ];
      
      const allElements = [];
      const elementMap = new Map();
      
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
              visible: isVisible,
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              zIndex: computedStyle.zIndex,
              position: computedStyle.position,
              display: computedStyle.display,
              visibility: computedStyle.visibility,
              opacity: computedStyle.opacity
            };
            
            // Create unique key to avoid duplicates
            const key = `${el.tagName}-${el.className}-${el.id}-${index}`;
            if (!elementMap.has(key)) {
              elementMap.set(key, elementInfo);
              allElements.push(elementInfo);
            }
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
      
      if (el.innerHTML && el.innerHTML.length < 100) {
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
      console.log('💡 Try looking for:');
      console.log('   - Plus (+) buttons');
      console.log('   - Generic buttons without specific text');
      console.log('   - Hidden file inputs');
      console.log('   - Drag-and-drop areas');
    }

    // Test file chooser on promising elements
    console.log('\n🧪 TESTING FILE CHOOSER ON PROMISING ELEMENTS:');
    console.log('=' .repeat(60));
    
    const testElements = uploadCandidates.length > 0 ? uploadCandidates.slice(0, 3) : visibleElements.slice(0, 5);
    
    for (let i = 0; i < testElements.length; i++) {
      const el = testElements[i];
      console.log(`\nTesting element ${i + 1}: ${el.tagName} - "${el.textContent}"`);
      
      try {
        const selector = generateSelector(el);
        const element = await page.$(selector);
        
        if (element) {
          console.log(`   Selector: ${selector}`);
          
          // Try to trigger file chooser
          try {
            const [fileChooser] = await Promise.all([
              page.waitForFileChooser({ timeout: 3000 }),
              element.click()
            ]);
            
            console.log('   ✅ FILE CHOOSER OPENED! This is likely the upload button.');
            console.log(`   🎯 Add this selector to your config: "${selector}"`);
            
            // Close the file chooser
            await fileChooser.cancel();
            break;
            
          } catch (e) {
            console.log(`   ❌ No file chooser opened: ${e.message}`);
          }
        } else {
          console.log(`   ❌ Could not find element with selector: ${selector}`);
        }
      } catch (error) {
        console.log(`   ❌ Error testing element: ${error.message}`);
      }
    }

    // Save detailed analysis to file
    const analysisFile = 'icloud_analysis.json';
    await fs.writeJson(analysisFile, pageAnalysis, { spaces: 2 });
    console.log(`\n💾 Detailed analysis saved to: ${analysisFile}`);

  } catch (error) {
    console.error('❌ Error during analysis:', error);
  } finally {
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

debugUploadButtonHeadless().catch(console.error);
