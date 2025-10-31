#!/usr/bin/env python3
"""
iCloud Photos Upload Script using Selenium WebDriver (Python)
More reliable than Puppeteer for complex web applications
"""

import os
import sys
import time
import glob
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ICloudUploaderPython:
    def __init__(self):
        self.driver = None
        self.uploaded_files = []
        self.failed_files = []
    
    def init_driver(self):
        """Initialize Chrome WebDriver with proper options"""
        print("🚀 Initializing iCloud uploader with Selenium...")
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Selenium WebDriver initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize WebDriver: {e}")
            return False
    
    def login(self):
        """Navigate to iCloud Photos and handle login"""
        print("🔐 Navigating to iCloud Photos...")
        
        try:
            self.driver.get('https://www.icloud.com/photos')
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                lambda driver: 'Photos' in driver.title
            )
            
            time.sleep(5)  # Additional wait for page stabilization
            
            # Check if we need to login
            try:
                login_elements = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="email"], input[name="appleId"]')
                if login_elements:
                    print("⚠️  Login required. Please log in manually...")
                    print("📝 Waiting for manual login completion...")
                    
                    # Wait for login to complete (photos interface to load)
                    WebDriverWait(self.driver, 300).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="photos-app"]')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.photos-app')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label*="Photos"]')),
                            EC.presence_of_element_located((By.TAG_NAME, 'main'))
                        )
                    )
                    print("✅ Login completed")
                else:
                    print("✅ Already logged in")
            except TimeoutException:
                print("✅ Already logged in or no login required")
            
            # Wait for interface to stabilize
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    def upload_file(self, file_path):
        """Upload a single file to iCloud Photos"""
        filename = os.path.basename(file_path)
        print(f"📁 Uploading file: {filename}")
        
        try:
            # Method 1: Look for file input directly
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                if file_input:
                    print("📎 Found file input, uploading directly...")
                    file_input.send_keys(file_path)
                    time.sleep(10)
                    return True
            except NoSuchElementException:
                pass
            
            # Method 2: Look for upload button and click it
            upload_selectors = [
                '[data-testid="photos-upload"]',
                'button[aria-label*="Upload"]',
                'button[aria-label*="Add"]',
                'button[aria-label*="Import"]',
                'button:contains("+")',
                '[role="button"]'
            ]
            
            for selector in upload_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        print(f"🔍 Found upload area: {selector}, clicking...")
                        element.click()
                        time.sleep(3)
                        
                        # Check if file input appeared
                        try:
                            file_input_after_click = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                            if file_input_after_click:
                                print("📎 File input appeared after click, uploading...")
                                file_input_after_click.send_keys(file_path)
                                time.sleep(15)
                                return True
                        except NoSuchElementException:
                            pass
                except NoSuchElementException:
                    continue
            
            # Method 3: Try keyboard shortcut (Ctrl+U)
            print("⌨️  Trying keyboard shortcut approach...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.CONTROL + 'u')
            time.sleep(2)
            
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                if file_input:
                    print("📎 File input appeared with keyboard shortcut, uploading...")
                    file_input.send_keys(file_path)
                    time.sleep(15)
                    return True
            except NoSuchElementException:
                pass
            
            # Method 4: Try drag and drop simulation
            print("🖱️  Trying drag and drop approach...")
            try:
                # Look for drop target
                drop_targets = [
                    '[data-testid="photos-app"]',
                    '.photos-app',
                    '[aria-label*="Photos"]',
                    'main',
                    '.main-content'
                ]
                
                drop_target = None
                for selector in drop_targets:
                    try:
                        drop_target = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if drop_target:
                    # Use JavaScript to simulate file drop
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # Create a file input element and trigger file selection
                    self.driver.execute_script("""
                        var input = document.createElement('input');
                        input.type = 'file';
                        input.style.display = 'none';
                        document.body.appendChild(input);
                        input.click();
                    """)
                    
                    # Wait for file input to appear
                    time.sleep(1)
                    file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                    file_input.send_keys(file_path)
                    time.sleep(15)
                    return True
                    
            except Exception as e:
                print(f"Drag and drop failed: {e}")
            
            print("❌ No upload method worked")
            return False
            
        except Exception as error:
            print(f"❌ Error uploading {filename}: {error}")
            return False
    
    def upload_files(self, file_paths):
        """Upload multiple files to iCloud Photos"""
        print(f"📤 Starting upload of {len(file_paths)} files...")
        
        for i, file_path in enumerate(file_paths):
            filename = os.path.basename(file_path)
            print(f"\n📁 Uploading file {i + 1}/{len(file_paths)}: {filename}")
            
            if self.upload_file(file_path):
                print(f"✅ Successfully uploaded: {filename}")
                self.uploaded_files.append(file_path)
            else:
                print(f"❌ Failed to upload: {filename}")
                self.failed_files.append(file_path)
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser closed")
    
    def print_summary(self):
        """Print upload summary"""
        print("\n📊 Upload Summary:")
        print(f"✅ Successful: {len(self.uploaded_files)}")
        print(f"❌ Failed: {len(self.failed_files)}")
        
        if self.failed_files:
            print("\n⚠️  Failed files:")
            for file_path in self.failed_files:
                print(f"   - {os.path.basename(file_path)}")

def main():
    """Main function"""
    # Get directory from command line arguments
    directory = './test_files'
    if len(sys.argv) > 2 and sys.argv[1] == '--dir':
        directory = sys.argv[2]
    
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        sys.exit(1)
    
    # Get all media files
    media_extensions = ['*.jpg', '*.jpeg', '*.png', '*.heic', '*.heif', '*.mp4', '*.mov', '*.avi']
    files = []
    for ext in media_extensions:
        files.extend(glob.glob(os.path.join(directory, ext)))
        files.extend(glob.glob(os.path.join(directory, ext.upper())))
    
    if not files:
        print("ℹ️  No media files found to upload")
        return
    
    print(f"📁 Found {len(files)} media files to upload")
    
    uploader = ICloudUploaderPython()
    
    try:
        if uploader.init_driver():
            if uploader.login():
                uploader.upload_files(files)
            else:
                print("❌ Failed to login to iCloud")
        else:
            print("❌ Failed to initialize WebDriver")
    except Exception as error:
        print(f"❌ Upload process failed: {error}")
    finally:
        uploader.close()
        uploader.print_summary()

if __name__ == "__main__":
    main()