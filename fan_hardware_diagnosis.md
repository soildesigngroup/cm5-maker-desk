# Fan Control Hardware Diagnosis

## Issue Summary
The EMC2301 fan controller chip is functioning correctly (all I2C communication works), but the physical fan does not respond to PWM control signals.

## Software Status ✅
- EMC2301 I2C communication: **WORKING**
- Register writes and reads: **WORKING**
- API endpoints: **WORKING**
- UI controls: **WORKING**
- PWM signal generation: **WORKING** (registers update correctly)

## Hardware Issues to Check 🔧

### 1. Check Fan Type
**Most likely issue**: Your fan may not support PWM control.

**Fan Types:**
- **2-wire fan**: Only +12V and GND (constant speed, no PWM control)
- **3-wire fan**: +12V, GND, and tachometer (speed sensing, limited PWM)
- **4-wire fan**: +12V, GND, tachometer, and PWM control (full PWM support)

**How to check:**
1. Count the wires going to your fan
2. Look at the fan label/model number
3. Check if there's a separate PWM wire (usually blue or yellow)

### 2. Check Physical Connections

**EMC2301 Connections to verify:**
- Pin 1 (PWM1): Should connect to fan PWM input
- Pin 2 (TACH1): Should connect to fan tachometer output
- Pin 3 (VDD): 3.3V power
- Pin 4 (GND): Ground
- Pin 5 (SDA): I2C data
- Pin 6 (SCL): I2C clock

**Fan Connections to verify:**
- Red wire: +12V power (not from EMC2301)
- Black wire: Ground
- Yellow/Blue wire: PWM control (should go to EMC2301 pin 1)
- Green/White wire: Tachometer (should go to EMC2301 pin 2)

### 3. Power Supply Check

**Fan Power Requirements:**
- Most PC fans need 12V power supply
- PWM signal is typically 5V or 3.3V logic level
- Fan power should come from main 12V supply, NOT from EMC2301

**Verify:**
1. Fan gets proper 12V power supply
2. EMC2301 only provides PWM signal, not main power
3. Check voltage levels with multimeter

## Quick Hardware Tests

### Test 1: Fan Power Test
```bash
# Disconnect PWM signal, connect fan directly to 12V
# Fan should run at full speed constantly
```

### Test 2: PWM Signal Test
```bash
# Use oscilloscope or logic analyzer to verify PWM output from EMC2301 pin 1
# Should see 25kHz PWM signal with varying duty cycle
```

### Test 3: Bypass EMC2301
```bash
# Connect fan PWM directly to 3.3V (should run full speed)
# Connect fan PWM directly to GND (should stop)
```

## Software Debugging Commands

### Check Current Status
```bash
python3 test_fan_control.py
sudo i2cget -y 10 0x2F 0x30  # Read current PWM setting
sudo i2cdump -y 10 0x2F      # Dump all registers
```

### Manual PWM Control
```bash
# Set PWM to 0% (should stop fan if working)
sudo i2cset -y 10 0x2F 0x30 0x00

# Set PWM to 100% (should max fan if working)
sudo i2cset -y 10 0x2F 0x30 0xFF
```

## Solutions Based on Fan Type

### If you have a 2-wire fan:
- **Problem**: No PWM control possible
- **Solution**: Replace with 4-wire PWM fan, or use relay control

### If you have a 3-wire fan:
- **Problem**: Limited PWM support
- **Solution**: May work with voltage regulation instead of PWM

### If you have a 4-wire fan:
- **Problem**: Wiring or configuration issue
- **Solution**: Check connections and power supply

## Recommended Next Steps

1. **Identify your fan type** (check wires and model number)
2. **Verify physical connections** (especially PWM wire)
3. **Check 12V power supply** to the fan
4. **Test fan directly** with 12V power (bypass EMC2301)

## Quick Fix Options

### Option A: Replace Fan
Get a confirmed 4-wire PWM fan like:
- Noctua NF-A4x20 PWM
- Sunon MF25060V1-1000U-A99
- Any fan labeled "PWM" or "4-wire"

### Option B: Relay Control
If fan doesn't support PWM, use a relay to turn it on/off:
- Use GPIO pin to control relay
- Relay switches 12V power to fan
- Less precise but functional

### Option C: Voltage Regulation
Use a MOSFET or voltage regulator:
- Convert PWM to variable voltage
- Control fan speed via voltage instead of PWM

## Hardware Verification Checklist

- [ ] Fan type confirmed (2/3/4 wire)
- [ ] PWM wire connected to EMC2301 pin 1
- [ ] Tachometer wire connected to EMC2301 pin 2
- [ ] Fan has separate 12V power supply
- [ ] Ground connections verified
- [ ] EMC2301 I2C connections working
- [ ] PWM signal measured with scope/meter

**If all hardware is correct and fan still doesn't respond, the fan likely doesn't support PWM control.**