#!/bin/bash
set -e

# Raspberry Pi CM5 HMI System Setup Script
# This script automates the configuration of hardware interfaces and dependencies
# for the CM5 Maker Desk HMI application

echo "🚀 Raspberry Pi CM5 HMI System Setup"
echo "===================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${PURPLE}[SETUP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running on Raspberry Pi
print_header "Checking system compatibility..."
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_error "This script is designed for Raspberry Pi systems only"
    print_error "Current system: $(uname -a)"
    exit 1
fi

print_status "✅ Running on Raspberry Pi system"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    SUDO_CMD=""
    print_status "Running as root"
else
    SUDO_CMD="sudo"
    print_status "Running with sudo privileges"
    # Test sudo access
    if ! sudo -n true 2>/dev/null; then
        print_warning "This script requires sudo privileges"
        print_status "You may be prompted for your password"
    fi
fi

# Get current directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
print_status "Working directory: $SCRIPT_DIR"

# Backup existing config.txt
CONFIG_FILE="/boot/firmware/config.txt"
BACKUP_FILE="/boot/firmware/config.txt.backup-$(date +%Y%m%d-%H%M%S)"

print_header "Backing up existing configuration..."
if [ -f "$CONFIG_FILE" ]; then
    $SUDO_CMD cp "$CONFIG_FILE" "$BACKUP_FILE"
    print_status "✅ Config backup created: $BACKUP_FILE"
else
    print_warning "Config file not found at $CONFIG_FILE"
    # Try alternative location
    CONFIG_FILE="/boot/config.txt"
    if [ -f "$CONFIG_FILE" ]; then
        BACKUP_FILE="/boot/config.txt.backup-$(date +%Y%m%d-%H%M%S)"
        $SUDO_CMD cp "$CONFIG_FILE" "$BACKUP_FILE"
        print_status "✅ Config backup created: $BACKUP_FILE"
    else
        print_error "Cannot find config.txt file"
        exit 1
    fi
fi

# Function to add or update config setting
add_config_setting() {
    local setting="$1"
    local comment="$2"

    if grep -q "^$setting" "$CONFIG_FILE"; then
        print_status "Setting already exists: $setting"
    elif grep -q "^#$setting" "$CONFIG_FILE"; then
        print_status "Enabling existing setting: $setting"
        $SUDO_CMD sed -i "s/^#$setting/$setting/" "$CONFIG_FILE"
    else
        print_status "Adding new setting: $setting"
        echo "" | $SUDO_CMD tee -a "$CONFIG_FILE" > /dev/null
        echo "# $comment" | $SUDO_CMD tee -a "$CONFIG_FILE" > /dev/null
        echo "$setting" | $SUDO_CMD tee -a "$CONFIG_FILE" > /dev/null
    fi
}

# Configure hardware interfaces
print_header "Configuring hardware interfaces in $CONFIG_FILE..."

# Enable I2C (required for ADC, I/O Expander, RTC, Fan Controller, EEPROM)
add_config_setting "dtparam=i2c_arm=on" "Enable I2C interface for HMI devices"

# Enable SPI (may be needed for some configurations)
add_config_setting "dtparam=spi=on" "Enable SPI interface"

# Enable GPIO
add_config_setting "dtparam=gpio=on" "Enable GPIO access"

# Configure I2C speed (optional optimization)
if ! grep -q "dtparam=i2c_arm_baudrate" "$CONFIG_FILE"; then
    add_config_setting "dtparam=i2c_arm_baudrate=400000" "Set I2C speed to 400kHz for better performance"
fi

# Enable CAN interface if supported
add_config_setting "dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25" "Enable CAN interface (if MCP2515 chip is available)"

# GPU memory split (reserve more for system)
add_config_setting "gpu_mem=64" "Reserve minimal GPU memory for headless operation"

# Enable camera interface (for AI-Vision system)
add_config_setting "dtparam=camera=on" "Enable camera interface for AI-Vision"

# Enable hardware watchdog
add_config_setting "dtparam=watchdog=on" "Enable hardware watchdog"

print_success "✅ Hardware interfaces configured"

# Update package repository
print_header "Updating package repository..."
$SUDO_CMD apt-get update -qq

# Install system dependencies
print_header "Installing system dependencies..."

SYSTEM_PACKAGES=(
    "python3"
    "python3-pip"
    "python3-venv"
    "python3-dev"
    "nodejs"
    "npm"
    "git"
    "i2c-tools"
    "can-utils"
    "build-essential"
    "libffi-dev"
    "libssl-dev"
    "libudev-dev"
    "pkg-config"
    "cmake"
)

