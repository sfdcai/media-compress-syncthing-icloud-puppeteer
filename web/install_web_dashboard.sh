#!/bin/bash
# Install Media Pipeline Web Dashboard

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
    echo "Media Pipeline Web Dashboard Installation"
    echo "=========================================="
    echo -e "${NC}"
}

check_requirements() {
    print_status "INFO" "Checking requirements..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root"
        exit 1
    fi
    
    # Check if media-pipeline user exists
    if ! id "$USER_NAME" &>/dev/null; then
        print_status "ERROR" "User $USER_NAME does not exist. Please run the main installation first."
        exit 1
    fi
    
    # Check if pipeline directory exists
    if [[ ! -d "$PIPELINE_DIR" ]]; then
        print_status "ERROR" "Pipeline directory $PIPELINE_DIR does not exist"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$PIPELINE_DIR/venv" ]]; then
        print_status "ERROR" "Virtual environment not found. Please run the main installation first."
        exit 1
    fi
    
    print_status "OK" "Requirements check passed"
}

install_dependencies() {
    print_status "INFO" "Installing Python dependencies..."
    
    # Install Flask and Flask-CORS
    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install flask flask-cors requests
    
    print_status "OK" "Python dependencies installed"
}

setup_web_directory() {
    print_status "INFO" "Setting up web directory..."
    
    # Create web directory if it doesn't exist
    mkdir -p "$WEB_DIR"
    
    # Copy web files
    cp -r web/* "$WEB_DIR/"
    
    # Set ownership
    chown -R "$USER_NAME:$USER_NAME" "$WEB_DIR"
    
    # Set permissions
    chmod -R 755 "$WEB_DIR"
    chmod +x "$WEB_DIR/server.py"
    
    print_status "OK" "Web directory setup completed"
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
    fi
}

start_service() {
    print_status "INFO" "Starting web dashboard service..."
    
    # Start the service
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for startup
    sleep 3
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "OK" "Web dashboard service started successfully"
    else
        print_status "ERROR" "Failed to start web dashboard service"
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

show_completion_info() {
    echo -e "${GREEN}"
    echo "=========================================="
    echo "Installation Completed Successfully!"
    echo "=========================================="
    echo -e "${NC}"
    
    echo -e "${BLUE}Web Dashboard Access:${NC}"
    echo "  URL: http://$(hostname -I | awk '{print $1}'):5000"
    echo "  Local: http://localhost:5000"
    echo ""
    
    echo -e "${BLUE}Service Management:${NC}"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    
    echo -e "${BLUE}Features:${NC}"
    echo "  ✓ System status monitoring"
    echo "  ✓ Pipeline control and execution"
    echo "  ✓ Configuration management"
    echo "  ✓ Log viewing"
    echo "  ✓ Troubleshooting tools"
    echo "  ✓ Service management"
    echo ""
    
    echo -e "${YELLOW}Note:${NC} The web dashboard runs on port 5000. Make sure this port is accessible from your network if you want to access it remotely."
}

main() {
    print_header
    
    check_requirements
    install_dependencies
    setup_web_directory
    install_systemd_service
    configure_firewall
    start_service
    show_completion_info
}

# Run main function
main "$@"