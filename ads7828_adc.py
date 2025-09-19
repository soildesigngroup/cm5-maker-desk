try:
    import smbus2 as smbus
except ImportError:
    import smbus
import time

class ADS7828:
    def __init__(self, bus_number=10, address=0x48, vref=3.3):
        self.bus_number = bus_number
        self.address = address
        self.vref = vref
        self.bus = None
        
    def connect(self):
        try:
            self.bus = smbus.SMBus(self.bus_number)
            self.bus.read_byte(self.address)
            print(f"ADS7828 connected at 0x{self.address:02X}")
            return True
        except Exception as e:
            print(f"ADS7828 connection failed: {e}")
            return False
    
    def read_channel(self, channel):
        if self.bus is None:
            return 0
        try:
            cmd = 0x80 | (channel << 4)
            data = self.bus.read_word_data(self.address, cmd)
            raw = ((data & 0xFF) << 8) | ((data >> 8) & 0xFF)
            return raw >> 4
        except Exception as e:
            print(f"Error reading channel {channel}: {e}")
            return 0
    
    def read_channel_voltage(self, channel):
        raw = self.read_channel(channel)
        return (raw / 4095.0) * self.vref
    
    def disconnect(self):
        if self.bus:
            self.bus.close()
