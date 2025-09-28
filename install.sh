#!/bin/bash
set -e

# AI-Powered Log Monitoring Agent Installation Script for Raspberry Pi
# This script sets up the log monitoring agent with proper permissions and systemd service

echo "🚀 Installing AI-Powered Log Monitoring Agent for Raspberry Pi"
echo "=============================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for system service installation
if [[ $EUID -eq 0 ]]; then
    INSTALL_SERVICE=true
    print_status "Running as root - will install systemd service"
else
    INSTALL_SERVICE=false
    print_warning "Not running as root - will skip systemd service installation"
    print_warning "Run with sudo to install as system service"
fi

# Check Python version
print_status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "Python version: $PYTHON_VERSION"

# Check pip3
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed"
    print_status "Installing pip3..."
    apt-get update && apt-get install -y python3-pip
fi

# Create installation directory
INSTALL_DIR="/opt/log-monitor"
CURRENT_DIR=$(pwd)

if [ "$INSTALL_SERVICE" = true ]; then
    print_status "Creating installation directory: $INSTALL_DIR"
    mkdir -p $INSTALL_DIR

    # Copy files to installation directory
    print_status "Copying application files..."
    cp log_monitor.py $INSTALL_DIR/
    cp requirements.txt $INSTALL_DIR/

    # Create data directories
    mkdir -p $INSTALL_DIR/data
    mkdir -p $INSTALL_DIR/logs
    mkdir -p /var/log/log-monitor

    # Set ownership and permissions
    useradd -r -s /bin/false -d $INSTALL_DIR log-monitor || true
    chown -R log-monitor:log-monitor $INSTALL_DIR
    chown -R log-monitor:log-monitor /var/log/log-monitor
    chmod +x $INSTALL_DIR/log_monitor.py

    WORK_DIR=$INSTALL_DIR
    RUN_USER="log-monitor"
else
    print_status "Installing in current directory: $CURRENT_DIR"
    mkdir -p logs data
    WORK_DIR=$CURRENT_DIR
    RUN_USER=$(whoami)
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ "$INSTALL_SERVICE" = true ]; then
    pip3 install -r $WORK_DIR/requirements.txt
else
    pip3 install --user -r requirements.txt
fi

# Create configuration file if it doesn't exist
CONFIG_FILE="$WORK_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    print_status "Creating default configuration..."
    cd $WORK_DIR
    python3 log_monitor.py --once 2>/dev/null || true  # This will create the config file
    print_warning "Configuration file created at $CONFIG_FILE"
    print_warning "Please edit this file and add your Claude API key before starting the service"
fi

# Install systemd service (if running as root)
if [ "$INSTALL_SERVICE" = true ]; then
    print_status "Creating systemd service..."

    cat > /etc/systemd/system/log-monitor.service << EOF
[Unit]
Description=AI-Powered Log Monitoring Agent
Documentation=https://github.com/your-repo/log-monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/log_monitor.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR /var/log/log-monitor
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true

# Resource limits for Raspberry Pi
MemoryLimit=256M
CPUQuota=50%

# Environment
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=log-monitor

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable log-monitor.service

    print_status "Systemd service installed and enabled"
    print_status "Service will start automatically on boot"
fi

# Create logrotate configuration
if [ "$INSTALL_SERVICE" = true ]; then
    print_status "Setting up log rotation..."

    cat > /etc/logrotate.d/log-monitor << EOF
/var/log/log-monitor/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 640 log-monitor log-monitor
    postrotate
        systemctl reload log-monitor.service >/dev/null 2>&1 || true
    endscript
}
EOF

    print_status "Log rotation configured"
fi

# Test installation
print_status "Testing installation..."
cd $WORK_DIR

# Test basic functionality
if python3 log_monitor.py --help &>/dev/null; then
    print_status "✅ Application runs successfully"
else
    print_error "❌ Application failed to run"
    exit 1
fi

# Test configuration loading (this will fail if API key is not set, which is expected)
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from log_monitor import LogMonitoringAgent
    agent = LogMonitoringAgent()
    print('✅ Configuration loaded successfully')
except ValueError as e:
    if 'Claude API key not configured' in str(e):
        print('⚠️  Configuration loaded but API key needs to be set')
    else:
        print(f'❌ Configuration error: {e}')
        sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    sys.exit(1)
"

echo ""
echo "🎉 Installation completed successfully!"
echo "======================================"

if [ "$INSTALL_SERVICE" = true ]; then
    echo "Installation directory: $INSTALL_DIR"
    echo "Configuration file: $CONFIG_FILE"
    echo "Log directory: /var/log/log-monitor"
    echo ""
    echo "Next steps:"
    echo "1. Edit the configuration file: sudo nano $CONFIG_FILE"
    echo "2. Add your Claude API key and configure log file paths"
    echo "3. Start the service: sudo systemctl start log-monitor"
    echo "4. Check service status: sudo systemctl status log-monitor"
    echo "5. View logs: sudo journalctl -u log-monitor -f"
    echo ""
    echo "Service commands:"
    echo "  Start:   sudo systemctl start log-monitor"
    echo "  Stop:    sudo systemctl stop log-monitor"
    echo "  Restart: sudo systemctl restart log-monitor"
    echo "  Status:  sudo systemctl status log-monitor"
    echo "  Logs:    sudo journalctl -u log-monitor -f"
else
    echo "Installation directory: $WORK_DIR"
    echo "Configuration file: $CONFIG_FILE"
    echo ""
    echo "Next steps:"
    echo "1. Edit the configuration file: nano $CONFIG_FILE"
    echo "2. Add your Claude API key and configure log file paths"
    echo "3. Run the agent: python3 log_monitor.py"
    echo ""
    echo "Manual commands:"
    echo "  Run once:      python3 log_monitor.py --once"
    echo "  Daily summary: python3 log_monitor.py --summary"
    echo "  Test email:    python3 log_monitor.py --test-email"
    echo "  Continuous:    python3 log_monitor.py"
fi

echo ""
echo "Configuration tips:"
echo "• Get Claude API key from: https://console.anthropic.com/"
echo "• Common log paths:"
echo "  - Nginx: /var/log/nginx/access.log, /var/log/nginx/error.log"
echo "  - Apache: /var/log/apache2/access.log, /var/log/apache2/error.log"
echo "  - System: /var/log/syslog, /var/log/messages"
echo "• Adjust thresholds based on your application's normal behavior"
echo "• Enable email alerts for critical issues"

# Create a simple test script
cat > $WORK_DIR/test_installation.sh << 'EOF'
#!/bin/bash
echo "🧪 Testing Log Monitor Installation"
echo "=================================="

echo "Testing configuration..."
python3 log_monitor.py --help

echo ""
echo "Testing single analysis run..."
python3 log_monitor.py --once

echo ""
echo "Testing daily summary..."
python3 log_monitor.py --summary

echo ""
echo "✅ Installation test completed"
EOF

chmod +x $WORK_DIR/test_installation.sh

echo ""
echo "💡 Run './test_installation.sh' to test the installation"
echo "📖 Check README.md for detailed usage instructions"

print_status "Installation script completed!"