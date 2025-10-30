#!/usr/bin/env node
/**
 * iCloud Photos Upload Script using Puppeteer
 * Automates file uploads to iCloud Photos web interface
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
                '--single-process'
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

            // Wait for login or photos interface
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
                           document.querySelector('[aria-label*="Photos"]');
                }, { timeout: 300000 }); // 5 minutes for manual login
                
                console.log('✅ Login completed');
            } else {
                console.log('✅ Already logged in');
            }

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

            // Look for upload button or drag-drop area
            const uploadSelectors = [
                '[data-testid="upload-button"]',
                '[aria-label*="Upload"]',
                'button[title*="Upload"]',
                '.upload-button',
                '.upload-area',
                '[data-testid="photos-upload"]'
            ];

            let uploadElement = null;
            for (const selector of uploadSelectors) {
                uploadElement = await this.page.$(selector);
                if (uploadElement) break;
            }

            if (!uploadElement) {
                // Try to find any clickable element that might trigger upload
                uploadElement = await this.page.$('button, [role="button"]');
                if (uploadElement) {
                    console.log('🔍 Found potential upload trigger, clicking...');
                    await uploadElement.click();
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
            }

            // Look for file input
            const fileInput = await this.page.$('input[type="file"]');
            if (fileInput) {
                console.log('📎 Found file input, uploading...');
                await fileInput.uploadFile(filePath);
                
                // Wait for upload to complete
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                // Look for success indicators
                const successIndicators = [
                    '[data-testid="upload-success"]',
                    '.upload-success',
                    '[aria-label*="success"]',
                    '.success-message'
                ];

                let uploadSuccess = false;
                for (const selector of successIndicators) {
                    const element = await this.page.$(selector);
                    if (element) {
                        uploadSuccess = true;
                        break;
                    }
                }

                // If no success indicator, assume success if no error
                if (!uploadSuccess) {
                    const errorElements = await this.page.$$('[data-testid*="error"], .error, [aria-label*="error"]');
                    uploadSuccess = errorElements.length === 0;
                }

                return uploadSuccess;
            } else {
                // Try drag and drop approach
                console.log('🖱️  Trying drag and drop approach...');
                
                const fileContent = await fs.readFile(filePath);
                const fileName = path.basename(filePath);
                
                // Create a data transfer object
                const dataTransfer = await this.page.evaluateHandle((fileContent, fileName) => {
                    const dt = new DataTransfer();
                    const file = new File([fileContent], fileName);
                    dt.items.add(file);
                    return dt;
                }, fileContent, fileName);

                // Find drop zone
                const dropZone = await this.page.$('body'); // Use body as fallback
                if (dropZone) {
                    await dropZone.dispatchEvent('drop', { dataTransfer });
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    return true;
                }
            }

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
iCloud Photos Upload Script

Usage: node upload_icloud.js [options]

Options:
  --dir <path>      Directory containing files to upload
  --interactive     Enable interactive mode (manual login)
  --help           Show this help message

Examples:
  node upload_icloud.js --dir /path/to/files
  node upload_icloud.js --dir /path/to/files --interactive
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