#!/usr/bin/env node
/**
 * Improved iCloud Photos Upload Script using Puppeteer
 * Properly mimics web browser behavior for uploading to iCloud Photos
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const ICLOUD_URL = 'https://www.icloud.com/photos';
const UPLOAD_TIMEOUT = 300000; // 5 minutes per file
const MAX_RETRIES = 3;

class ICloudUploader {
    constructor() {
        this.browser = null;
        this.page = null;
        this.uploadedFiles = [];
        this.failedFiles = [];
    }

    async init() {
        console.log('🚀 Initializing iCloud uploader...');
        
        this.browser = await puppeteer.launch({
            headless: true, // Run headless for server environment
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
                '--single-process',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        });

        this.page = await this.browser.newPage();
        
        // Set user agent
        await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Set viewport
        await this.page.setViewport({ width: 1920, height: 1080 });
        
        console.log('✅ Browser initialized');
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
            
            // Check if we need to login
            const loginButton = await this.page.$('input[type="email"], input[name="appleId"]');
            if (loginButton) {
                console.log('⚠️  Login required. Please log in manually...');
                console.log('📝 Waiting for manual login completion...');
                
                // Wait for login to complete (photos interface to load)
                await this.page.waitForFunction(() => {
                    return document.querySelector('[data-testid="photos-app"]') || 
                           document.querySelector('.photos-app') ||
                           document.querySelector('[aria-label*="Photos"]') ||
                           document.querySelector('main') ||
                           document.querySelector('.main-content');
                }, { timeout: 300000 }); // 5 minutes for manual login
                
                console.log('✅ Login completed');
            } else {
                console.log('✅ Already logged in');
            }

            // Wait a bit more for the interface to stabilize
            await new Promise(resolve => setTimeout(resolve, 3000));

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
            const fileInput = await this.page.$('input[type="file"]');
            if (fileInput) {
                console.log('📎 Found file input, uploading...');
                await fileInput.uploadFile(filePath);
                
                // Wait for upload to complete
                await new Promise(resolve => setTimeout(resolve, 15000));
                
                // Check for success indicators
                const successIndicators = [
                    '[data-testid="upload-success"]',
                    '.upload-success',
                    '[aria-label*="success"]',
                    '.success-message',
                    '.upload-complete'
                ];

                let uploadSuccess = false;
                for (const selector of successIndicators) {
                    const element = await this.page.$(selector);
                    if (element) {
                        uploadSuccess = true;
                        break;
                    }
                }

                // If no success indicator, check for errors
                if (!uploadSuccess) {
                    const errorElements = await this.page.$$('[data-testid*="error"], .error, [aria-label*="error"], .upload-error');
                    uploadSuccess = errorElements.length === 0;
                }

                return uploadSuccess;
            }

            // Method 2: Try to trigger file dialog with keyboard shortcut
            console.log('⌨️  Trying keyboard shortcut approach...');
            await this.page.keyboard.down('Control');
            await this.page.keyboard.press('KeyO');
            await this.page.keyboard.up('Control');
            
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // Check if file input appeared
            const fileInputAfterShortcut = await this.page.$('input[type="file"]');
            if (fileInputAfterShortcut) {
                console.log('📎 File input appeared after shortcut, uploading...');
                await fileInputAfterShortcut.uploadFile(filePath);
                await new Promise(resolve => setTimeout(resolve, 15000));
                return true;
            }

            // Method 3: Try clicking on upload areas
            console.log('🔍 Looking for upload areas to click...');
            const uploadAreas = [
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
                '[role="button"]'
            ];

            for (const selector of uploadAreas) {
                try {
                    const element = await this.page.$(selector);
                    if (element) {
                        console.log(`🔍 Found upload area: ${selector}, clicking...`);
                        await element.click();
                        await new Promise(resolve => setTimeout(resolve, 3000));
                        
                        // Check if file input appeared
                        const fileInputAfterClick = await this.page.$('input[type="file"]');
                        if (fileInputAfterClick) {
                            console.log('📎 File input appeared after click, uploading...');
                            await fileInputAfterClick.uploadFile(filePath);
                            await new Promise(resolve => setTimeout(resolve, 15000));
                            return true;
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }

            // Method 4: Try drag and drop on photos area
            console.log('🖱️  Trying drag and drop approach...');
            
            // Look for photos container or main content area
            const dropTargets = [
                '[data-testid="photos-app"]',
                '.photos-app',
                '[aria-label*="Photos"]',
                'main',
                '.main-content',
                'body'
            ];

            let dropTarget = null;
            for (const selector of dropTargets) {
                dropTarget = await this.page.$(selector);
                if (dropTarget) break;
            }

            if (dropTarget) {
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
                }, fileContent, fileName, dropTargets.find(selector => dropTarget));
                
                if (dropSuccess) {
                    await new Promise(resolve => setTimeout(resolve, 15000));
                    return true;
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
        if (this.browser) {
            await this.browser.close();
            console.log('🔒 Browser closed');
        }
    }
}

// Command line interface
async function main() {
    const args = process.argv.slice(2);
    let uploadDir = null;
    let interactive = false;

    // Parse arguments
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--dir' && i + 1 < args.length) {
            uploadDir = args[i + 1];
            i++;
        } else if (args[i] === '--interactive') {
            interactive = true;
        } else if (args[i] === '--help') {
            console.log(`
Improved iCloud Photos Upload Script

Usage: node upload_icloud_improved.js [options]

Options:
  --dir <path>      Directory containing files to upload
  --interactive     Enable interactive mode (manual login)
  --help           Show this help message

Examples:
  node upload_icloud_improved.js --dir /path/to/files
  node upload_icloud_improved.js --dir /path/to/files --interactive
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

    const uploader = new ICloudUploader();
    
    try {
        await uploader.init();
        
        if (interactive) {
            console.log('👤 Interactive mode enabled - manual login required');
        }
        
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

export default ICloudUploader;