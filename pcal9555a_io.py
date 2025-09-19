try:
    import smbus2 as smbus
except ImportError:
    import smbus

class PCAL9555A:
    def __init__(self, bus_number=10, address=0x24):
        self.bus_number = bus_number
        self.address = address
        self.bus = None
        
    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            self.bus.read_byte(self.address)
            print(f"PCAL9555A connected at 0x{self.address:02X}")
            return True
        except Exception as e:
            print(f"PCAL9555A connection failed: {e}")
            return False
    
    def read_pin(self, pin):
        return 0
    
    def write_pin(self, pin, state):
        return True
    
    def configure_pin(self, pin, direction, pullup=True):
        return True
    
    def get_pin_info(self, pin):
        return {"direction": "input", "pullup": True}
    
    def reset_to_defaults(self):
        return True
    
    def disconnect(self):
        if self.bus:
            self.bus.close()
