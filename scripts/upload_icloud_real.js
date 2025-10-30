#!/usr/bin/env node
/**
 * Real iCloud Photos Upload Script with 2FA Support
 * Uses virtual display for server environments
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const ICLOUD_URL = 'https://www.icloud.com/photos';
const UPLOAD_TIMEOUT = 300000; // 5 minutes per file
const WAIT_TIMEOUT = 30000; // 30 seconds for user input

class RealICloudUploader {
    constructor() {
        this.browser = null;
        this.page = null;
        this.uploadedFiles = [];
        this.failedFiles = [];
        this.rl = null;
    }

    async init() {
        console.log('🚀 Initializing real iCloud uploader with virtual display...');
        
        this.browser = await puppeteer.launch({
            headless: false, // We'll use virtual display
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
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        });

        this.page = await this.browser.newPage();
        
        // Set user agent
        await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Set viewport
        await this.page.setViewport({ width: 1920, height: 1080 });
        
        // Set up readline for user input
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        console.log('✅ Browser initialized with virtual display');
    }

    async waitForUserInput(prompt) {
        return new Promise((resolve) => {
            this.rl.question(prompt, (answer) => {
                resolve(answer.trim());
            });
        });
    }

    async login() {
        console.log('🔐 Navigating to iCloud Photos...');
        
        try {
            await this.page.goto(ICLOUD_URL, { 
                waitUntil: 'networkidle2',
                timeout: 30000 
            });

            // Wait for page to load
            await this.page.waitForSelector('body', { timeout: 10000 });
            
            console.log('📱 Browser opened. Checking login status...');
            
            // Wait a moment for any redirects or login prompts
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // Check if we're on login page or photos page
            const currentUrl = this.page.url();
            console.log(`📍 Current URL: ${currentUrl}`);
            
            if (currentUrl.includes('signin') || currentUrl.includes('login')) {
                console.log('🔑 Login required. Please log in manually...');
                console.log('💡 Once logged in, press Enter to continue...');
                
                await this.waitForUserInput('Press Enter when logged in...');
                
                // Wait for potential 2FA
                console.log('🔍 Checking for 2FA prompt...');
                await new Promise(resolve => setTimeout(resolve, 3000));
                
                // Check for 2FA input field
                const twoFactorInput = await this.page.$('input[type="text"][placeholder*="code"], input[type="text"][placeholder*="Code"], input[type="text"][placeholder*="verification"], input[type="text"][placeholder*="Verification"]');
                
                if (twoFactorInput) {
                    console.log('📱 2FA code required!');
                    const code = await this.waitForUserInput('Enter 2FA code: ');
                    
                    if (code) {
                        console.log('🔢 Entering 2FA code...');
                        await twoFactorInput.click();
                        await twoFactorInput.type(code);
                        
                        // Look for submit button
                        const submitButton = await this.page.$('button[type="submit"], input[type="submit"], button:contains("Continue"), button:contains("Verify")');
                        if (submitButton) {
                            await submitButton.click();
                            console.log('✅ 2FA code submitted');
                        }
                        
                        // Wait for navigation
                        await new Promise(resolve => setTimeout(resolve, 5000));
                    }
                }
            }
            
            // Wait for photos interface to be ready
            console.log('🔍 Checking if photos interface is ready...');
            await this.page.waitForFunction(() => {
                return document.querySelector('[data-testid="photos-app"]') || 
                       document.querySelector('.photos-app') ||
                       document.querySelector('[aria-label*="Photos"]') ||
                       document.querySelector('main') ||
                       document.querySelector('.main-content') ||
                       document.querySelector('body');
            }, { timeout: 15000 });
            
            console.log('✅ Photos interface ready');
            
            // Take a screenshot for debugging
            await this.page.screenshot({ path: '/tmp/icloud_photos_logged_in.png' });
            console.log('📸 Screenshot saved to /tmp/icloud_photos_logged_in.png');

            return true;
        } catch (error) {
            console.error('❌ Login failed:', error.message);
            return false;
        }
    }

    async uploadFiles(files) {
        console.log(`📤 Starting upload of ${files.length} files...`);
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            console.log(`\n📁 Uploading file ${i + 1}/${files.length}: ${path.basename(file)}`);
            
            try {
                const success = await this.uploadSingleFile(file);
                if (success) {
                    this.uploadedFiles.push(file);
                    console.log(`✅ Uploaded: ${path.basename(file)}`);
                } else {
                    this.failedFiles.push(file);
                    console.log(`❌ Failed: ${path.basename(file)}`);
                }
            } catch (error) {
                this.failedFiles.push(file);
                console.error(`❌ Error uploading ${path.basename(file)}:`, error.message);
            }
        }
        
        console.log(`\n📊 Upload Summary:`);
        console.log(`✅ Successful: ${this.uploadedFiles.length}`);
        console.log(`❌ Failed: ${this.failedFiles.length}`);
    }

    async uploadSingleFile(filePath) {
        try {
            // Check if file exists
            if (!await fs.pathExists(filePath)) {
                throw new Error(`File not found: ${filePath}`);
            }

            console.log(`📎 Attempting to upload: ${path.basename(filePath)}`);

            // Method 1: Look for file input element
            console.log('🔍 Looking for file input elements...');
            const fileInputs = await this.page.$$('input[type="file"]');
            console.log(`Found ${fileInputs.length} file input elements`);
            
            if (fileInputs.length > 0) {
                console.log('📎 Found file input, uploading...');
                await fileInputs[0].uploadFile(filePath);
                
                // Wait for upload to complete
                console.log('⏳ Waiting for upload to complete...');
                await new Promise(resolve => setTimeout(resolve, 20000));
                
                // Take screenshot after upload attempt
                await this.page.screenshot({ path: '/tmp/icloud_after_upload.png' });
                console.log('📸 Screenshot saved to /tmp/icloud_after_upload.png');
                
                return true;
            }

            // Method 2: Try keyboard shortcut
            console.log('⌨️  Trying keyboard shortcut Ctrl+O...');
            await this.page.keyboard.down('Control');
            await this.page.keyboard.press('KeyO');
            await this.page.keyboard.up('Control');
            
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // Check if file input appeared
            const fileInputsAfterShortcut = await this.page.$$('input[type="file"]');
            console.log(`Found ${fileInputsAfterShortcut.length} file inputs after shortcut`);
            
            if (fileInputsAfterShortcut.length > 0) {
                console.log('📎 File input appeared after shortcut, uploading...');
                await fileInputsAfterShortcut[0].uploadFile(filePath);
                await new Promise(resolve => setTimeout(resolve, 20000));
                
                await this.page.screenshot({ path: '/tmp/icloud_after_shortcut_upload.png' });
                console.log('📸 Screenshot saved to /tmp/icloud_after_shortcut_upload.png');
                
                return true;
            }

            // Method 3: Try clicking on various elements
            console.log('🔍 Looking for clickable upload elements...');
            const clickableSelectors = [
                '[data-testid="upload-button"]',
                '[aria-label*="Upload"]',
                'button[title*="Upload"]',
                '.upload-button',
                '.upload-area',
                '[data-testid="photos-upload"]',
                'button:contains("Upload")',
                'button:contains("Add")',
                'button:contains("Import")',
                'button:contains("+")',
                '[role="button"]',
                'button'
            ];

            for (const selector of clickableSelectors) {
                try {
                    const elements = await this.page.$$(selector);
                    console.log(`Found ${elements.length} elements matching: ${selector}`);
                    
                    if (elements.length > 0) {
                        console.log(`🔍 Clicking element: ${selector}`);
                        await elements[0].click();
                        await new Promise(resolve => setTimeout(resolve, 3000));
                        
                        // Check if file input appeared
                        const fileInputsAfterClick = await this.page.$$('input[type="file"]');
                        console.log(`Found ${fileInputsAfterClick.length} file inputs after click`);
                        
                        if (fileInputsAfterClick.length > 0) {
                            console.log('📎 File input appeared after click, uploading...');
                            await fileInputsAfterClick[0].uploadFile(filePath);
                            await new Promise(resolve => setTimeout(resolve, 20000));
                            
                            await this.page.screenshot({ path: '/tmp/icloud_after_click_upload.png' });
                            console.log('📸 Screenshot saved to /tmp/icloud_after_click_upload.png');
                            
                            return true;
                        }
                    }
                } catch (e) {
                    console.log(`Error with selector ${selector}: ${e.message}`);
                }
            }

            // Method 4: Try drag and drop
            console.log('🖱️  Trying drag and drop approach...');
            
            const dropTargets = [
                '[data-testid="photos-app"]',
                '.photos-app',
                '[aria-label*="Photos"]',
                'main',
                '.main-content',
                'body'
            ];

            for (const selector of dropTargets) {
                const element = await this.page.$(selector);
                if (element) {
                    console.log(`🖱️  Trying drag and drop on: ${selector}`);
                    
                    // Read file content
                    const fileContent = await fs.readFile(filePath);
                    const fileName = path.basename(filePath);
                    
                    // Create file object and trigger drop event
                    const dropSuccess = await this.page.evaluate(async (fileContent, fileName, targetSelector) => {
                        const target = document.querySelector(targetSelector);
                        if (!target) return false;
                        
                        try {
                            // Create file object
                            const file = new File([fileContent], fileName, { type: 'image/jpeg' });
                            
                            // Create drag and drop event
                            const dragEvent = new DragEvent('dragover', {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: new DataTransfer()
                            });
                            
                            const dropEvent = new DragEvent('drop', {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: new DataTransfer()
                            });
                            
                            // Add file to data transfer
                            dropEvent.dataTransfer.items.add(file);
                            
                            // Dispatch events
                            target.dispatchEvent(dragEvent);
                            await new Promise(resolve => setTimeout(resolve, 100));
                            target.dispatchEvent(dropEvent);
                            
                            return true;
                        } catch (e) {
                            console.error('Drop event error:', e);
                            return false;
                        }
                    }, fileContent, fileName, selector);
                    
                    if (dropSuccess) {
                        await new Promise(resolve => setTimeout(resolve, 20000));
                        
                        await this.page.screenshot({ path: '/tmp/icloud_after_drop_upload.png' });
                        console.log('📸 Screenshot saved to /tmp/icloud_after_drop_upload.png');
                        
                        return true;
                    }
                }
            }

            console.log('❌ No upload method worked');
            return false;

        } catch (error) {
            console.error(`❌ Upload error: ${error.message}`);
            return false;
        }
    }

    async close() {
        if (this.rl) {
            this.rl.close();
        }
        if (this.browser) {
            console.log('🔒 Closing browser in 5 seconds...');
            await new Promise(resolve => setTimeout(resolve, 5000));
            await this.browser.close();
            console.log('🔒 Browser closed');
        }
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);
    let uploadDir = null;

    // Parse arguments
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--dir' && i + 1 < args.length) {
            uploadDir = args[i + 1];
            i++;
        } else if (args[i] === '--help') {
            console.log(`
Real iCloud Photos Upload Script with 2FA Support

Usage: node upload_icloud_real.js [options]

Options:
  --dir <path>      Directory containing files to upload
  --help           Show this help message

Examples:
  node upload_icloud_real.js --dir /path/to/files
            `);
            process.exit(0);
        }
    }

    if (!uploadDir) {
        console.error('❌ Error: --dir parameter is required');
        console.log('Use --help for usage information');
        process.exit(1);
    }

    // Check if directory exists
    if (!await fs.pathExists(uploadDir)) {
        console.error(`❌ Error: Directory not found: ${uploadDir}`);
        process.exit(1);
    }

    // Get files to upload
    const files = await fs.readdir(uploadDir);
    const mediaFiles = files.filter(file => {
        const ext = path.extname(file).toLowerCase();
        return ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'].includes(ext);
    }).map(file => path.join(uploadDir, file));

    if (mediaFiles.length === 0) {
        console.log('ℹ️  No media files found to upload');
        process.exit(0);
    }

    console.log(`📁 Found ${mediaFiles.length} media files to upload`);

    const uploader = new RealICloudUploader();
    
    try {
        await uploader.init();
        
        const loginSuccess = await uploader.login();
        if (!loginSuccess) {
            throw new Error('Login failed');
        }

        await uploader.uploadFiles(mediaFiles);
        
        // Exit with appropriate code
        if (uploader.failedFiles.length > 0) {
            console.log(`\n⚠️  Some uploads failed. Check the logs above.`);
            process.exit(1);
        } else {
            console.log(`\n🎉 All uploads completed successfully!`);
            process.exit(0);
        }
        
    } catch (error) {
        console.error('❌ Fatal error:', error.message);
        process.exit(1);
    } finally {
        await uploader.close();
    }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}

export default RealICloudUploader;