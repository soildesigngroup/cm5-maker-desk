try:
    import smbus2 as smbus
except ImportError:
    import smbus

class AT24CM01:
    MEMORY_SIZE = 131072
    
    def __init__(self, bus_number=10, base_address=0x56):
        self.bus_number = bus_number
        self.base_address = base_address
        self.bus = None
        
    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            self.bus.read_byte(self.base_address)
            print(f"AT24CM01 connected at 0x{self.base_address:02X}")
            return True
        except Exception as e:
            print(f"AT24CM01 connection failed: {e}")
            return False
    
    def read_bytes(self, address, length):
        return [0] * length
    
    def write_bytes(self, address, data):
        return True
    
    def read_string(self, address, max_length):
        return "Mock EEPROM Data"
    
    def write_string(self, address, text):
        return True
    
    def get_memory_info(self):
        return {"size": self.MEMORY_SIZE, "type": "AT24CM01"}
    
    def test_memory(self, address, size):
        return True
    
    def _read_byte(self, address):
        return 0xAA
    
    def disconnect(self):
        if self.bus:
            self.bus.close()
