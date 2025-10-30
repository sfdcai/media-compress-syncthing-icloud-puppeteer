# Media Pipeline Web Dashboard Troubleshooting Guide

## Common Issues and Solutions

### 1. Web Dashboard Not Accessible

**Symptoms:**
- Cannot access http://IP:5000
- Connection refused or timeout errors
- Service not running

**Solutions:**
```bash
# Check service status
sudo systemctl status media-pipeline-web

# Check if service is running
sudo systemctl is-active media-pipeline-web

# Start the service
sudo systemctl start media-pipeline-web

# Check logs
sudo journalctl -u media-pipeline-web -f

# Check if port 5000 is listening
sudo netstat -tlnp | grep :5000
```

### 2. Permission Errors

**Symptoms:**
- Permission denied errors in logs
- Service fails to start
- Cannot access files

**Solutions:**
```bash
# Fix ownership
sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline/web

# Fix permissions
sudo chmod -R 755 /opt/media-pipeline/web
sudo chmod +x /opt/media-pipeline/web/server.py

# Check user exists
id media-pipeline
```

### 3. Python Dependencies Missing

**Symptoms:**
- ImportError for Flask or other modules
- Service fails to start with Python errors

**Solutions:**
```bash
# Install missing dependencies
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install flask flask-cors requests

# Check installed packages
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip list

# Reinstall all requirements
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install -r /opt/media-pipeline/requirements.txt
```

### 4. Database Connection Issues

**Symptoms:**
- Supabase connection errors
- Database status shows as disconnected
- API calls fail

**Solutions:**
```bash
# Check Supabase configuration
grep -E "SUPABASE_URL|SUPABASE_KEY" /opt/media-pipeline/config/settings.env

# Test Supabase connection
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py

# Check network connectivity
ping supabase.com
```

### 5. Service Management Issues

**Symptoms:**
- Service won't start/stop/restart
- Service keeps crashing
- High restart count

**Solutions:**
```bash
# Check service configuration
sudo systemctl cat media-pipeline-web

# Reload systemd configuration
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart media-pipeline-web

# Check for conflicts
sudo systemctl list-units --failed
```

### 6. Firewall Issues

**Symptoms:**
- Cannot access from remote machines
- Connection timeout from external IPs

**Solutions:**
```bash
# Check UFW status
sudo ufw status

# Allow port 5000
sudo ufw allow 5000/tcp

# Check if port is open
sudo netstat -tlnp | grep :5000

# Test local access first
curl http://localhost:5000/api/status
```

### 7. API Endpoint Errors

**Symptoms:**
- API calls return 500 errors
- JSON parsing errors
- Timeout errors

**Solutions:**
```bash
# Check API logs
sudo journalctl -u media-pipeline-web -f

# Test individual endpoints
curl http://localhost:5000/api/status
curl http://localhost:5000/api/config

# Check Python path
echo $PYTHONPATH

# Verify script permissions
ls -la /opt/media-pipeline/web/server.py
```

### 8. Configuration Issues

**Symptoms:**
- Configuration not loading
- Feature toggles not working
- Settings not saving

**Solutions:**
```bash
# Check config file exists and is readable
ls -la /opt/media-pipeline/config/settings.env

# Check file permissions
sudo chmod 644 /opt/media-pipeline/config/settings.env
sudo chown media-pipeline:media-pipeline /opt/media-pipeline/config/settings.env

# Validate configuration
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/media-pipeline/config/settings.env')
print('Config loaded successfully')
"
```

### 9. Performance Issues

**Symptoms:**
- Slow page loading
- High CPU usage
- Memory issues

**Solutions:**
```bash
# Check system resources
htop
free -h
df -h

# Check service resource usage
sudo systemctl status media-pipeline-web

# Monitor logs for errors
sudo journalctl -u media-pipeline-web --since "1 hour ago"

# Restart service to clear memory
sudo systemctl restart media-pipeline-web
```

### 10. SSL/HTTPS Issues

**Symptoms:**
- Mixed content warnings
- SSL certificate errors
- HTTPS not working

**Solutions:**
```bash
# For production, consider using a reverse proxy like nginx
# Install nginx
sudo apt install nginx

# Create nginx configuration
sudo nano /etc/nginx/sites-available/media-pipeline-web

# Enable site
sudo ln -s /etc/nginx/sites-available/media-pipeline-web /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Advanced Troubleshooting

### Debug Mode

Enable debug mode for more detailed logging:

```bash
# Edit the service file
sudo systemctl edit media-pipeline-web

# Add environment variables
[Service]
Environment=FLASK_ENV=development
Environment=FLASK_DEBUG=1

# Restart service
sudo systemctl restart media-pipeline-web
```

### Manual Testing

Test the web server manually:

```bash
# Run server manually
cd /opt/media-pipeline/web
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python server.py

# Test in another terminal
curl http://localhost:5000/api/status
```

### Log Analysis

Analyze logs for patterns:

```bash
# Check for errors
sudo journalctl -u media-pipeline-web | grep -i error

# Check for warnings
sudo journalctl -u media-pipeline-web | grep -i warn

# Check startup sequence
sudo journalctl -u media-pipeline-web --since "10 minutes ago"
```

### Network Diagnostics

```bash
# Check if port is open
sudo netstat -tlnp | grep :5000

# Test connectivity
telnet localhost 5000

# Check firewall rules
sudo ufw status numbered
```

## Emergency Recovery

If the web dashboard is completely broken:

```bash
# Stop the service
sudo systemctl stop media-pipeline-web
sudo systemctl disable media-pipeline-web

# Remove service file
sudo rm /etc/systemd/system/media-pipeline-web.service
sudo systemctl daemon-reload

# Reinstall
cd /opt/media-pipeline/web
sudo ./install_web_dashboard.sh
```

## Getting Help

1. **Check Logs**: Always start with `sudo journalctl -u media-pipeline-web -f`
2. **Verify Service Status**: `sudo systemctl status media-pipeline-web`
3. **Test Manually**: Run the server manually to isolate issues
4. **Check Dependencies**: Ensure all Python packages are installed
5. **Verify Permissions**: Check file ownership and permissions

## Prevention

- Regularly update the system and packages
- Monitor service logs for early warning signs
- Keep backups of configuration files
- Test changes in a development environment first
- Use proper firewall rules and security practices