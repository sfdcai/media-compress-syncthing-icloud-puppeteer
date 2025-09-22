/**
 * Clear Cookies and Force Fresh Login
 * 
 * This script clears old cookies and forces a fresh login to iCloud.
 * 
 * Usage: node scripts/clear_cookies_and_login.js
 */

import fs from 'fs-extra';
import path from 'path';

const COOKIE_FILE = path.resolve('./cookies.json');

async function clearCookiesAndLogin() {
  console.log('🧹 Clearing old cookies and forcing fresh login...');
  
  // Remove old cookies
  if (await fs.pathExists(COOKIE_FILE)) {
    await fs.remove(COOKIE_FILE);
    console.log('✅ Removed old cookies file');
  } else {
    console.log('ℹ️  No cookies file found');
  }
  
  console.log('');
  console.log('🔄 Now run the main upload script with --interactive:');
  console.log('   node scripts/upload_icloud.js --dir /tmp/test_upload --interactive');
  console.log('');
  console.log('💡 This will:');
  console.log('   1. Open a visible browser (if display available)');
  console.log('   2. Navigate to iCloud Photos');
  console.log('   3. Wait for you to complete login and 2FA');
  console.log('   4. Save fresh cookies for future use');
  console.log('');
  console.log('⚠️  If you get "Missing X server" error, you need to:');
  console.log('   - Use X11 forwarding: ssh -X user@server');
  console.log('   - Or run on a machine with a display');
  console.log('   - Or use VNC/remote desktop');
}

clearCookiesAndLogin().catch(console.error);
