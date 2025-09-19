try:
    import smbus2 as smbus
except ImportError:
    import smbus

class EMC2301:
    def __init__(self, bus_number=10, address=0x2F):
        self.bus_number = bus_number
        self.address = address
        self.bus = None
        
    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            self.bus.read_byte(self.address)
            print(f"EMC2301 connected at 0x{self.address:02X}")
            return True
        except Exception as e:
            print(f"EMC2301 connection failed: {e}")
            return False
    
    def set_pwm_duty_cycle(self, duty):
        return True
    
    def set_fan_target_rpm(self, rpm):
        return True
    
    def read_fan_rpm(self):
        return 1200
    
    def get_pwm_duty_cycle(self):
        return 50.0
    
    def get_fan_status(self):
        return {"status": "running"}
    
    def configure_fan(self, enable_rpm_control=True, poles=2, edges=1):
        return True
    
    def disconnect(self):
        if self.bus:
            self.bus.close()
