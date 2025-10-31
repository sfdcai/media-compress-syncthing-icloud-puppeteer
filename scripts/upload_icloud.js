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

const DEFAULT_MAX_RETRIES = (() => {
    const envValue = process.env.UPLOAD_RETRY_ATTEMPTS;
    const parsed = Number.parseInt(envValue ?? '3', 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 3;
})();

const DEFAULT_RETRY_DELAY_MS = (() => {
    const envValue = process.env.UPLOAD_RETRY_DELAY;
    const parsed = Number.parseFloat(envValue ?? '2');
    if (Number.isFinite(parsed) && parsed >= 0) {
        return Math.round(parsed * 1000);
    }
    return 2000;
})();

const DEFAULT_UPLOAD_TIMEOUT_MS = (() => {
    const timeoutMs = Number.parseInt(process.env.ICLOUD_UPLOAD_TIMEOUT_MS ?? '', 10);
    if (Number.isFinite(timeoutMs) && timeoutMs > 0) {
        return timeoutMs;
    }
    const timeoutSeconds = Number.parseFloat(process.env.ICLOUD_UPLOAD_TIMEOUT ?? '300');
    if (Number.isFinite(timeoutSeconds) && timeoutSeconds > 0) {
        return Math.round(timeoutSeconds * 1000);
    }
    return 300000; // 5 minutes per file
})();

const DEFAULT_SLOWMO_MS = (() => {
    const slowMo = Number.parseInt(process.env.PUPPETEER_SLOWMO ?? '0', 10);
    return Number.isFinite(slowMo) && slowMo >= 0 ? slowMo : 0;
})();

const DEFAULT_LAUNCH_ARGS = [
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
];

const parseHeadlessPreference = () => {
    const raw = process.env.PUPPETEER_HEADLESS;
    if (!raw) {
        return 'new';
    }

    const normalized = raw.toLowerCase();
    if (['false', 'no', 'off', 'headful'].includes(normalized)) {
        return false;
    }

    if (['true', 'yes', 'on'].includes(normalized)) {
        return true;
    }

    // Allow explicit Puppeteer modes such as "new" or "shell"
    return raw;
};

const parseListEnv = (value) => {
    if (!value) {
        return [];
    }

    return value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
};

class ICloudUploader {
    constructor(options = {}) {
        const {
            customUploadSelector = null,
            sessionFile = null,
            headless = parseHeadlessPreference(),
            maxRetries = DEFAULT_MAX_RETRIES,
            retryDelayMs = DEFAULT_RETRY_DELAY_MS,
            uploadTimeoutMs = DEFAULT_UPLOAD_TIMEOUT_MS,
            slowMo = DEFAULT_SLOWMO_MS,
            extraLaunchArgs = parseListEnv(process.env.PUPPETEER_EXTRA_ARGS)
        } = options;

        this.browser = null;
        this.page = null;
        this.uploadedFiles = [];
        this.failedFiles = [];
        this.customUploadSelector = customUploadSelector;
        this.sessionFile = sessionFile;
        this.sessionReady = false;
        this.selectors = selectorsConfig;
        this.headless = headless;
        this.maxRetries = Number.isFinite(maxRetries) && maxRetries > 0 ? Math.floor(maxRetries) : DEFAULT_MAX_RETRIES;
        this.retryDelayMs = Number.isFinite(retryDelayMs) && retryDelayMs >= 0 ? retryDelayMs : DEFAULT_RETRY_DELAY_MS;
        this.uploadTimeoutMs = Number.isFinite(uploadTimeoutMs) && uploadTimeoutMs > 0 ? uploadTimeoutMs : DEFAULT_UPLOAD_TIMEOUT_MS;
        this.slowMo = Number.isFinite(slowMo) && slowMo >= 0 ? slowMo : DEFAULT_SLOWMO_MS;
        this.extraLaunchArgs = Array.isArray(extraLaunchArgs) ? extraLaunchArgs : [];
    }

    async init() {
        console.log('🚀 Initializing iCloud uploader...');

        const launchArgs = [...DEFAULT_LAUNCH_ARGS, ...this.extraLaunchArgs];
        if (launchArgs.length > DEFAULT_LAUNCH_ARGS.length) {
            console.log(`⚙️  Applying additional launch args: ${this.extraLaunchArgs.join(', ')}`);
        }

        this.browser = await puppeteer.launch({
            headless: this.headless,
            slowMo: this.slowMo,
            args: launchArgs,
        });

        this.page = await this.browser.newPage();

        await this._loadSessionCookies();

        // Set user agent
        await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

        // Set viewport
        await this.page.setViewport({ width: 1920, height: 1080 });

        console.log(`✅ Browser initialized (headless: ${this.headless})`);
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

        while (Date.now() - start < this.uploadTimeoutMs) {
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
        console.log(
            `⚙️  Upload config → maxRetries: ${this.maxRetries}, retryDelay: ${Math.round(this.retryDelayMs / 100) / 10}s, timeout: ${Math.round(this.uploadTimeoutMs / 1000)}s`
        );

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

        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                const fileInput = await this.findFileInput(1000) || await this.triggerUploadInterface();

                if (!fileInput) {
                    console.log('⚠️  Could not locate a usable file input.');
                    if (attempt === this.maxRetries) {
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
                if (attempt < this.maxRetries) {
                    console.log('🔁 Retrying upload...');
                    await this.page.waitForTimeout(this.retryDelayMs);
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
    let maxRetries = DEFAULT_MAX_RETRIES;
    let retryDelayMs = DEFAULT_RETRY_DELAY_MS;
    let uploadTimeoutMs = DEFAULT_UPLOAD_TIMEOUT_MS;
    let slowMo = DEFAULT_SLOWMO_MS;
    let headless = parseHeadlessPreference();
    let headlessExplicit = false;
    let extraLaunchArgs = parseListEnv(process.env.PUPPETEER_EXTRA_ARGS);

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
        } else if (args[i] === '--max-retries' && i + 1 < args.length) {
            const parsed = Number.parseInt(args[i + 1], 10);
            if (Number.isFinite(parsed) && parsed > 0) {
                maxRetries = parsed;
            }
            i++;
        } else if (args[i] === '--retry-delay' && i + 1 < args.length) {
            const parsed = Number.parseFloat(args[i + 1]);
            if (Number.isFinite(parsed) && parsed >= 0) {
                retryDelayMs = Math.round(parsed * 1000);
            }
            i++;
        } else if (args[i] === '--timeout' && i + 1 < args.length) {
            const parsed = Number.parseFloat(args[i + 1]);
            if (Number.isFinite(parsed) && parsed > 0) {
                uploadTimeoutMs = Math.round(parsed * 1000);
            }
            i++;
        } else if (args[i] === '--slowmo' && i + 1 < args.length) {
            const parsed = Number.parseInt(args[i + 1], 10);
            if (Number.isFinite(parsed) && parsed >= 0) {
                slowMo = parsed;
            }
            i++;
        } else if (args[i] === '--headless') {
            const next = args[i + 1];
            if (next && !next.startsWith('--')) {
                const normalized = next.toLowerCase();
                if (['false', 'no', 'off', 'headful'].includes(normalized)) {
                    headless = false;
                } else if (['true', 'yes', 'on'].includes(normalized)) {
                    headless = true;
                } else {
                    headless = next;
                }
                headlessExplicit = true;
                i++;
            } else {
                headless = true;
                headlessExplicit = true;
            }
        } else if (args[i] === '--headful' || args[i] === '--no-headless') {
            headless = false;
            headlessExplicit = true;
        } else if (args[i] === '--launch-arg' && i + 1 < args.length) {
            extraLaunchArgs.push(args[i + 1]);
            i++;
        } else if (args[i] === '--help') {
            showHelp = true;
        }
    }

    if (interactive && !headlessExplicit) {
        headless = false;
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
  --max-retries <n>  Number of upload retries before giving up (default: env or ${DEFAULT_MAX_RETRIES})
  --retry-delay <s>  Seconds to wait between retries (default: env or ${Math.round(DEFAULT_RETRY_DELAY_MS / 1000)})
  --timeout <s>      Seconds to wait for upload completion (default: env or ${Math.round(DEFAULT_UPLOAD_TIMEOUT_MS / 1000)})
  --slowmo <ms>      Milliseconds of Puppeteer slow-motion delay (default: env or ${DEFAULT_SLOWMO_MS})
  --headless [mode]  Force headless mode (true/false/new)
  --headful          Alias for --headless false
  --launch-arg <arg> Append an additional Chromium launch argument
  --help           Show this help message

Examples:
  node upload_icloud.js --dir /path/to/files
  node upload_icloud.js --dir /path/to/files --interactive
  node upload_icloud.js --dir /path/to/files --session-file /opt/media-pipeline/.config/icloud_session.json
  node upload_icloud.js --dir /path/to/files --upload-selector "button[aria-label='Upload']"
  node upload_icloud.js --dir /path/to/files --max-retries 5 --retry-delay 10 --timeout 600
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

    const uploader = new ICloudUploader({
        customUploadSelector,
        sessionFile,
        headless,
        maxRetries,
        retryDelayMs,
        uploadTimeoutMs,
        slowMo,
        extraLaunchArgs,
    });

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
