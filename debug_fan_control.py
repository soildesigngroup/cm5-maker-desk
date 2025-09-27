#!/usr/bin/env python3
"""
Advanced EMC2301 Fan Controller Debugging Script
This script tests different configurations to get the fan working
"""

try:
    import smbus2 as smbus
except ImportError:
    import smbus
import time
import sys

class EMC2301Debug:
    # EMC2301 Register addresses
    REG_FAN_SETTING = 0x30      # Fan Speed Setting Register
    REG_PWM_DIVIDE = 0x31       # PWM Divide Register
    REG_FAN_CONFIG1 = 0x32      # Fan Configuration Register 1
    REG_FAN_CONFIG2 = 0x33      # Fan Configuration Register 2
    REG_GAIN = 0x35             # Gain Register
    REG_FAN_SPIN_UP = 0x36      # Fan Spin Up Configuration
    REG_TACH_COUNT = 0x3E       # Tachometer Count Register
    REG_PRODUCT_ID = 0xFD       # Product ID Register
    REG_MANUFACTURER_ID = 0xFE  # Manufacturer ID Register
    REG_REVISION = 0xFF         # Revision Register

    def __init__(self, bus_number=10, address=0x2F):
        self.bus_number = bus_number
        self.address = address
        self.bus = None

    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            # Test connection
            product_id = self.bus.read_byte_data(self.address, self.REG_PRODUCT_ID)
            mfg_id = self.bus.read_byte_data(self.address, self.REG_MANUFACTURER_ID)
            revision = self.bus.read_byte_data(self.address, self.REG_REVISION)

            print(f"EMC2301 connected:")
            print(f"  Product ID: 0x{product_id:02X}")
            print(f"  Manufacturer ID: 0x{mfg_id:02X}")
            print(f"  Revision: 0x{revision:02X}")
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def read_register(self, reg):
        """Read a single register"""
        try:
            return self.bus.read_byte_data(self.address, reg)
        except Exception as e:
            print(f"Failed to read register 0x{reg:02X}: {e}")
            return None

    def write_register(self, reg, value):
        """Write a single register and verify"""
        try:
            self.bus.write_byte_data(self.address, reg, value)
            readback = self.bus.read_byte_data(self.address, reg)
            if readback == value:
                print(f"  ✓ Register 0x{reg:02X} = 0x{value:02X} (verified)")
                return True
            else:
                print(f"  ✗ Register 0x{reg:02X} write failed. Expected 0x{value:02X}, got 0x{readback:02X}")
                return False
        except Exception as e:
            print(f"  ✗ Failed to write register 0x{reg:02X}: {e}")
            return False

    def dump_key_registers(self):
        """Dump key registers for debugging"""
        print("\nKey Register Status:")
        key_regs = {
            0x30: "Fan Speed Setting",
            0x31: "PWM Divide",
            0x32: "Fan Config 1",
            0x33: "Fan Config 2",
            0x35: "Gain",
            0x36: "Fan Spin Up",
            0x3E: "Tach Count LSB",
            0x3F: "Tach Count MSB"
        }

        for reg, name in key_regs.items():
            value = self.read_register(reg)
            if value is not None:
                print(f"  0x{reg:02X} ({name:15s}): 0x{value:02X} ({value:3d})")

    def test_configuration_1(self):
        """Test Configuration 1: Basic PWM mode"""
        print("\n=== Testing Configuration 1: Basic PWM ===")

        # Reset configuration
        self.write_register(self.REG_PWM_DIVIDE, 0x00)    # No PWM divide
        self.write_register(self.REG_FAN_CONFIG1, 0x80)   # Enable fan, PWM mode
        self.write_register(self.REG_FAN_CONFIG2, 0x00)   # Default settings
        self.write_register(self.REG_GAIN, 0x01)          # Low gain
        self.write_register(self.REG_FAN_SPIN_UP, 0x00)   # No spin up delay

        # Test PWM sequence
        test_values = [0x00, 0x40, 0x80, 0xC0, 0xFF, 0x80]
        for i, pwm_val in enumerate(test_values):
            print(f"\nStep {i+1}: Setting PWM to 0x{pwm_val:02X} ({pwm_val/255*100:.1f}%)")
            self.write_register(self.REG_FAN_SETTING, pwm_val)

            # Wait and check tachometer
            time.sleep(3)
            tach_lsb = self.read_register(self.REG_TACH_COUNT)
            tach_msb = self.read_register(self.REG_TACH_COUNT + 1)
            if tach_lsb is not None and tach_msb is not None:
                tach_count = (tach_msb << 8) | tach_lsb
                print(f"  Tachometer reading: {tach_count}")

            input("  Press Enter to continue to next setting...")

    def test_configuration_2(self):
        """Test Configuration 2: Different PWM frequency"""
        print("\n=== Testing Configuration 2: Different PWM Frequency ===")

        # Try different PWM frequencies
        pwm_dividers = [0x00, 0x01, 0x02, 0x04, 0x08]

        for divider in pwm_dividers:
            print(f"\nTesting PWM divider: 0x{divider:02X}")
            self.write_register(self.REG_PWM_DIVIDE, divider)
            self.write_register(self.REG_FAN_CONFIG1, 0x80)   # Enable fan, PWM mode
            self.write_register(self.REG_FAN_CONFIG2, 0x00)

            # Set to 75% PWM
            self.write_register(self.REG_FAN_SETTING, 0xC0)
            time.sleep(2)

            # Check if fan responds
            print(f"  Set PWM to 75% with divider 0x{divider:02X}")
            print(f"  Listen for fan speed change...")
            input("  Press Enter for next frequency...")

    def test_configuration_3(self):
        """Test Configuration 3: Force PWM output enable"""
        print("\n=== Testing Configuration 3: Force PWM Enable ===")

        # Different Config1 settings to try
        config1_values = [
            (0x80, "Basic PWM enable"),
            (0x88, "PWM + Output enable"),
            (0x8C, "PWM + Different output mode"),
            (0x90, "Alternative PWM mode"),
            (0xA0, "PWM with different base"),
            (0x2B, "Original setting from script")
        ]

        for config_val, description in config1_values:
            print(f"\nTesting Config1: 0x{config_val:02X} ({description})")

            # Apply configuration
            self.write_register(self.REG_PWM_DIVIDE, 0x01)
            self.write_register(self.REG_FAN_CONFIG1, config_val)
            self.write_register(self.REG_FAN_CONFIG2, 0x00)
            self.write_register(self.REG_GAIN, 0x01)

            # Test with 50% PWM
            self.write_register(self.REG_FAN_SETTING, 0x80)
            time.sleep(2)

            print(f"  Applied config, set to 50% PWM")

            # Now test 100%
            self.write_register(self.REG_FAN_SETTING, 0xFF)
            time.sleep(2)
            print(f"  Now at 100% PWM")

            # Back to 0%
            self.write_register(self.REG_FAN_SETTING, 0x00)
            time.sleep(2)
            print(f"  Now at 0% PWM")

            response = input("  Did you hear the fan change? (y/n/q): ").lower()
            if response == 'q':
                break
            elif response == 'y':
                print(f"  *** SUCCESS: Configuration 0x{config_val:02X} works! ***")
                return config_val

        return None

    def test_rpm_mode(self):
        """Test RPM-based control mode"""
        print("\n=== Testing RPM Mode ===")

        # Configure for RPM mode
        self.write_register(self.REG_PWM_DIVIDE, 0x01)
        self.write_register(self.REG_FAN_CONFIG1, 0x2B)   # RPM mode
        self.write_register(self.REG_FAN_CONFIG2, 0x00)
        self.write_register(self.REG_GAIN, 0x01)

        # Set target RPM (this is more complex and may not work without proper setup)
        print("RPM mode requires more complex setup - skipping for now")

    def interactive_test(self):
        """Interactive testing mode"""
        print("\n=== Interactive Test Mode ===")
        print("You can manually set PWM values and observe the fan")

        while True:
            try:
                user_input = input("\nEnter PWM value (0-255) or 'q' to quit: ").strip()
                if user_input.lower() == 'q':
                    break

                pwm_value = int(user_input)
                if 0 <= pwm_value <= 255:
                    print(f"Setting PWM to {pwm_value} ({pwm_value/255*100:.1f}%)")
                    self.write_register(self.REG_FAN_SETTING, pwm_value)
                    self.dump_key_registers()
                else:
                    print("Value must be 0-255")

            except ValueError:
                print("Invalid input")
            except KeyboardInterrupt:
                break

    def disconnect(self):
        if self.bus:
            # Set to safe PWM level
            self.write_register(self.REG_FAN_SETTING, 0x80)  # 50%
            self.bus.close()

