/**
 * Manual Selector Testing Script
 * This script helps you find the correct selectors for iCloud Photos
 */

import puppeteer from 'puppeteer';
import fs from 'fs';

const ICLOUD_PHOTOS_URL = 'https://www.icloud.com/photos/';

async function testSelectors() {
  console.log('Starting manual selector testing...');
  
  const browser = await puppeteer.launch({
    headless: false, // Set to true if you want headless mode
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  page.setDefaultNavigationTimeout(120000);
  
  try {
    console.log('Navigating to iCloud Photos...');
    await page.goto(ICLOUD_PHOTOS_URL);
    
    console.log('Waiting for page to load...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    console.log('Looking for upload-related elements...');
    
    // Test various selectors
    const selectors = [
      'button[aria-label*="Upload"]',
      'button[title*="Upload"]',
      'button[aria-label*="Add"]',
      'button[title*="Add"]',
      'button[aria-label*="Import"]',
      'button[title*="Import"]',
      'button[aria-label*="Photos"]',
      'button[title*="Photos"]',
      'button[aria-label*="Library"]',
      'button[title*="Library"]',
      'input[type="file"]',
      'button[data-testid*="upload"]',
      'button[data-testid*="add"]',
      'button[data-testid*="import"]'
    ];
    
    const foundSelectors = [];
    
    for (const selector of selectors) {
      try {
        const elements = await page.$$(selector);
        if (elements.length > 0) {
          console.log(`✓ Found ${elements.length} element(s) with selector: ${selector}`);
          foundSelectors.push(selector);
          
          // Get element details
          for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            const text = await element.evaluate(el => el.textContent);
            const ariaLabel = await element.evaluate(el => el.getAttribute('aria-label'));
            const title = await element.evaluate(el => el.getAttribute('title'));
            const dataTestId = await element.evaluate(el => el.getAttribute('data-testid'));
            
            console.log(`  Element ${i + 1}:`);
            console.log(`    Text: "${text}"`);
            console.log(`    aria-label: "${ariaLabel}"`);
            console.log(`    title: "${title}"`);
            console.log(`    data-testid: "${dataTestId}"`);
          }
        }
      } catch (error) {
        console.log(`✗ Error testing selector ${selector}: ${error.message}`);
      }
    }
    
    console.log('\n=== SUMMARY ===');
    console.log(`Found ${foundSelectors.length} working selectors:`);
    foundSelectors.forEach(selector => console.log(`  - ${selector}`));
    
    // Save results to file
    const results = {
      timestamp: new Date().toISOString(),
      workingSelectors: foundSelectors,
      allTestedSelectors: selectors
    };
    
    fs.writeFileSync('selector_test_results.json', JSON.stringify(results, null, 2));
    console.log('\nResults saved to selector_test_results.json');
    
  } catch (error) {
    console.error('Error during testing:', error);
  } finally {
    console.log('\nPress Ctrl+C to close the browser and exit...');
    // Keep browser open for manual inspection
    // await browser.close();
  }
}

testSelectors().catch(console.error);
