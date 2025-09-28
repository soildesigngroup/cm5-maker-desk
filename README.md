# Raspberry Pi CM5 Maker Desk - HMI Control System

A comprehensive Human-Machine Interface (HMI) control panel designed specifically for the Raspberry Pi CM5. This system provides real-time monitoring and control of industrial IoT devices, storage management, automation, and AI-powered diagnostics.

![HMI Control Panel](https://img.shields.io/badge/Platform-Raspberry%20Pi%20CM5-red?style=for-the-badge&logo=raspberry-pi)
![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-blue?style=for-the-badge&logo=react)
![Python](https://img.shields.io/badge/Backend-Python%20%2B%20Flask-green?style=for-the-badge&logo=python)

## 🚀 Quick Start

### Automated Setup (Recommended)

Clone the repository and run the automated setup script:

```bash
# Clone the repository
git clone https://github.com/soildesigngroup/cm5-maker-desk.git
cd cm5-maker-desk

# Run automated setup (requires sudo for hardware configuration)
sudo ./setup-raspberry-pi.sh

# Reboot to apply hardware interface changes
sudo reboot

# After reboot, test the setup
./test-setup.sh

# Start the HMI system
./start-hmi.sh
```

The web interface will be available at: **http://localhost:5173**

## 🎯 Features

### Core HMI Capabilities
- **Real-time System Monitoring** - CPU, memory, temperature, and storage
- **ADC Monitoring** - Multi-channel analog input with graphing
- **I/O Control** - Digital input/output with real-time status
- **Fan Control** - Intelligent thermal management
- **RTC Display** - Real-time clock with synchronization
- **Storage Management** - Drive formatting, health monitoring, and speed testing

### Advanced Features
- **AI-Vision System** - Computer vision with real-time processing
- **CAN Bus Interface** - Industrial vehicle communication
- **Audio Output Control** - System audio management
- **Automation Engine** - Rule-based device automation
- **DIAG Agent** - AI-powered log analysis and diagnostics

### Hardware Integration
- **ADS7828 ADC** - 8-channel 12-bit analog-to-digital converter
- **PCAL9555A I/O Expander** - 16-bit GPIO expansion
- **PCF85063A RTC** - Real-time clock with battery backup
- **EMC2301 Fan Controller** - PWM fan speed control
- **AT24CM01 EEPROM** - Non-volatile data storage
- **CAN Interface** - MCP2515-based CAN communication

## 📋 System Requirements

### Hardware
- **Raspberry Pi CM5** (Compute Module 5)
- **I2C-enabled carrier board**
- **MicroSD card** (32GB+ recommended)
- **Power supply** (5V/3A minimum)

### Software
- **Raspberry Pi OS** (64-bit, latest)
- **Python 3.9+**
- **Node.js 18+**
- **Hardware interfaces enabled** (I2C, SPI, GPIO)

## 🔧 Manual Setup

If you prefer manual installation or need to troubleshoot:

### 1. Hardware Interface Configuration

Enable required interfaces in `/boot/firmware/config.txt`:

```bash
# Enable I2C for HMI devices
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=400000

# Enable SPI interface
dtparam=spi=on

# Enable GPIO access
dtparam=gpio=on

# Enable CAN interface (if MCP2515 available)
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25

# Enable camera for AI-Vision
dtparam=camera=on

# Optimize memory allocation
gpu_mem=64
```

### 2. System Dependencies

```bash
# Update package repository
sudo apt-get update

# Install system packages
sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
    nodejs npm git i2c-tools can-utils build-essential \
    libffi-dev libssl-dev libudev-dev pkg-config cmake

# Install storage management tools
sudo apt-get install -y lsblk parted util-linux smartmontools hdparm
```

### 3. Python Environment

```bash
# Create virtual environment
python3 -m venv cm5-venv

# Activate environment
source cm5-venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Node.js Dependencies

```bash
# Install frontend dependencies
npm install
```

### 5. User Permissions

```bash
# Add user to hardware access groups
sudo usermod -a -G gpio,i2c,spi,dialout $USER

# Logout and login again for group changes to take effect
```

## 🎮 Usage

### Starting the System

```bash
# Method 1: Use provided startup script
./start-hmi.sh

# Method 2: Manual startup
# Terminal 1 - Start Python API
source cm5-venv/bin/activate
python hmi_json_api.py server

# Terminal 2 - Start React frontend
npm run dev
```

### Web Interface

Navigate to `http://localhost:5173` to access the HMI control panel.

#### Available Tabs:
- **Overview** - System status and key metrics
- **ADC** - Analog input monitoring with real-time graphs
- **I/O** - Digital input/output control
- **Fan** - Thermal management and fan control
- **RTC** - Real-time clock display and settings
- **Storage** - Drive management, formatting, and speed testing
- **CAN** - CAN bus communication and diagnostics
- **Audio** - System audio output control
- **AI-Vision** - Computer vision processing
- **Automation** - Device automation rules
- **DIAG Agent** - System diagnostics and log analysis
- **Settings** - API connection and system configuration

### API Interface

The Python backend provides a JSON API at `http://localhost:8081/api/command`

Example API call:
```bash
curl -X POST http://localhost:8081/api/command \
  -H "Content-Type: application/json" \
  -d '{"action": "get_system_status", "params": {}}'
```

## 🔍 Testing and Troubleshooting

### Run System Tests
```bash
# Test hardware interfaces and setup
./test-setup.sh

# Check I2C devices
sudo i2cdetect -y 1

# Test hardware interfaces
ls -la /dev/i2c-* /dev/spi*
```

### Common Issues

**I2C devices not detected:**
- Verify hardware connections
- Check `/boot/firmware/config.txt` settings
- Ensure proper power supply
- Run `sudo i2cdetect -y 1` to scan for devices

**Permission errors:**
- Verify user is in required groups: `groups $USER`
- Logout and login after adding groups
- Check udev rules: `ls -la /etc/udev/rules.d/*hmi*`

**Storage operations fail:**
- Ensure user has sudo privileges
- Check if drives are mounted: `lsblk`
- Verify storage tools are installed: `which parted mkfs`

**CAN interface issues:**
- Verify MCP2515 hardware connections
- Check oscillator frequency in config.txt
- Test with: `ip link show can0`

## 🏗️ Architecture

### Frontend (React + TypeScript)
- **Component-based UI** with shadcn/ui
- **Real-time data** via WebSocket connections
- **Responsive design** optimized for industrial displays
- **TypeScript** for type safety

### Backend (Python + Flask)
- **RESTful API** for device communication
- **Hardware abstraction** layer for I2C/SPI devices
- **Real-time data streaming** via WebSockets
- **Storage management** with Linux system tools
- **AI integration** for vision and diagnostics

### Hardware Layer
- **I2C bus** for sensor and control devices
- **GPIO** for digital I/O operations
- **CAN bus** for industrial communication
- **Storage interfaces** for drive management

## 📁 Project Structure

```
cm5-maker-desk/
├── src/                          # React frontend source
│   ├── components/               # UI components
│   │   ├── hmi/                 # HMI-specific components
│   │   └── ui/                  # Base UI components
│   ├── services/                # API service layer
│   └── pages/                   # Main application pages
├── hmi_json_api.py              # Python backend API
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies
├── setup-raspberry-pi.sh        # Automated setup script
├── start-hmi.sh                 # System startup script
├── test-setup.sh                # Installation test script
└── README.md                    # This file
```

## 🛠️ Development

### Frontend Development

```bash
# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

### Backend Development

```bash
# Activate Python environment
source cm5-venv/bin/activate

# Run API server in development mode
python hmi_json_api.py server

# Run with debug logging
python hmi_json_api.py server --debug
```

## 🔒 Security

- **Hardware access** requires proper user permissions
- **Storage operations** use sudo with validation
- **API endpoints** include input sanitization
- **File operations** include path validation
- **System commands** use subprocess security practices

## 📊 Performance

### Optimizations
- **I2C speed** configured for 400kHz operation
- **Memory allocation** optimized for embedded systems
- **Database** uses SQLite for minimal overhead
- **Caching** implemented for frequent operations

### Resource Usage
- **RAM**: ~200MB typical usage
- **CPU**: ~15% on idle, ~30% under load
- **Storage**: ~50MB application data
- **Network**: Local interfaces only

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with descriptive messages
5. Push to your fork and create a pull request

## 📄 License

This project is designed for the Raspberry Pi CM5 hardware platform and integrates with various industrial control systems.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Run `./test-setup.sh` to diagnose common problems
3. Review system logs: `journalctl -f`
4. Check hardware connections and power supply

## 🎯 Roadmap

- [ ] **MQTT Integration** - IoT cloud connectivity
- [ ] **Database Export** - Historical data export
- [ ] **Mobile Interface** - Responsive mobile UI
- [ ] **Advanced Automation** - Complex rule engine
- [ ] **Network Configuration** - Remote access setup
- [ ] **Hardware Expansion** - Additional device support

---

**Built for Industrial IoT • Optimized for Raspberry Pi CM5 • Real-time Performance**