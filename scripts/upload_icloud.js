#!/usr/bin/env node
/**
 * Automated iCloud Photos Upload Script using Puppeteer
 * Restores trusted sessions, discovers upload targets, and uploads batches reliably
 */

import puppeteer from 'puppeteer';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const selectorsPath = path.join(__dirname, 'icloud_selectors.json');
let selectorsConfig = {
    uploadButtonSelectors: [],
    pageSelectors: {},
    waitSelectors: {}
};

try {
    selectorsConfig = fs.readJSONSync(selectorsPath);
} catch (error) {
    console.warn(`⚠️  Could not load selector configuration at ${selectorsPath}: ${error.message}`);
}

// Configuration
const ICLOUD_URL = 'https://www.icloud.com/photos';
const UPLOAD_TIMEOUT = 300000; // 5 minutes per file
const MAX_RETRIES = 3;

class ICloudUploader {
    constructor(options = {}) {
        const {
            customUploadSelector = null,
            sessionFile = null,
        } = options;

        this.browser = null;
        this.page = null;
        this.uploadedFiles = [];
        this.failedFiles = [];
        this.customUploadSelector = customUploadSelector;
        this.sessionFile = sessionFile;
        this.sessionReady = false;
        this.selectors = selectorsConfig;
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

        await this._loadSessionCookies();

        // Set user agent
        await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

        // Set viewport
        await this.page.setViewport({ width: 1920, height: 1080 });
        
        console.log('✅ Browser initialized');
    }

    async _loadSessionCookies() {
        if (!this.sessionFile) {
            return;
        }

        try {
            if (!await fs.pathExists(this.sessionFile)) {
                console.log(`ℹ️  No existing session file found at ${this.sessionFile}`);
                return;
            }

            const cookies = await fs.readJSON(this.sessionFile);
            if (!Array.isArray(cookies) || cookies.length === 0) {
                console.log(`ℹ️  Session file ${this.sessionFile} is empty; proceeding with manual login`);
                return;
            }

            await this.page.setCookie(...cookies);
            console.log(`🔐 Restored ${cookies.length} session cookies from ${this.sessionFile}`);
        } catch (error) {
            console.warn(`⚠️  Failed to restore session cookies from ${this.sessionFile}: ${error.message}`);
        }
    }

    async _saveSessionCookies() {
        if (!this.sessionFile || !this.page || !this.sessionReady) {
            return;
        }

        try {
            const cookies = await this.page.cookies();
            await fs.ensureDir(path.dirname(this.sessionFile));
            await fs.writeJSON(this.sessionFile, cookies, { spaces: 2 });
            console.log(`💾 Saved ${cookies.length} session cookies to ${this.sessionFile}`);
        } catch (error) {
            console.warn(`⚠️  Failed to persist session cookies to ${this.sessionFile}: ${error.message}`);
        }
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
                await this.waitForPhotosInterface(300000); // 5 minutes for manual login

                console.log('✅ Login completed');
            } else {
                console.log('✅ Already logged in');
            }

            await this.waitForPhotosInterface();

            // Wait a bit more for the interface to stabilize
            await new Promise(resolve => setTimeout(resolve, 3000));

            await this._saveSessionCookies();

