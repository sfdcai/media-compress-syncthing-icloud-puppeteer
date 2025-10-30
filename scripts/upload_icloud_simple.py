#!/usr/bin/env python3
"""
Simple iCloud Photos Upload Script
Uses a more direct approach with better error handling
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

class SimpleICloudUploader:
    def __init__(self):
        self.driver = None
        self.uploaded_files = []
        self.failed_files = []
    
    def init_driver(self):
        """Initialize Chrome WebDriver"""
        print("🚀 Initializing iCloud uploader...")
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ WebDriver initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize WebDriver: {e}")
            return False
    
    def login(self):
        """Navigate to iCloud Photos"""
        print("🔐 Navigating to iCloud Photos...")
        
        try:
            self.driver.get('https://www.icloud.com/photos')
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                lambda driver: 'Photos' in driver.title or 'iCloud' in driver.title
            )
            
            time.sleep(5)
            print("✅ Page loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            return False
    
    def find_upload_method(self):
        """Find the best upload method available"""
        print("🔍 Looking for upload methods...")
        
        # Method 1: Look for file input
        try:
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            if file_inputs:
                print("📎 Found file input element")
                return 'file_input', file_inputs[0]
        except:
            pass
        
        # Method 2: Look for upload buttons
        upload_button_selectors = [
            'button[aria-label*="Upload"]',
            'button[aria-label*="Add"]',
            'button[aria-label*="Import"]',
            '[data-testid*="upload"]',
            '[data-testid*="add"]',
            'button:contains("+")',
            'button:contains("Upload")',
            'button:contains("Add")'
        ]
        
        for selector in upload_button_selectors:
            try:
                if ':contains(' in selector:
                    # Use XPath for text content
                    xpath = f"//button[contains(text(), '{selector.split(':contains(')[1].rstrip(')')}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    print(f"🔘 Found upload button: {selector}")
                    return 'button', elements[0]
            except:
                continue
        
        # Method 3: Look for any clickable element that might trigger upload
        try:
            clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="button"], button, [onclick]')
            if clickable_elements:
                print("🔘 Found clickable elements, will try clicking")
                return 'clickable', clickable_elements[0]
        except:
            pass
        
        print("❌ No upload method found")
        return None, None
    
    def upload_file(self, file_path):
        """Upload a single file"""
        filename = os.path.basename(file_path)
        print(f"📁 Uploading: {filename}")
        
        try:
            method, element = self.find_upload_method()
            
            if method == 'file_input':
                print("📎 Using file input method...")
                element.send_keys(file_path)
                time.sleep(10)
                return True
            
            elif method == 'button' or method == 'clickable':
                print("🔘 Using button click method...")
                element.click()
                time.sleep(3)
                
                # Look for file input after clicking
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                    print("📎 File input appeared after click")
                    file_input.send_keys(file_path)
                    time.sleep(15)
                    return True
                except NoSuchElementException:
                    print("❌ No file input appeared after click")
                    return False
            
            else:
                print("❌ No upload method available")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def upload_files(self, file_paths):
        """Upload multiple files"""
        print(f"📤 Starting upload of {len(file_paths)} files...")
        
        for i, file_path in enumerate(file_paths):
            print(f"\n📁 File {i + 1}/{len(file_paths)}: {os.path.basename(file_path)}")
            
            if self.upload_file(file_path):
                print(f"✅ Success: {os.path.basename(file_path)}")
                self.uploaded_files.append(file_path)
            else:
                print(f"❌ Failed: {os.path.basename(file_path)}")
                self.failed_files.append(file_path)
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser closed")
    
    def print_summary(self):
        """Print results"""
        print(f"\n📊 Upload Summary:")
        print(f"✅ Successful: {len(self.uploaded_files)}")
        print(f"❌ Failed: {len(self.failed_files)}")
        
        if self.failed_files:
            print("\n⚠️  Failed files:")
            for file_path in self.failed_files:
                print(f"   - {os.path.basename(file_path)}")

def main():
    """Main function"""
    directory = './test_files'
    if len(sys.argv) > 2 and sys.argv[1] == '--dir':
        directory = sys.argv[2]
    
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        sys.exit(1)
    
    # Find media files
    media_extensions = ['*.jpg', '*.jpeg', '*.png', '*.heic', '*.heif', '*.mp4', '*.mov', '*.avi']
    files = []
    for ext in media_extensions:
        files.extend(glob.glob(os.path.join(directory, ext)))
        files.extend(glob.glob(os.path.join(directory, ext.upper())))
    
    if not files:
        print("ℹ️  No media files found")
        return
    
    print(f"📁 Found {len(files)} media files")
    
    uploader = SimpleICloudUploader()
    
    try:
        if uploader.init_driver() and uploader.login():
            uploader.upload_files(files)
        else:
            print("❌ Failed to initialize or login")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        uploader.close()
        uploader.print_summary()

if __name__ == "__main__":
    main()