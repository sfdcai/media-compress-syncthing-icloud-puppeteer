/**
 * iCloud Login Helper
 * 
 * This script helps you properly log into iCloud Photos with 2FA support.
 * It will open a visible browser (if possible) or guide you through the process.
 * 
 * Usage: node scripts/login_to_icloud.js
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';

const COOKIE_FILE = path.resolve('./cookies.json');
const ICLOUD_PHOTOS_URL = 'https://www.icloud.com/photos/';

async function saveCookies(page) {
  const cookies = await page.cookies();
  await fs.writeJson(COOKIE_FILE, cookies, { spaces: 2 });
  console.log('✅ Saved cookies to', COOKIE_FILE);
}

async function checkLoginStatus(page) {
  const currentUrl = page.url();
  console.log('📍 Current URL:', currentUrl);
  
  // Check if we're on a login page
  const isLoginPage = currentUrl.includes('appleid.apple.com') || 
                     currentUrl.includes('signin') || 
                     currentUrl.includes('login') ||
                     currentUrl.includes('auth') ||
                     currentUrl.includes('authentication');
  
  if (isLoginPage) {
    console.log('🔐 Login page detected');
    return false;
  }
  
  // Check if we can see the Photos interface
  const hasSignInButton = await page.$('ui-button.sign-in-button') !== null;
  if (hasSignInButton) {
    console.log('🔐 Sign In button detected - not logged in');
    return false;
  }
  
  // Check for Photos interface elements
  const hasPhotosInterface = await page.evaluate(() => {
    // Look for common Photos interface elements
    return document.querySelector('[data-testid*="photo"]') !== null ||
           document.querySelector('.photos-grid') !== null ||
           document.querySelector('.photo-tile') !== null ||
           document.querySelector('[class*="photo"]') !== null;
  });
  
  if (hasPhotosInterface) {
    console.log('✅ Photos interface detected - logged in');
    return true;
  }
  
  console.log('❓ Unknown page state');
  return false;
}

async function loginToICloud() {
  console.log('🔐 iCloud Login Helper');
  console.log('=' .repeat(50));
  
  // Try to detect if we can run in non-headless mode
  const canRunVisible = process.env.DISPLAY || process.env.WAYLAND_DISPLAY;
  
  if (!canRunVisible) {
    console.log('❌ No display available. Cannot run interactive login.');
    console.log('💡 Solutions:');
    console.log('   1. Use X11 forwarding: ssh -X user@server');
    console.log('   2. Use VNC or remote desktop');
    console.log('   3. Run this on a machine with a display');
    console.log('   4. Delete cookies and use the main script with --interactive');
    return;
  }
  
  console.log('🖥️  Display detected. Opening visible browser...');
  
  const browser = await puppeteer.launch({
    headless: false, // Visible browser for login
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
    console.log('🌐 Navigating to iCloud Photos...');
    await page.goto(ICLOUD_PHOTOS_URL, { waitUntil: 'networkidle2', timeout: 120000 });
    
    // Check current login status
    const isLoggedIn = await checkLoginStatus(page);
    
    if (isLoggedIn) {
      console.log('✅ Already logged in! Saving fresh cookies...');
      await saveCookies(page);
      console.log('🎉 Login successful! You can now run the upload script.');
    } else {
      console.log('🔐 Login required. Please complete the following steps:');
      console.log('');
      console.log('1. 📱 Enter your Apple ID and password in the browser window');
      console.log('2. 🔐 Complete 2FA (SMS, authenticator app, or trusted device)');
      console.log('3. ⏳ Wait for the Photos interface to load');
      console.log('4. ✅ Press Enter here when you see the Photos interface');
      console.log('');
      console.log('⏳ Waiting for you to complete login...');
      
      // Wait for user to complete login
      await new Promise(resolve => {
        process.stdin.once('data', () => {
          resolve();
        });
      });
      
      // Check if login was successful
      const loginSuccessful = await checkLoginStatus(page);
      
      if (loginSuccessful) {
        console.log('✅ Login successful! Saving cookies...');
        await saveCookies(page);
        console.log('🎉 You can now run the upload script without --interactive!');
      } else {
        console.log('❌ Login may not have completed successfully.');
        console.log('💡 Please try again or check the browser window.');
      }
    }

  } catch (error) {
    console.error('❌ Error during login:', error);
  } finally {
    console.log('🔄 Closing browser...');
    await browser.close();
  }
}

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('\n👋 Closing browser and exiting...');
  process.exit(0);
});

loginToICloud().catch(console.error);
