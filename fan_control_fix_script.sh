#!/bin/bash

echo "==================== CM5 Fan Control Fix Script ===================="
echo "This script will fix the EMC2301 fan controller to enable actual hardware control"
echo

# Check if we're in the right directory
if [ ! -f "hmi_json_api.py" ]; then
    echo "Error: Please run this script from the cm5-maker-desk directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Warning: Virtual environment not active. Activating..."
    source cm5-venv/bin/activate
fi

echo "Step 1: Installing required I2C tools..."
sudo apt-get update -qq
sudo apt-get install -y i2c-tools

echo
echo "Step 2: Testing I2C connection to EMC2301..."
echo "Scanning I2C bus 10 for devices..."
sudo i2cdetect -y 10

echo
echo "Step 3: Creating updated EMC2301 driver with real hardware control..."

# Create the updated EMC2301 driver
cat > emc2301_fan_controller.py << 'EOF'
try:
    import smbus2 as smbus
except ImportError:
    import smbus
import time

class EMC2301:
    """
    EMC2301 Fan Controller Driver
    Supports PWM fan control via I2C
    """
    
    # EMC2301 Register addresses
    REG_FAN_SETTING = 0x30      # Fan Speed Setting Register
    REG_PWM_DIVIDE = 0x31       # PWM Divide Register  
    REG_FAN_CONFIG1 = 0x32      # Fan Configuration Register 1
    REG_FAN_CONFIG2 = 0x33      # Fan Configuration Register 2
    REG_GAIN = 0x35             # Gain Register
    REG_FAN_SPIN_UP = 0x36      # Fan Spin Up Configuration
    REG_TACH_COUNT = 0x3E       # Tachometer Count Register
    REG_TACH_LIMIT_LSB = 0x38   # Tachometer Limit LSB
    REG_TACH_LIMIT_MSB = 0x39   # Tachometer Limit MSB
    
    def __init__(self, bus_number=10, address=0x2F):
        self.bus_number = bus_number
        self.address = address
        self.bus = None
        self.initialized = False
        
    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            # Test connection by reading a register
            test_read = self.bus.read_byte_data(self.address, self.REG_FAN_SETTING)
            print(f"EMC2301 connected at 0x{self.address:02X} (current setting: {test_read})")
            
            # Initialize the fan controller
            self._initialize()
            return True
            
        except Exception as e:
            print(f"EMC2301 connection failed: {e}")
            return False
    
    def _initialize(self):
        """Initialize EMC2301 for PWM control"""
        try:
            # Configure for PWM mode
            # Set PWM frequency divider (lower value = higher frequency)
            self.bus.write_byte_data(self.address, self.REG_PWM_DIVIDE, 0x01)
            
            # Configure Fan Config 1: Enable PWM mode, disable RPM mode
            self.bus.write_byte_data(self.address, self.REG_FAN_CONFIG1, 0x2B)
            
            # Configure Fan Config 2: Set edge rate and other timing
            self.bus.write_byte_data(self.address, self.REG_FAN_CONFIG2, 0x00)
            
            # Set reasonable gain
            self.bus.write_byte_data(self.address, self.REG_GAIN, 0x01)
            
            print("EMC2301 initialized for PWM control")
            self.initialized = True
            
        except Exception as e:
            print(f"EMC2301 initialization failed: {e}")
            self.initialized = False
    
    def set_pwm_duty_cycle(self, duty):
        """Set PWM duty cycle (0-100%)"""
        if self.bus is None:
            print("ERROR: EMC2301 not connected")
            return False
            
        if not self.initialized:
            print("WARNING: EMC2301 not properly initialized")
            
        try:
            # Clamp duty cycle to valid range
            duty = max(0, min(100, duty))
            
            # Convert percentage to 8-bit value (0-255)
            # EMC2301 uses 0xFF for 100% duty cycle
            pwm_value = int((duty / 100.0) * 255)
            
            print(f"Setting fan PWM to {duty}% (register value: 0x{pwm_value:02X})")
            
            # Write to Fan Speed Setting register
            self.bus.write_byte_data(self.address, self.REG_FAN_SETTING, pwm_value)
            
            # Verify the write
            readback = self.bus.read_byte_data(self.address, self.REG_FAN_SETTING)
            if readback == pwm_value:
                print(f"SUCCESS: PWM set to {duty}% (verified: 0x{readback:02X})")
                return True
            else:
                print(f"WARNING: PWM write verification failed. Expected: 0x{pwm_value:02X}, Got: 0x{readback:02X}")
                return False
                
        except Exception as e:
            print(f"Failed to set PWM duty cycle: {e}")
            return False
    
    def set_fan_target_rpm(self, rpm):
        """Set target RPM (requires RPM mode configuration)"""
        print(f"DEBUG: set_fan_target_rpm called with rpm={rpm}")
        # Note: RPM mode requires more complex setup with tachometer feedback
        # For now, convert RPM to approximate PWM percentage
        # This is a rough approximation - actual RPM will vary by fan
        if rpm <= 0:
            pwm_percent = 0
        elif rpm >= 3000:
            pwm_percent = 100
        else:
            pwm_percent = (rpm / 3000.0) * 100
            
        return self.set_pwm_duty_cycle(pwm_percent)
    
    def read_fan_rpm(self):
        """Read current fan RPM from tachometer"""
        if self.bus is None:
            return None
            
        try:
            # Read tachometer count (16-bit value)
            tach_lsb = self.bus.read_byte_data(self.address, self.REG_TACH_COUNT)
            tach_msb = self.bus.read_byte_data(self.address, self.REG_TACH_COUNT + 1)
            tach_count = (tach_msb << 8) | tach_lsb
            
            # Convert tachometer count to RPM
            # Formula varies by fan and configuration
            # This is a generic approximation
            if tach_count > 0:
                rpm = int(5000000 / tach_count)  # Approximate conversion
            else:
                rpm = 0
                
            print(f"DEBUG: Tachometer count: {tach_count}, Calculated RPM: {rpm}")
            return rpm
            
        except Exception as e:
            print(f"Failed to read fan RPM: {e}")
            return None
    
    def get_pwm_duty_cycle(self):
        """Get current PWM duty cycle"""
        if self.bus is None:
            return None
            
        try:
            pwm_value = self.bus.read_byte_data(self.address, self.REG_FAN_SETTING)
            duty_percent = (pwm_value / 255.0) * 100
            print(f"DEBUG: Current PWM register: 0x{pwm_value:02X} ({duty_percent:.1f}%)")
            return duty_percent
            
        except Exception as e:
            print(f"Failed to read PWM duty cycle: {e}")
            return None
    
    def get_fan_status(self):
        """Get comprehensive fan status"""
        status = {
            "connected": self.bus is not None,
            "initialized": self.initialized,
            "pwm_duty": self.get_pwm_duty_cycle(),
            "rpm": self.read_fan_rpm()
        }
        
        try:
            if self.bus:
                # Read configuration registers for debugging
                config1 = self.bus.read_byte_data(self.address, self.REG_FAN_CONFIG1)
                config2 = self.bus.read_byte_data(self.address, self.REG_FAN_CONFIG2)
                status["config1"] = f"0x{config1:02X}"
                status["config2"] = f"0x{config2:02X}"
                
        except Exception as e:
            status["config_error"] = str(e)
            
        return status
    
    def configure_fan(self, enable_rpm_control=True, poles=2, edges=1):
        """Configure fan parameters"""
        print(f"DEBUG: configure_fan called - rpm_control={enable_rpm_control}, poles={poles}, edges={edges}")
        
        # For now, just reinitialize with PWM mode
        if self.bus:
            self._initialize()
            
        return True
    
    def test_fan_control(self):
        """Test function to verify fan control is working"""
        print("\n=== EMC2301 Fan Control Test ===")
        
        if not self.bus:
            print("ERROR: Fan controller not connected")
            return False
            
        try:
            # Test sequence: 100% -> 50% -> 25% -> 75% -> 100%
            test_speeds = [100, 50, 25, 75, 100]
            
            for speed in test_speeds:
                print(f"\nSetting fan to {speed}%...")
                success = self.set_pwm_duty_cycle(speed)
                
                if success:
                    time.sleep(2)  # Wait for fan to respond
                    current_duty = self.get_pwm_duty_cycle()
                    print(f"Current duty cycle: {current_duty:.1f}%")
                else:
                    print(f"FAILED to set speed to {speed}%")
                    return False
                    
            print("\n=== Fan Control Test Complete ===")
            return True
            
        except Exception as e:
            print(f"Fan control test failed: {e}")
            return False
    
    def disconnect(self):
        if self.bus:
            try:
                # Set fan to a safe speed before disconnecting
                self.set_pwm_duty_cycle(50)
                self.bus.close()
                print("EMC2301 disconnected")
            except:
                pass
