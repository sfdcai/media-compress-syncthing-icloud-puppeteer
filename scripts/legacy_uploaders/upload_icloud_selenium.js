#!/usr/bin/env node
/**
 * iCloud Photos Upload Script using Selenium WebDriver
 * More reliable than Puppeteer for complex web applications
 */

const { Builder, By, until, Key } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');
const fs = require('fs-extra');
const path = require('path');

class ICloudUploaderSelenium {
    constructor() {
        this.driver = null;
        this.uploadedFiles = [];
        this.failedFiles = [];
    }

    async init() {
        console.log('🚀 Initializing iCloud uploader with Selenium...');
        
        const options = new chrome.Options();
        options.addArguments('--no-sandbox');
        options.addArguments('--disable-setuid-sandbox');
        options.addArguments('--disable-dev-shm-usage');
        options.addArguments('--disable-gpu');
        options.addArguments('--headless');
        options.addArguments('--window-size=1920,1080');
        
        this.driver = await new Builder()
            .forBrowser('chrome')
            .setChromeOptions(options)
            .build();
        
        console.log('✅ Selenium WebDriver initialized');
    }

    async login() {
        console.log('🔐 Navigating to iCloud Photos...');
        
        try {
            await this.driver.get('https://www.icloud.com/photos');
            await this.driver.wait(until.titleContains('Photos'), 30000);
            
            // Wait for page to load
            await this.driver.sleep(5000);
            
            // Check if we need to login
            try {
                const loginButton = await this.driver.findElement(By.css('input[type="email"], input[name="appleId"]'));
                if (loginButton) {
                    console.log('⚠️  Login required. Please log in manually...');
                    console.log('📝 Waiting for manual login completion...');
                    
                    // Wait for login to complete (photos interface to load)
                    await this.driver.wait(until.elementLocated(By.css('[data-testid="photos-app"], .photos-app, [aria-label*="Photos"], main')), 300000);
                    
                    console.log('✅ Login completed');
                } else {
                    console.log('✅ Already logged in');
                }
            } catch (e) {
                console.log('✅ Already logged in or no login required');
            }

            // Wait a bit more for the interface to stabilize
            await this.driver.sleep(3000);
            return true;
        } catch (error) {
            console.error('❌ Login failed:', error.message);
            return false;
        }
    }

    async uploadFile(filePath) {
        const fileName = path.basename(filePath);
        console.log(`📁 Uploading file: ${fileName}`);
        
        try {
            // Method 1: Look for file input directly
            try {
                const fileInput = await this.driver.findElement(By.css('input[type="file"]'));
                if (fileInput) {
                    console.log('📎 Found file input, uploading directly...');
                    await fileInput.sendKeys(filePath);
                    await this.driver.sleep(10000);
                    return true;
                }
            } catch (e) {
                // File input not found, try other methods
            }

            // Method 2: Look for upload button and click it
            const uploadSelectors = [
                '[data-testid="photos-upload"]',
                'button:contains("Upload")',
                'button:contains("Add")',
                'button:contains("Import")',
                'button:contains("+")',
                '[role="button"]'
            ];

            for (const selector of uploadSelectors) {
                try {
                    const element = await this.driver.findElement(By.css(selector));
                    if (element) {
                        console.log(`🔍 Found upload area: ${selector}, clicking...`);
                        await element.click();
                        await this.driver.sleep(3000);
                        
                        // Check if file input appeared
                        try {
                            const fileInputAfterClick = await this.driver.findElement(By.css('input[type="file"]'));
                            if (fileInputAfterClick) {
                                console.log('📎 File input appeared after click, uploading...');
                                await fileInputAfterClick.sendKeys(filePath);
                                await this.driver.sleep(15000);
                                return true;
                            }
                        } catch (e) {
                            // File input didn't appear
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }

            // Method 3: Try keyboard shortcut (Ctrl+U)
            console.log('⌨️  Trying keyboard shortcut approach...');
            const body = await this.driver.findElement(By.tagName('body'));
            await body.sendKeys(Key.CONTROL + 'u');
            await this.driver.sleep(2000);
            
            try {
                const fileInput = await this.driver.findElement(By.css('input[type="file"]'));
                if (fileInput) {
                    console.log('📎 File input appeared with keyboard shortcut, uploading...');
                    await fileInput.sendKeys(filePath);
                    await this.driver.sleep(15000);
                    return true;
                }
            } catch (e) {
                // File input didn't appear
            }

            console.log('❌ No upload method worked');
            return false;

        } catch (error) {
            console.error(`❌ Error uploading ${fileName}:`, error.message);
            return false;
        }
    }

    async uploadFiles(filePaths) {
        console.log(`📤 Starting upload of ${filePaths.length} files...`);
        
        for (let i = 0; i < filePaths.length; i++) {
            const filePath = filePaths[i];
            const fileName = path.basename(filePath);
            
            console.log(`\n📁 Uploading file ${i + 1}/${filePaths.length}: ${fileName}`);
            
            if (await this.uploadFile(filePath)) {
                console.log(`✅ Successfully uploaded: ${fileName}`);
                this.uploadedFiles.push(filePath);
            } else {
                console.log(`❌ Failed to upload: ${fileName}`);
                this.failedFiles.push(filePath);
            }
        }
    }

    async close() {
        if (this.driver) {
            await this.driver.quit();
            console.log('🔒 Browser closed');
        }
    }

    printSummary() {
        console.log('\n📊 Upload Summary:');
        console.log(`✅ Successful: ${this.uploadedFiles.length}`);
        console.log(`❌ Failed: ${this.failedFiles.length}`);
        
        if (this.failedFiles.length > 0) {
            console.log('\n⚠️  Failed files:');
            this.failedFiles.forEach(file => console.log(`   - ${path.basename(file)}`));
        }
    }
}

async function main() {
    const args = process.argv.slice(2);
    const dirArg = args.indexOf('--dir');
    const directory = dirArg !== -1 ? args[dirArg + 1] : './test_files';
    
    if (!fs.existsSync(directory)) {
        console.error(`❌ Directory not found: ${directory}`);
        process.exit(1);
    }
    
    // Get all media files
    const files = fs.readdirSync(directory)
        .filter(file => /\.(jpg|jpeg|png|heic|heif|mp4|mov|avi)$/i.test(file))
        .map(file => path.join(directory, file));
    
    if (files.length === 0) {
        console.log('ℹ️  No media files found to upload');
        return;
    }
    
    console.log(`📁 Found ${files.length} media files to upload`);
    
    const uploader = new ICloudUploaderSelenium();
    
    try {
        await uploader.init();
        
        if (await uploader.login()) {
            await uploader.uploadFiles(files);
        } else {
            console.error('❌ Failed to login to iCloud');
        }
    } catch (error) {
        console.error('❌ Upload process failed:', error.message);
    } finally {
        await uploader.close();
        uploader.printSummary();
    }
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = ICloudUploaderSelenium;