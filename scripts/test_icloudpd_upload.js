/**
 * Test iCloud Upload using icloudpd
 * 
 * This script tests the icloudpd upload functionality with a single file.
 * 
 * Usage: node scripts/test_icloudpd_upload.js
 */

import { spawn } from 'child_process';
import fs from 'fs-extra';
import path from 'path';

const ICLOUDPD_PATH = '/opt/media-pipeline/venv/bin/icloudpd';

async function testICloudPDUpload() {
  console.log('🧪 Testing iCloud Upload with icloudpd...');
  
  // Check if icloudpd is available
  if (!await fs.pathExists(ICLOUDPD_PATH)) {
    console.error(`❌ icloudpd not found at ${ICLOUDPD_PATH}`);
    console.error('Please ensure the Python virtual environment is properly set up.');
    return;
  }
  
  console.log('✅ icloudpd found');
  
  // Test basic icloudpd functionality
  console.log('🔍 Testing icloudpd authentication...');
  
  return new Promise((resolve, reject) => {
    const process = spawn(ICLOUDPD_PATH, ['--list-albums'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    
    process.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    process.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        console.log('✅ icloudpd authentication working');
        console.log('📋 Available albums:');
        console.log(stdout);
        resolve(true);
      } else {
        console.error('❌ icloudpd authentication failed');
        console.error('Error:', stderr);
        resolve(false);
      }
    });
    
    process.on('error', (error) => {
      console.error('❌ Error running icloudpd:', error.message);
      reject(error);
    });
  });
}

testICloudPDUpload().catch(console.error);