            return true;
        } catch (error) {
            console.error('❌ Login failed:', error.message);
            return false;
        }
    }

    async waitForPhotosInterface(timeout = 60000) {
        const start = Date.now();
        console.log('⏳ Waiting for Photos interface to become ready...');
        const selectors = this.selectors.pageSelectors || {};
        const candidates = [
            selectors.photosPage,
            selectors.uploadButton,
            selectors.fileInput,
            '[data-testid="photos-app"]',
            '.photos-app',
            '[aria-label*="Photos"]',
            'main',
            '.main-content'
        ].filter(Boolean);

        while (Date.now() - start < timeout) {
            for (const frame of this.page.frames()) {
                for (const selector of candidates) {
                    try {
                        const element = await frame.$(selector);
                        if (element) {
                            await element.dispose();
                            const elapsed = Date.now() - start;
                            console.log(`✅ Photos interface ready after ${Math.round(elapsed / 1000)}s`);
                            this.sessionReady = true;
                            return frame;
                        }
                    } catch (error) {
                        // Ignore selector errors, continue checking other frames/selectors
                    }
                }
            }

            await this.page.waitForTimeout(1000);
        }

        const elapsed = Date.now() - start;
        const selectorList = candidates.join(', ') || 'no selectors provided';
        throw new Error(`Timed out waiting for the iCloud Photos interface after ${Math.round(elapsed / 1000)}s (selectors checked: ${selectorList})`);
    }

    getUploadSelectors() {
        const configuredSelectors = Array.isArray(this.selectors.uploadButtonSelectors)
            ? [...this.selectors.uploadButtonSelectors]
            : [];

        if (this.customUploadSelector) {
            configuredSelectors.unshift(this.customUploadSelector);
        }

        // Remove pseudo selectors that Puppeteer cannot handle directly
        return configuredSelectors.filter(Boolean).map(selector => selector.trim()).filter(selector => {
            return !selector.includes(':contains');
        });
    }

    async clickElement(handle) {
        try {
            await handle.click({ delay: 20 });
            return true;
        } catch (error) {
            try {
                await handle.evaluate(el => el.click());
                return true;
            } catch (innerError) {
                return false;
            }
        }
    }

    async findFileInput(timeout = 5000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            for (const frame of this.page.frames()) {
                const inputs = await frame.$$('input[type="file"]');
                for (const input of inputs) {
                    const isDisabled = await input.evaluate(el => el.disabled || el.getAttribute('aria-hidden') === 'true');
                    if (!isDisabled) {
                        return input;
                    }
                    await input.dispose();
                }
            }

            await this.page.waitForTimeout(500);
        }

        return null;
    }

    async triggerUploadInterface() {
        const selectors = this.getUploadSelectors();
        if (selectors.length === 0) {
            console.log('⚠️  No upload selectors configured. Provide --upload-selector or set ICLOUD_UPLOAD_SELECTOR.');
            return null;
        }

        for (const selector of selectors) {
            for (const frame of this.page.frames()) {
                try {
                    const element = await frame.$(selector);
                    if (!element) {
                        continue;
                    }

                    console.log(`🔍 Found potential upload trigger: ${selector}`);
                    const clicked = await this.clickElement(element);
                    await element.dispose();

                    if (!clicked) {
                        continue;
                    }

                    // Give the DOM some time to inject the file input
                    const inputHandle = await this.findFileInput(4000);
                    if (inputHandle) {
                        return inputHandle;
                    }
                } catch (error) {
                    // Ignore selector errors and continue
                }
            }
        }

        return null;
    }

    async waitForUploadCompletion() {
        const selectors = this.selectors.waitSelectors || {};
        const successSelectors = [selectors.uploadComplete, '[data-testid="upload-complete"]', '.upload-complete'].filter(Boolean);
        const progressSelectors = [selectors.uploadProgress, '[data-testid="upload-progress"]', '.upload-progress'].filter(Boolean);
        const errorSelectors = ['[data-testid*="error"]', '.error', '[aria-label*="error"]'];

        const start = Date.now();

        while (Date.now() - start < UPLOAD_TIMEOUT) {
            for (const frame of this.page.frames()) {
                for (const selector of errorSelectors) {
                    const errorElement = await frame.$(selector);
                    if (errorElement) {
                        await errorElement.dispose();
                        throw new Error('iCloud reported an error during upload');
                    }
                }

                for (const selector of successSelectors) {
                    const successElement = await frame.$(selector);
                    if (successElement) {
                        await successElement.dispose();
                        return true;
                    }
                }

                if (progressSelectors.length > 0) {
                    const progressElement = await frame.$(progressSelectors[0]);
                    if (progressElement) {
                        await progressElement.dispose();
                        // Progress detected, keep waiting
                    }
                }
            }

            await this.page.waitForTimeout(1000);
        }

        throw new Error('Upload timed out waiting for completion');
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
        // Check if file exists
        if (!await fs.pathExists(filePath)) {
            throw new Error(`File not found: ${filePath}`);
        }

        console.log(`📎 Attempting to upload: ${path.basename(filePath)}`);

        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                const fileInput = await this.findFileInput(1000) || await this.triggerUploadInterface();

                if (!fileInput) {
                    console.log('⚠️  Could not locate a usable file input.');
                    if (attempt === MAX_RETRIES) {
                        console.log('💡 Tip: Provide a custom selector with --upload-selector or ICLOUD_UPLOAD_SELECTOR.');
                    }
                    continue;
                }

                await fileInput.uploadFile(filePath);

                try {
                    await this.waitForUploadCompletion();
                    await fileInput.dispose();
                    return true;
                } catch (waitError) {
                    await fileInput.dispose();
                    throw waitError;
                }
            } catch (error) {
                console.error(`❌ Attempt ${attempt} failed: ${error.message}`);
                if (attempt < MAX_RETRIES) {
                    console.log('🔁 Retrying upload...');
                    await this.page.waitForTimeout(2000);
                }
            }
        }

        return false;
    }

    async close() {
        if (this.browser) {
            await this._saveSessionCookies();
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
    let customUploadSelector = process.env.ICLOUD_UPLOAD_SELECTOR || null;
    let sessionFile = process.env.ICLOUD_SESSION_FILE || null;
    let showHelp = false;

    // Parse arguments
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--dir' && i + 1 < args.length) {
            uploadDir = args[i + 1];
            i++;
        } else if (args[i] === '--interactive') {
            interactive = true;
        } else if (args[i] === '--upload-selector' && i + 1 < args.length) {
            customUploadSelector = args[i + 1];
            i++;
        } else if (args[i] === '--session-file' && i + 1 < args.length) {
            sessionFile = args[i + 1];
            i++;
        } else if (args[i] === '--help') {
            showHelp = true;
        }
    }

    if (showHelp) {
        console.log(`
Automated iCloud Photos Upload Script

Usage: node upload_icloud.js [options]

Options:
  --dir <path>      Directory containing files to upload
  --interactive     Enable interactive mode (manual login)
  --upload-selector <css>  Custom CSS selector for the upload button/input
  --session-file <path>    Persist and reuse session cookies between runs
  --help           Show this help message

Examples:
  node upload_icloud.js --dir /path/to/files
  node upload_icloud.js --dir /path/to/files --interactive
  node upload_icloud.js --dir /path/to/files --session-file /opt/media-pipeline/.config/icloud_session.json
  node upload_icloud.js --dir /path/to/files --upload-selector "button[aria-label='Upload']"
        `);
        return 0;
    }

    if (!uploadDir) {
        console.error('❌ Error: --dir parameter is required');
        console.log('Use --help for usage information');
        return 1;
    }

    // Check if directory exists
    if (!await fs.pathExists(uploadDir)) {
        console.error(`❌ Error: Directory not found: ${uploadDir}`);
        return 1;
    }

    // Get files to upload
    const files = await fs.readdir(uploadDir);
    const mediaFiles = files.filter(file => {
        const ext = path.extname(file).toLowerCase();
        return ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'].includes(ext);
    }).map(file => path.join(uploadDir, file));

    if (mediaFiles.length === 0) {
        console.log('ℹ️  No media files found to upload');
        return 0;
    }

    console.log(`📁 Found ${mediaFiles.length} media files to upload`);

    const uploader = new ICloudUploader({ customUploadSelector, sessionFile });

    let exitCode = 0;

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
            exitCode = 1;
        } else {
            console.log(`\n🎉 All uploads completed successfully!`);
            exitCode = 0;
        }

    } catch (error) {
        console.error('❌ Fatal error:', error.message);
        exitCode = 1;
    } finally {
        await uploader.close();
    }

    return exitCode;
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main()
        .then(code => {
            if (typeof code === 'number') {
                process.exitCode = code;
            }
        })
        .catch(error => {
            console.error(error);
            process.exitCode = 1;
        });
}

export default ICloudUploader;