for package in "${SYSTEM_PACKAGES[@]}"; do
    if dpkg -l | grep -qw "$package"; then
        print_status "✅ $package already installed"
    else
        print_status "Installing $package..."
        $SUDO_CMD apt-get install -y "$package"
    fi
done

# Install additional tools for storage and hardware management
OPTIONAL_PACKAGES=(
    "lsblk"
    "parted"
    "util-linux"
    "smartmontools"
    "hdparm"
)

print_status "Installing storage management tools..."
for package in "${OPTIONAL_PACKAGES[@]}"; do
    if ! command -v "$package" &> /dev/null; then
        $SUDO_CMD apt-get install -y "$package" || print_warning "Failed to install $package"
    fi
done

print_success "✅ System dependencies installed"

# Setup Python virtual environment
print_header "Setting up Python virtual environment..."

VENV_DIR="$SCRIPT_DIR/cm5-venv"
if [ -d "$VENV_DIR" ]; then
    print_status "Virtual environment already exists at $VENV_DIR"
else
    print_status "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    print_success "✅ Virtual environment created"
fi

# Activate virtual environment and install Python dependencies
print_status "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
    print_success "✅ Python dependencies installed from requirements.txt"
else
    print_warning "requirements.txt not found, installing basic dependencies..."
    pip install flask flask-cors smbus2 python-can websockets requests anthropic schedule psutil
fi

deactivate

# Setup Node.js dependencies
print_header "Setting up Node.js dependencies..."

if [ -f "$SCRIPT_DIR/package.json" ]; then
    cd "$SCRIPT_DIR"
    print_status "Installing Node.js dependencies..."
    npm install
    print_success "✅ Node.js dependencies installed"
else
    print_warning "package.json not found, skipping Node.js setup"
fi

# Configure user permissions for hardware access
print_header "Configuring user permissions..."

CURRENT_USER=${SUDO_USER:-$(whoami)}
print_status "Configuring permissions for user: $CURRENT_USER"

# Add user to required groups
USER_GROUPS=("gpio" "i2c" "spi" "dialout")
for group in "${USER_GROUPS[@]}"; do
    if getent group "$group" > /dev/null 2>&1; then
        if groups "$CURRENT_USER" | grep -q "\b$group\b"; then
            print_status "✅ User already in $group group"
        else
            print_status "Adding user to $group group..."
            $SUDO_CMD usermod -a -G "$group" "$CURRENT_USER"
        fi
    else
        print_warning "Group $group does not exist"
    fi
done

# Set up udev rules for hardware access (if needed)
UDEV_RULES_FILE="/etc/udev/rules.d/99-hmi-hardware.rules"
if [ ! -f "$UDEV_RULES_FILE" ]; then
    print_status "Creating udev rules for hardware access..."
    cat << EOF | $SUDO_CMD tee "$UDEV_RULES_FILE" > /dev/null
# HMI Hardware Access Rules
# Allow access to I2C devices
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0664"
# Allow access to SPI devices
SUBSYSTEM=="spidev", GROUP="spi", MODE="0664"
# Allow access to GPIO
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0664"
# Allow access to CAN devices
SUBSYSTEM=="net", KERNEL=="can*", GROUP="dialout", MODE="0664"
EOF
    print_success "✅ Udev rules created"
    $SUDO_CMD udevadm control --reload-rules
else
    print_status "✅ Udev rules already exist"
fi

# Create startup scripts
print_header "Creating startup scripts..."

# Create HMI service startup script
HMI_START_SCRIPT="$SCRIPT_DIR/start-hmi.sh"
cat << EOF > "$HMI_START_SCRIPT"
#!/bin/bash
# HMI System Startup Script

cd "$SCRIPT_DIR"

# Start Python HMI API service
echo "Starting HMI API service..."
source cm5-venv/bin/activate
python hmi_json_api.py server &
HMI_PID=\$!
echo "HMI API service started with PID: \$HMI_PID"

# Start React development server
echo "Starting React development server..."
npm run dev &
REACT_PID=\$!
echo "React development server started with PID: \$REACT_PID"

echo "HMI System started successfully!"
echo "Web interface available at: http://localhost:5173"
echo "API service available at: http://localhost:8081"
echo ""
echo "To stop the services:"
echo "  kill \$HMI_PID \$REACT_PID"

# Wait for user input to stop services
echo "Press Ctrl+C to stop all services..."
trap 'kill \$HMI_PID \$REACT_PID 2>/dev/null; exit' INT
wait
EOF

chmod +x "$HMI_START_SCRIPT"
print_success "✅ Startup script created: $HMI_START_SCRIPT"

# Create test script
TEST_SCRIPT="$SCRIPT_DIR/test-setup.sh"
cat << 'EOF' > "$TEST_SCRIPT"
#!/bin/bash
# HMI System Test Script

