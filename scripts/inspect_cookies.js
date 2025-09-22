/**
 * Cookie Inspector for iCloud Authentication
 * 
 * This script helps you understand what cookies are saved
 * and whether you're actually logged in to iCloud.
 * 
 * Usage: node scripts/inspect_cookies.js
 */

import fs from 'fs-extra';
import path from 'path';

const COOKIE_FILE = path.resolve('./cookies.json');

async function inspectCookies() {
  console.log('🍪 iCloud Cookie Inspector');
  console.log('=' .repeat(50));
  
  if (!await fs.pathExists(COOKIE_FILE)) {
    console.log('❌ No cookies file found at:', COOKIE_FILE);
    console.log('   This means you need to run the script with --interactive first.');
    return;
  }
  
  try {
    const cookies = await fs.readJson(COOKIE_FILE);
    console.log(`✅ Found ${cookies.length} cookies`);
    
    // Group cookies by domain
    const cookiesByDomain = {};
    cookies.forEach(cookie => {
      if (!cookiesByDomain[cookie.domain]) {
        cookiesByDomain[cookie.domain] = [];
      }
      cookiesByDomain[cookie.domain].push(cookie);
    });
    
    console.log('\n📊 Cookies by domain:');
    Object.keys(cookiesByDomain).forEach(domain => {
      console.log(`\n🌐 ${domain}:`);
      cookiesByDomain[domain].forEach(cookie => {
        const expires = cookie.expires ? new Date(cookie.expires * 1000).toISOString() : 'Session';
        const secure = cookie.secure ? '🔒' : '🔓';
        const httpOnly = cookie.httpOnly ? '🚫' : '✅';
        
        console.log(`   ${secure}${httpOnly} ${cookie.name}: ${cookie.value.substring(0, 20)}... (expires: ${expires})`);
      });
    });
    
    // Check for important iCloud cookies
    const importantCookies = cookies.filter(cookie => 
      cookie.name.includes('session') || 
      cookie.name.includes('auth') || 
      cookie.name.includes('token') ||
      cookie.name.includes('apple') ||
      cookie.name.includes('icloud')
    );
    
    if (importantCookies.length > 0) {
      console.log('\n🔑 Important authentication cookies found:');
      importantCookies.forEach(cookie => {
        const expires = cookie.expires ? new Date(cookie.expires * 1000).toISOString() : 'Session';
        console.log(`   ${cookie.name}: expires ${expires}`);
      });
    }
    
    // Check if cookies are expired
    const now = Date.now() / 1000;
    const expiredCookies = cookies.filter(cookie => 
      cookie.expires && cookie.expires < now
    );
    
    if (expiredCookies.length > 0) {
      console.log(`\n⏰ ${expiredCookies.length} cookies are expired and will be ignored`);
    }
    
    console.log('\n💡 What this means:');
    console.log('   - If you see authentication cookies, you might be logged in');
    console.log('   - If cookies are expired, you need to login again');
    console.log('   - The script uses these cookies to avoid 2FA on subsequent runs');
    console.log('   - If you want to force a fresh login, delete the cookies file');
    
  } catch (error) {
    console.error('❌ Error reading cookies:', error.message);
  }
}

inspectCookies().catch(console.error);
