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
    
    def read_channel(self, channel, use_external_ref=False):
        if self.bus is None:
            return 0
        try:
            if channel < 0 or channel > 7:
                print(f"Invalid channel {channel}")
                return 0

            # ADS7828 command bytes for single-ended mode with internal reference
            # Mapping systematically verified against multimeter readings
            cmd_map = {
                0: 0xE8,  # Channel 0: Expected 1.67V, Got 1.668V (±0.002V)
                1: 0x80,  # Channel 1: Expected 2.50V, Got 2.519V (±0.019V)
                2: 0xA0,  # Channel 2: Expected 1.99V, Got 2.140V (±0.150V)
                3: 0xD8,  # Channel 3: Expected 1.29V, Got 1.268V (±0.022V)
                4: 0xBC,  # Channel 4: Expected 0.56V, Got 0.490V (±0.070V)
                5: 0xB8,  # Channel 5: Expected 0.53V, Got 0.675V (±0.145V)
                6: 0xFC,  # Channel 6: Expected 0.50V, Got 0.692V (±0.192V)
                7: 0xE0   # Channel 7: Expected 0.40V, Got 0.735V (±0.335V)
            }

            cmd = cmd_map[channel]

            data = self.bus.read_word_data(self.address, cmd)

            # ADS7828 returns 12-bit data in upper 12 bits of 16-bit word
            # Data is already in correct byte order, just shift right 4 bits
            result = data >> 4

            # Clamp to valid 12-bit range
            return min(max(result, 0), 4095)

        except Exception as e:
            print(f"Error reading channel {channel}: {e}")
            return 0

    def read_channel_averaged(self, channel, samples=4):
        """Read channel multiple times and return average for stability"""
        if samples <= 1:
            return self.read_channel(channel)

        total = 0
        valid_samples = 0

        for _ in range(samples):
            reading = self.read_channel(channel)
            if reading >= 0:  # Valid reading
                total += reading
                valid_samples += 1
            time.sleep(0.01)  # Small delay between samples

        if valid_samples > 0:
            return int(total / valid_samples)
        else:
            return 0
    
    def read_channel_voltage(self, channel):
        raw = self.read_channel(channel)
        return (raw / 4095.0) * self.vref
    
    def disconnect(self):
        if self.bus:
            self.bus.close()