def main():
    print("EMC2301 Advanced Fan Controller Debug Tool")
    print("=" * 50)

    fan = EMC2301Debug()

    if not fan.connect():
        print("Failed to connect to EMC2301")
        sys.exit(1)

    fan.dump_key_registers()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == 'config1':
            fan.test_configuration_1()
        elif mode == 'config2':
            fan.test_configuration_2()
        elif mode == 'config3':
            working_config = fan.test_configuration_3()
            if working_config:
                print(f"\n*** Working configuration found: 0x{working_config:02X} ***")
        elif mode == 'rpm':
            fan.test_rpm_mode()
        elif mode == 'interactive':
            fan.interactive_test()
        else:
            print(f"Unknown mode: {mode}")
    else:
        print("\nUsage:")
        print("  python3 debug_fan_control.py config1      # Test basic PWM config")
        print("  python3 debug_fan_control.py config2      # Test different PWM frequencies")
        print("  python3 debug_fan_control.py config3      # Test different config registers")
        print("  python3 debug_fan_control.py interactive  # Manual PWM testing")
        print("\nRunning all tests...")

        # Run all tests
        fan.test_configuration_1()
        fan.test_configuration_2()
        working_config = fan.test_configuration_3()

        if working_config:
            print(f"\n*** Working configuration found: 0x{working_config:02X} ***")
            print("Update your EMC2301 driver to use this configuration!")

    fan.disconnect()

if __name__ == "__main__":
    main()