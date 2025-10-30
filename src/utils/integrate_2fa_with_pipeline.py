#!/usr/bin/env python3
"""
Integration script to add intelligent 2FA handling to existing pipeline steps
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step
from intelligent_2fa_handler import Intelligent2FAHandler

def patch_icloudpd_for_2fa():
    """Patch icloudpd to use intelligent 2FA handler"""
    try:
        # Find icloudpd installation
        result = subprocess.run(['which', 'icloudpd'], capture_output=True, text=True)
        if result.returncode != 0:
            log_step("integrate_2fa", "icloudpd not found in PATH", "error")
            return False
        
        icloudpd_path = result.stdout.strip()
        log_step("integrate_2fa", f"Found icloudpd at: {icloudpd_path}", "info")
        
        # Create a wrapper script for icloudpd with 2FA support
        wrapper_script = f"""#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_2fa_handler import Intelligent2FAHandler

def main():
    # Initialize 2FA handler
    handler = Intelligent2FAHandler()
    
    # Get 2FA code if needed
    print("🔐 Checking for 2FA requirement...")
    
    # Run original icloudpd command
    original_args = sys.argv[1:]
    cmd = ['{icloudpd_path}'] + original_args
    
    # Add 2FA handling
    cmd.extend(['--trusted-device', '--no-progress-bar'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check if 2FA is required
        if 'Two-factor authentication is required' in result.stderr:
            print("🔐 2FA required, requesting code via Telegram...")
            code = handler.wait_for_2fa_code("iCloud Download", 5)
            
            if code:
                print(f"✅ 2FA code received: {code}")
                # Retry with 2FA code
                cmd.extend(['--password', os.getenv('ICLOUD_PASSWORD')])
                result = subprocess.run(cmd, capture_output=True, text=True)
            else:
                print("❌ No 2FA code received")
                return 1
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode
        
    except Exception as e:
        print(f"Error running icloudpd: {{e}}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
        
        wrapper_path = project_root / "scripts" / "icloudpd_with_2fa.py"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_script)
        
        # Make executable
        os.chmod(wrapper_path, 0o755)
        
        log_step("integrate_2fa", f"Created icloudpd wrapper: {wrapper_path}", "info")
        return True
        
    except Exception as e:
        log_step("integrate_2fa", f"Error patching icloudpd: {e}", "error")
        return False

def patch_upload_script():
    """Update upload_icloud.js to use intelligent 2FA handler"""
    try:
        upload_script_path = project_root / "scripts" / "upload_icloud.js"
        
        if not upload_script_path.exists():
            log_step("integrate_2fa", "upload_icloud.js not found", "error")
            return False
        
        # Read current script
        with open(upload_script_path, 'r') as f:
            content = f.read()
        
        # Replace the 2FA handler call
        old_2fa_call = """    const pythonScript = spawn('python3', [
      path.join(__dirname, 'telegram_2fa_optimized.py'),
      '--wait',
      '--step', pipelineStep,
      '--timeout', timeoutMinutes.toString()
    ], {"""
        
        new_2fa_call = """    const pythonScript = spawn('python3', [
      path.join(__dirname, 'intelligent_2fa_handler.py'),
      'wait',
      pipelineStep,
      timeoutMinutes.toString()
    ], {"""
        
        if old_2fa_call in content:
            content = content.replace(old_2fa_call, new_2fa_call)
            
            # Write updated script
            with open(upload_script_path, 'w') as f:
                f.write(content)
            
            log_step("integrate_2fa", "Updated upload_icloud.js to use intelligent 2FA handler", "info")
            return True
        else:
            log_step("integrate_2fa", "Could not find 2FA handler call in upload_icloud.js", "warning")
            return False
        
    except Exception as e:
        log_step("integrate_2fa", f"Error patching upload script: {e}", "error")
        return False

def create_2fa_service():
    """Create systemd service for Telegram webhook handler"""
    try:
        service_content = f"""[Unit]
Description=Media Pipeline Telegram Webhook Handler
After=network.target

[Service]
Type=simple
User=media-pipeline
Group=media-pipeline
WorkingDirectory={project_root}
ExecStart={project_root}/venv/bin/python {project_root}/scripts/telegram_webhook_handler.py poll
Restart=always
RestartSec=10
Environment=PATH={project_root}/venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile={project_root}/config/settings.env

[Install]
WantedBy=multi-user.target
"""
        
        service_path = Path("/etc/systemd/system/media-pipeline-telegram.service")
        
        # Write service file
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Reload systemd and enable service
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', 'enable', 'media-pipeline-telegram'], check=True)
        
        log_step("integrate_2fa", "Created Telegram webhook service", "info")
        return True
        
    except Exception as e:
        log_step("integrate_2fa", f"Error creating Telegram service: {e}", "error")
        return False

def setup_supabase_tables():
    """Setup Supabase tables for Telegram integration"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            log_step("integrate_2fa", "Supabase credentials not found", "warning")
            return False
        
        # Read SQL file
        sql_file = project_root / "scripts" / "setup_telegram_tables.sql"
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL via Supabase REST API
        import requests
        
        url = f"{supabase_url}/rest/v1/rpc/exec_sql"
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        
        data = {'sql': sql_content}
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            log_step("integrate_2fa", "Supabase tables created successfully", "info")
            return True
        else:
            log_step("integrate_2fa", f"Failed to create Supabase tables: {response.text}", "error")
            return False
        
    except Exception as e:
        log_step("integrate_2fa", f"Error setting up Supabase tables: {e}", "error")
        return False

def main():
    """Main integration function"""
    log_step("integrate_2fa", "Starting 2FA integration", "info")
    
    success_count = 0
    total_steps = 4
    
    # Step 1: Setup Supabase tables
    if setup_supabase_tables():
        success_count += 1
    
    # Step 2: Patch icloudpd
    if patch_icloudpd_for_2fa():
        success_count += 1
    
    # Step 3: Patch upload script
    if patch_upload_script():
        success_count += 1
    
    # Step 4: Create Telegram service
    if create_2fa_service():
        success_count += 1
    
    log_step("integrate_2fa", f"Integration completed: {success_count}/{total_steps} steps successful", "info")
    
    if success_count == total_steps:
        print("✅ All integration steps completed successfully!")
        print("\nNext steps:")
        print("1. Start the Telegram webhook service:")
        print("   sudo systemctl start media-pipeline-telegram")
        print("2. Test the 2FA integration:")
        print("   python3 scripts/intelligent_2fa_handler.py wait 'Test Pipeline'")
        print("3. Check Telegram bot commands:")
        print("   Send /help to your bot")
    else:
        print(f"⚠️ Integration completed with {total_steps - success_count} issues")
        print("Please check the logs for details")

if __name__ == "__main__":
    main()