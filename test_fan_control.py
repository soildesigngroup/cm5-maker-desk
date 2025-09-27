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