EOF

echo "Step 4: Creating diagnostic script..."

# Create a diagnostic script
cat > test_fan_control.py << 'EOF'
#!/usr/bin/env python3
"""
EMC2301 Fan Controller Test Script
"""

import sys
import time
from emc2301_fan_controller import EMC2301

def main():
    print("=== EMC2301 Fan Controller Diagnostic ===")
    
    # Create fan controller instance
    fan = EMC2301(bus_number=10, address=0x2F)
    
    # Connect to the fan controller
    if not fan.connect():
        print("FAILED: Could not connect to EMC2301")
        sys.exit(1)
    
    # Get initial status
    print("\nInitial Status:")
    status = fan.get_fan_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Run fan control test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        fan.test_fan_control()
    
    # Manual speed control
    elif len(sys.argv) > 1:
        try:
            speed = int(sys.argv[1])
            print(f"\nSetting fan speed to {speed}%")
            fan.set_pwm_duty_cycle(speed)
            
            time.sleep(1)
            final_status = fan.get_fan_status()
            print(f"Final PWM duty: {final_status.get('pwm_duty', 'Unknown'):.1f}%")
            
        except ValueError:
            print("Usage: python3 test_fan_control.py [speed_percentage|test]")
    
    else:
        print("\nUsage:")
        print("  python3 test_fan_control.py test     # Run full test sequence")
        print("  python3 test_fan_control.py 50      # Set fan to 50%")
    
    fan.disconnect()

if __name__ == "__main__":
    main()
EOF

chmod +x test_fan_control.py

echo
echo "Step 5: Testing I2C communication directly..."

echo "Reading current fan setting register:"
sudo i2cget -y 10 0x2F 0x30 2>/dev/null || echo "Could not read fan register - check wiring"

echo
echo "Step 6: Running Python fan test..."
python3 test_fan_control.py

echo
echo "==================== Fix Complete ===================="
echo
echo "Next steps:"
echo "1. Test fan control with: python3 test_fan_control.py test"
echo "2. Set specific speed with: python3 test_fan_control.py 75"
echo "3. Restart your API server: python3 hmi_json_api.py server"
echo "4. Test fan control from the web UI"
echo
echo "If fan still doesn't respond:"
echo "- Check physical wiring between EMC2301 and fan"
echo "- Verify fan requires PWM control (not just 12V)"
echo "- Check EMC2301 datasheet for your specific model"
echo
echo "Debug commands:"
echo "- Direct I2C test: sudo i2cset -y 10 0x2F 0x30 128  # Set 50%"
echo "- Read register: sudo i2cget -y 10 0x2F 0x30        # Read current setting"