echo "🧪 Testing HMI System Setup"
echo "============================"

cd "$(dirname "${BASH_SOURCE[0]}")"

# Test I2C
echo "Testing I2C interface..."
if command -v i2cdetect &> /dev/null; then
    if i2cdetect -l | grep -q i2c; then
        echo "✅ I2C interface detected"
        # Show I2C devices (requires root)
        if [[ $EUID -eq 0 ]]; then
            echo "Scanning I2C bus 1..."
            i2cdetect -y 1 2>/dev/null || echo "⚠️  I2C scan requires root privileges"
        fi
    else
        echo "❌ No I2C interfaces found"
    fi
else
    echo "❌ i2c-tools not installed"
fi

# Test Python environment
echo ""
echo "Testing Python environment..."
if [ -d "cm5-venv" ]; then
    source cm5-venv/bin/activate
    echo "✅ Virtual environment activated"

    # Test Python imports
    python3 -c "
import sys
modules = ['flask', 'smbus2', 'json', 'subprocess']
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module} import successful')
    except ImportError as e:
        print(f'❌ {module} import failed: {e}')
"
    deactivate
else
    echo "❌ Virtual environment not found"
fi

# Test Node.js setup
echo ""
echo "Testing Node.js environment..."
if command -v node &> /dev/null && command -v npm &> /dev/null; then
    echo "✅ Node.js and npm available"
    echo "Node.js version: $(node --version)"
    echo "npm version: $(npm --version)"

    if [ -f "package.json" ]; then
        echo "✅ package.json found"
        if [ -d "node_modules" ]; then
            echo "✅ Node modules installed"
        else
            echo "⚠️  Node modules not installed (run: npm install)"
        fi
    else
        echo "❌ package.json not found"
    fi
else
    echo "❌ Node.js or npm not installed"
fi

# Test hardware interfaces
echo ""
echo "Testing hardware interfaces..."
if [ -c "/dev/i2c-1" ]; then
    echo "✅ I2C device /dev/i2c-1 exists"
else
    echo "❌ I2C device /dev/i2c-1 not found"
fi

if ls /dev/spi* >/dev/null 2>&1; then
    echo "✅ SPI devices found: $(ls /dev/spi*)"
else
    echo "⚠️  No SPI devices found"
fi

if [ -d "/sys/class/gpio" ]; then
    echo "✅ GPIO interface available"
else
    echo "❌ GPIO interface not found"
fi

echo ""
echo "🎉 Test completed!"
echo ""
echo "Next steps:"
echo "1. Reboot the system to apply all configuration changes"
echo "2. Run './start-hmi.sh' to start the HMI system"
echo "3. Access the web interface at http://localhost:5173"
EOF

chmod +x "$TEST_SCRIPT"
print_success "✅ Test script created: $TEST_SCRIPT"

# Final configuration check
print_header "Final system check..."

echo ""
print_success "🎉 Raspberry Pi CM5 HMI System Setup Complete!"
echo "================================================="
echo ""
echo "📋 Configuration Summary:"
echo "  • Hardware interfaces enabled (I2C, SPI, GPIO, CAN)"
echo "  • Python virtual environment created: cm5-venv/"
echo "  • System dependencies installed"
echo "  • User permissions configured"
echo "  • Startup scripts created"
echo ""
echo "📁 Files created:"
echo "  • $HMI_START_SCRIPT - Start HMI system"
echo "  • $TEST_SCRIPT - Test installation"
echo "  • $BACKUP_FILE - Config backup"
echo ""
echo "⚠️  IMPORTANT: A system reboot is required to activate hardware interface changes"
echo ""
echo "🚀 Next steps:"
echo "1. Reboot your system: sudo reboot"
echo "2. After reboot, test the setup: ./test-setup.sh"
echo "3. Start the HMI system: ./start-hmi.sh"
echo "4. Access the web interface at: http://localhost:5173"
echo ""
echo "🔧 Optional NVMe Performance Optimization:"
echo "  • If you have slow NVMe performance, run: sudo ./optimize-nvme.sh"
echo "  • This can improve SSD speeds by up to 10x"
echo "  • Check current PCIe status with: lspci -vvv | grep -A5 NVMe"
echo ""
echo "📖 For troubleshooting, check:"
echo "  • Hardware connections are correct"
echo "  • All required devices are connected"
echo "  • User is in the correct permission groups"
echo ""

# Ask if user wants to reboot now
echo -n "Would you like to reboot now? (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    print_status "Rebooting system..."
    $SUDO_CMD reboot
else
    print_warning "Remember to reboot before using the HMI system!"
fi