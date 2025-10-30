#!/bin/bash
# Complete Media Pipeline Web Dashboard Setup
# This script integrates the web dashboard with the main media pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PIPELINE_DIR="/opt/media-pipeline"
WEB_DIR="$PIPELINE_DIR/web"
SERVICE_NAME="media-pipeline-web"
USER_NAME="media-pipeline"

print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
    esac
}

print_header() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "Media Pipeline Web Dashboard Setup"
    echo "=========================================="
    echo -e "${NC}"
}

check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "README.md" ]] || [[ ! -d "scripts" ]]; then
        print_status "ERROR" "Please run this script from the media-pipeline root directory"
        exit 1
    fi
    
    # Check if main pipeline is installed
    if [[ ! -d "$PIPELINE_DIR" ]]; then
        print_status "ERROR" "Media pipeline not found at $PIPELINE_DIR"
        print_status "INFO" "Please run the main installation first: sudo ./install.sh"
        exit 1
    fi
    
    # Check if user exists
    if ! id "$USER_NAME" &>/dev/null; then
        print_status "ERROR" "User $USER_NAME does not exist"
        print_status "INFO" "Please run the main installation first: sudo ./install.sh"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$PIPELINE_DIR/venv" ]]; then
        print_status "ERROR" "Virtual environment not found"
        print_status "INFO" "Please run the main installation first: sudo ./install.sh"
        exit 1
    fi
    
    print_status "OK" "Prerequisites check passed"
}

install_web_dependencies() {
    print_status "INFO" "Installing web dashboard dependencies..."
    
    # Install Flask and related packages
    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install flask flask-cors
    
    print_status "OK" "Web dependencies installed"
}

setup_web_files() {
    print_status "INFO" "Setting up web dashboard files..."
    
    # Create web directory
    mkdir -p "$WEB_DIR"
    
    # Copy web files
    cp -r web/* "$WEB_DIR/"
    
    # Set ownership and permissions
    chown -R "$USER_NAME:$USER_NAME" "$WEB_DIR"
    chmod -R 755 "$WEB_DIR"
    chmod +x "$WEB_DIR/server.py"
    
    print_status "OK" "Web files setup completed"
}

install_systemd_service() {
    print_status "INFO" "Installing systemd service..."
    
    # Copy service file
    cp "$WEB_DIR/media-pipeline-web.service" "/etc/systemd/system/"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    print_status "OK" "Systemd service installed and enabled"
}

configure_firewall() {
    print_status "INFO" "Configuring firewall..."
    
    # Check if UFW is active
    if ufw status | grep -q "Status: active"; then
        # Allow web dashboard port
        ufw allow 5000/tcp comment "Media Pipeline Web Dashboard"
        print_status "OK" "Firewall configured for port 5000"
    else
        print_status "WARN" "UFW is not active, skipping firewall configuration"
        print_status "INFO" "You may need to manually open port 5000 if using a firewall"
    fi
}

start_web_service() {
    print_status "INFO" "Starting web dashboard service..."
    
    # Start the service
    systemctl start "$SERVICE_NAME"
    
    # Wait for startup
    sleep 3
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "OK" "Web dashboard service started successfully"
    else
        print_status "ERROR" "Failed to start web dashboard service"
        print_status "INFO" "Checking service status..."
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

test_web_dashboard() {
    print_status "INFO" "Testing web dashboard..."
    
    # Wait a moment for service to fully start
    sleep 2
    
    # Test API endpoint
    if curl -s http://localhost:5000/api/status > /dev/null; then
        print_status "OK" "Web dashboard API is responding"
    else
        print_status "WARN" "Web dashboard API test failed"
        print_status "INFO" "Service may still be starting up"
    fi
}

create_nginx_config() {
    print_status "INFO" "Creating nginx configuration template..."
    
    # Check if nginx is installed
    if command -v nginx &> /dev/null; then
        print_status "INFO" "Nginx is installed, creating configuration template"
        
        # Create nginx config
        cat > "/etc/nginx/sites-available/media-pipeline-web" << 'EOF'
server {
    listen 80;
    server_name _;  # Replace with your domain or IP
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF
        
        print_status "OK" "Nginx configuration created at /etc/nginx/sites-available/media-pipeline-web"
        print_status "INFO" "To enable: sudo ln -s /etc/nginx/sites-available/media-pipeline-web /etc/nginx/sites-enabled/"
        print_status "INFO" "Then: sudo nginx -t && sudo systemctl reload nginx"
    else
        print_status "INFO" "Nginx not installed, skipping nginx configuration"
    fi
}

show_completion_info() {
    echo -e "${GREEN}"
    echo "=========================================="
    echo "Web Dashboard Setup Completed!"
    echo "=========================================="
    echo -e "${NC}"
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo -e "${BLUE}Access Information:${NC}"
    echo "  Local Access:  http://localhost:5000"
    echo "  Remote Access: http://$SERVER_IP:5000"
    echo ""
    
    echo -e "${BLUE}Service Management:${NC}"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    
    echo -e "${BLUE}Web Dashboard Features:${NC}"
    echo "  ✓ Real-time system status monitoring"
    echo "  ✓ Pipeline control and manual execution"
    echo "  ✓ Configuration management with feature toggles"
    echo "  ✓ Log viewer with multiple log types"
    echo "  ✓ Troubleshooting tools and auto-fix"
    echo "  ✓ Service management interface"
    echo ""
    
    echo -e "${BLUE}API Endpoints:${NC}"
    echo "  Status:  http://$SERVER_IP:5000/api/status"
    echo "  Config:  http://$SERVER_IP:5000/api/config"
    echo "  Logs:    http://$SERVER_IP:5000/api/logs"
    echo ""
    
    echo -e "${YELLOW}Security Notes:${NC}"
    echo "  • Web dashboard runs on port 5000"
    echo "  • No built-in authentication (add if needed)"
    echo "  • Credentials are masked in the interface"
    echo "  • Consider using nginx reverse proxy for production"
    echo ""
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Open http://$SERVER_IP:5000 in your browser"
    echo "  2. Check system status and configuration"
    echo "  3. Test pipeline control features"
    echo "  4. Review logs and troubleshooting tools"
    echo ""
    
    if command -v nginx &> /dev/null; then
        echo -e "${YELLOW}Optional - Enable Nginx Reverse Proxy:${NC}"
        echo "  sudo ln -s /etc/nginx/sites-available/media-pipeline-web /etc/nginx/sites-enabled/"
        echo "  sudo nginx -t"
        echo "  sudo systemctl reload nginx"
        echo "  Then access via: http://$SERVER_IP (port 80)"
        echo ""
    fi
    
    echo -e "${GREEN}Setup completed successfully!${NC}"
}

main() {
    print_header
    
    check_prerequisites
    install_web_dependencies
    setup_web_files
    install_systemd_service
    configure_firewall
    start_web_service
    test_web_dashboard
    create_nginx_config
    show_completion_info
}

# Run main function
main "$@"