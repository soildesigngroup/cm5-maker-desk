#!/usr/bin/env python3
"""
HMI JSON API Library
Unified JSON interface for all HMI devices:
- ADS7828 ADC
- PCAL9555A I/O Expander  
- PCF85063A RTC
- EMC2301 Fan Controller
- AT24CM01 EEPROM
"""

import json
import time
import threading
import queue
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import uuid

# Import device classes (assumes they're available)
try:
    from ads7828_adc import ADS7828
    from pcal9555a_io import PCAL9555A
    from pcf85063a_rtc import PCF85063A
    from emc2301_fan_controller import EMC2301
    from at24cm01_eeprom import AT24CM01
except ImportError as e:
    print(f"Warning: Some device modules not available: {e}")

@dataclass
class DeviceStatus:
    """Standard device status structure"""
    device_type: str
    device_id: str
    connected: bool
    last_update: float
    error_message: Optional[str] = None
    capabilities: List[str] = None

@dataclass
class APIResponse:
    """Standard API response structure"""
    success: bool
    timestamp: float
    request_id: Optional[str] = None
    data: Optional[Dict] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None

class HMIJsonAPI:
    """
    Unified JSON API for all HMI devices
    Provides standardized JSON-based interface for GUI applications
    """
    
    def __init__(self, bus_number=10, auto_connect=True):
        """
        Initialize HMI JSON API
        
        Args:
            bus_number (int): I2C bus number
            auto_connect (bool): Automatically connect to devices on init
        """
        self.bus_number = bus_number
        
        # Device instances
        self.devices = {}
        self.device_configs = {
            'adc': {'class': ADS7828, 'address': 0x48, 'vref': 3.3},
            'io': {'class': PCAL9555A, 'address': 0x24},
            'rtc': {'class': PCF85063A, 'address': 0x51},
            'fan': {'class': EMC2301, 'address': 0x2F},
            'eeprom': {'class': AT24CM01, 'base_address': 0x56}
        }
        
        # API state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 1.0
        self.data_queue = queue.Queue(maxsize=1000)
        self.callbacks = {}  # Event callbacks
        
        # Device status tracking
        self.device_status = {}
        
        # Initialize devices if requested
        if auto_connect:
            self.initialize_devices()
    
    def initialize_devices(self) -> Dict[str, bool]:
        """
        Initialize and connect to all available devices
        
        Returns:
            Dict[str, bool]: Connection status for each device
        """
        connection_results = {}
        
        for device_id, config in self.device_configs.items():
            try:
                device_class = config['class']
                
                # Create device instance with appropriate parameters
                if device_id == 'adc':
                    device = device_class(
                        bus_number=self.bus_number,
                        address=config['address'],
                        vref=config['vref']
                    )
                elif device_id == 'eeprom':
                    device = device_class(
                        bus_number=self.bus_number,
                        base_address=config['base_address']
                    )
                else:
                    device = device_class(
                        bus_number=self.bus_number,
                        address=config['address']
                    )
                
                # Attempt connection
                connected = device.connect()
                
                if connected:
                    self.devices[device_id] = device
                    self.device_status[device_id] = DeviceStatus(
                        device_type=device_class.__name__,
                        device_id=device_id,
                        connected=True,
                        last_update=time.time(),
                        capabilities=self._get_device_capabilities(device_id)
                    )
                    connection_results[device_id] = True
                else:
                    connection_results[device_id] = False
                    self.device_status[device_id] = DeviceStatus(
                        device_type=device_class.__name__,
                        device_id=device_id,
                        connected=False,
                        last_update=time.time(),
                        error_message="Connection failed"
                    )
                    
            except Exception as e:
                connection_results[device_id] = False
                self.device_status[device_id] = DeviceStatus(
                    device_type=config['class'].__name__,
                    device_id=device_id,
                    connected=False,
                    last_update=time.time(),
                    error_message=str(e)
                )
        
        return connection_results
    
    def _get_device_capabilities(self, device_id: str) -> List[str]:
        """Get list of capabilities for a device"""
        capabilities = {
            'adc': ['read_channel', 'read_all_channels', 'set_vref', 'get_status'],
            'io': ['read_pin', 'write_pin', 'configure_pin', 'read_all_pins', 'reset', 'get_status'],
            'rtc': ['read_datetime', 'set_datetime', 'set_alarm', 'set_clkout', 'get_status'],
            'fan': ['set_pwm', 'set_rpm', 'read_rpm', 'get_status', 'configure'],
            'eeprom': ['read', 'write', 'read_string', 'write_string', 'erase', 'test', 'get_info']
        }
        return capabilities.get(device_id, [])
    
    def process_json_command(self, json_command: str) -> str:
        """
        Process a JSON command and return JSON response
        
        Args:
            json_command (str): JSON command string
            
        Returns:
            str: JSON response string
        """
        try:
            # Parse JSON command
            command = json.loads(json_command)
            
            # Validate basic command structure
            if not isinstance(command, dict):
                return self._error_response("Command must be a JSON object")
            
            if 'action' not in command:
                return self._error_response("Command must include 'action' field")
            
            # Extract common fields
            action = command.get('action')
            device = command.get('device')
            params = command.get('params', {})
            request_id = command.get('request_id', str(uuid.uuid4()))
            
            # Route command to appropriate handler
            if action == 'get_system_status':
                response = self._handle_get_system_status(request_id)
            elif action == 'get_device_list':
                response = self._handle_get_device_list(request_id)
            elif action == 'start_monitoring':
                response = self._handle_start_monitoring(request_id, params)
            elif action == 'stop_monitoring':
                response = self._handle_stop_monitoring(request_id)
            elif device:
                response = self._handle_device_command(action, device, params, request_id)
            else:
                response = self._error_response("Unknown action or missing device", request_id)
            
            return json.dumps(asdict(response), indent=2)
            
        except json.JSONDecodeError as e:
            return self._error_response(f"Invalid JSON: {e}")
        except Exception as e:
            return self._error_response(f"Unexpected error: {e}")
    
    def _handle_get_system_status(self, request_id: str) -> APIResponse:
        """Get overall system status"""
        status_data = {
            'timestamp': time.time(),
            'bus_number': self.bus_number,
            'monitoring_active': self.monitoring_active,
            'monitoring_interval': self.monitoring_interval,
            'devices': {device_id: asdict(status) for device_id, status in self.device_status.items()}
        }
        
        return APIResponse(
            success=True,
            timestamp=time.time(),
            request_id=request_id,
            data=status_data
        )
    
    def _handle_get_device_list(self, request_id: str) -> APIResponse:
        """Get list of available devices and their capabilities"""
        devices_data = {}
        
        for device_id, status in self.device_status.items():
            devices_data[device_id] = {
                'type': status.device_type,
                'connected': status.connected,
                'capabilities': status.capabilities or [],
                'last_update': status.last_update,
                'error': status.error_message
            }
        
        return APIResponse(
            success=True,
            timestamp=time.time(),
            request_id=request_id,
            data={'devices': devices_data}
        )
    
    def _handle_device_command(self, action: str, device_id: str, params: Dict, request_id: str) -> APIResponse:
        """Handle device-specific commands"""
        
        # Check if device exists and is connected
        if device_id not in self.devices:
            return APIResponse(
                success=False,
                timestamp=time.time(),
                request_id=request_id,
                error=f"Device '{device_id}' not found or not connected"
            )
        
        device = self.devices[device_id]
        
        try:
            # Route to device-specific handlers
            if device_id == 'adc':
                return self._handle_adc_command(device, action, params, request_id)
            elif device_id == 'io':
                return self._handle_io_command(device, action, params, request_id)
            elif device_id == 'rtc':
                return self._handle_rtc_command(device, action, params, request_id)
            elif device_id == 'fan':
                return self._handle_fan_command(device, action, params, request_id)
            elif device_id == 'eeprom':
                return self._handle_eeprom_command(device, action, params, request_id)
            else:
                return APIResponse(
                    success=False,
                    timestamp=time.time(),
                    request_id=request_id,
                    error=f"No handler for device type '{device_id}'"
                )
                
        except Exception as e:
            return APIResponse(
                success=False,
                timestamp=time.time(),
                request_id=request_id,
                error=f"Device command failed: {e}",
                data={'traceback': traceback.format_exc()}
            )
    
    def _handle_adc_command(self, device: ADS7828, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle ADC-specific commands"""
        
        if action == 'read_channel':
            channel = params.get('channel', 0)
            if not (0 <= channel <= 7):
                return self._error_response("Channel must be 0-7", request_id)
            
            raw_value = device.read_channel(channel)
            voltage = device.read_channel_voltage(channel)
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'channel': channel,
                    'raw_value': raw_value,
                    'voltage': voltage,
                    'vref': device.vref
                }
            )
        
        elif action == 'read_all_channels':
            channels_data = []
            for channel in range(8):
                raw_value = device.read_channel(channel)
                voltage = device.read_channel_voltage(channel)
                channels_data.append({
                    'channel': channel,
                    'raw_value': raw_value,
                    'voltage': voltage
                })
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'channels': channels_data,
                    'vref': device.vref
                }
            )
        
        elif action == 'set_vref':
            vref = params.get('vref')
            if not vref or not isinstance(vref, (int, float)):
                return self._error_response("Invalid vref value", request_id)
            
            device.vref = float(vref)
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'vref': device.vref}
            )
        
        else:
            return self._error_response(f"Unknown ADC action: {action}", request_id)
    
    def _handle_io_command(self, device: PCAL9555A, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle I/O expander commands"""
        
        if action == 'read_pin':
            pin = params.get('pin')
            if not isinstance(pin, int) or not (0 <= pin <= 15):
                return self._error_response("Pin must be 0-15", request_id)
            
            state = device.read_pin(pin)
            pin_info = device.get_pin_info(pin)
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'pin': pin,
                    'state': state,
                    'info': pin_info
                }
            )
        
        elif action == 'write_pin':
            pin = params.get('pin')
            state = params.get('state')
            
            if not isinstance(pin, int) or not (0 <= pin <= 15):
                return self._error_response("Pin must be 0-15", request_id)
            
            success = device.write_pin(pin, bool(state))
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'pin': pin,
                    'state': bool(state),
                    'write_success': success
                }
            )
        
        elif action == 'configure_pin':
            pin = params.get('pin')
            direction = params.get('direction', 'input')
            pullup = params.get('pullup', True)
            
            if not isinstance(pin, int) or not (0 <= pin <= 15):
                return self._error_response("Pin must be 0-15", request_id)
            
            success = device.configure_pin(pin, direction, pullup)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'pin': pin,
                    'direction': direction,
                    'pullup': pullup,
                    'configure_success': success
                }
            )
        
        elif action == 'read_all_pins':
            pins_data = []
            for pin in range(16):
                state = device.read_pin(pin)
                info = device.get_pin_info(pin)
                pins_data.append({
                    'pin': pin,
                    'state': state,
                    'info': info
                })
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'pins': pins_data}
            )
        
        elif action == 'reset':
            success = device.reset_to_defaults()
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={'reset_success': success}
            )
        
        else:
            return self._error_response(f"Unknown I/O action: {action}", request_id)
    
    def _handle_rtc_command(self, device: PCF85063A, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle RTC commands"""
        
        if action == 'read_datetime':
            datetime_info = device.read_datetime()
            
            return APIResponse(
                success=datetime_info is not None,
                timestamp=time.time(),
                request_id=request_id,
                data=datetime_info
            )
        
        elif action == 'set_datetime':
            datetime_str = params.get('datetime')
            if not datetime_str:
                return self._error_response("Missing datetime parameter", request_id)
            
            try:
                # Parse datetime string (ISO format expected)
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                success = device.set_datetime(
                    dt.year, dt.month, dt.day,
                    dt.hour, dt.minute, dt.second
                )
                
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'datetime': datetime_str,
                        'set_success': success
                    }
                )
                
            except ValueError as e:
                return self._error_response(f"Invalid datetime format: {e}", request_id)
        
        elif action == 'set_clkout':
            frequency = params.get('frequency', 0)
            if not isinstance(frequency, int) or not (0 <= frequency <= 7):
                return self._error_response("Frequency must be 0-7", request_id)
            
            success = device.set_clkout_frequency(frequency)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'frequency': frequency,
                    'set_success': success
                }
            )
        
        else:
            return self._error_response(f"Unknown RTC action: {action}", request_id)
    
    def _handle_fan_command(self, device: EMC2301, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle fan controller commands"""
        
        if action == 'set_pwm':
            duty_cycle = params.get('duty_cycle')
            if not isinstance(duty_cycle, (int, float)) or not (0 <= duty_cycle <= 100):
                return self._error_response("duty_cycle must be 0-100", request_id)
            
            success = device.set_pwm_duty_cycle(float(duty_cycle))
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'duty_cycle': duty_cycle,
                    'set_success': success
                }
            )
        
        elif action == 'set_rpm':
            target_rpm = params.get('target_rpm')
            if not isinstance(target_rpm, int) or not (0 <= target_rpm <= 65535):
                return self._error_response("target_rpm must be 0-65535", request_id)
            
            # Enable RPM control mode
            device.configure_fan(enable_rpm_control=True)
            success = device.set_fan_target_rpm(target_rpm)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'target_rpm': target_rpm,
                    'set_success': success
                }
            )
        
        elif action == 'read_rpm':
            rpm = device.read_fan_rpm()
            pwm = device.get_pwm_duty_cycle()
            status = device.get_fan_status()
            
            return APIResponse(
                success=rpm is not None,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'rpm': rpm,
                    'pwm_duty_cycle': pwm,
                    'status': status
                }
            )
        
        elif action == 'configure':
            rpm_control = params.get('rpm_control', True)
            poles = params.get('poles', 2)
            edges = params.get('edges', 1)
            
            success = device.configure_fan(
                enable_rpm_control=bool(rpm_control),
                poles=int(poles),
                edges=int(edges)
            )
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'rpm_control': rpm_control,
                    'poles': poles,
                    'edges': edges,
                    'configure_success': success
                }
            )
        
        else:
            return self._error_response(f"Unknown fan action: {action}", request_id)
    
    def _handle_eeprom_command(self, device: AT24CM01, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle EEPROM commands"""
        
        if action == 'read':
            address = params.get('address', 0)
            length = params.get('length', 1)
            
            if not isinstance(address, int) or not (0 <= address < device.MEMORY_SIZE):
                return self._error_response(f"Address must be 0-{device.MEMORY_SIZE-1}", request_id)
            
            if not isinstance(length, int) or length <= 0:
                return self._error_response("Length must be positive", request_id)
            
            data = device.read_bytes(address, length)
            
            return APIResponse(
                success=data is not None,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'address': address,
                    'length': length,
                    'data': data,
                    'data_hex': [f"0x{b:02X}" for b in data] if data else None
                }
            )
        
        elif action == 'write':
            address = params.get('address', 0)
            data = params.get('data', [])
            
            if not isinstance(address, int) or not (0 <= address < device.MEMORY_SIZE):
                return self._error_response(f"Address must be 0-{device.MEMORY_SIZE-1}", request_id)
            
            if not isinstance(data, list):
                return self._error_response("Data must be list of bytes", request_id)
            
            success = device.write_bytes(address, data)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'address': address,
                    'length': len(data),
                    'write_success': success
                }
            )
        
        elif action == 'read_string':
            address = params.get('address', 0)
            max_length = params.get('max_length', 1024)
            
            text = device.read_string(address, max_length)
            
            return APIResponse(
                success=text is not None,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'address': address,
                    'text': text,
                    'length': len(text) if text else 0
                }
            )
        
        elif action == 'write_string':
            address = params.get('address', 0)
            text = params.get('text', '')
            
            success = device.write_string(address, text)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'address': address,
                    'text': text,
                    'length': len(text),
                    'write_success': success
                }
            )
        
        elif action == 'get_info':
            info = device.get_memory_info()
            
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data=info
            )
        
        elif action == 'test':
            address = params.get('address', 0x1000)
            size = params.get('size', 256)
            
            success = device.test_memory(address, size)
            
            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'test_address': address,
                    'test_size': size,
                    'test_passed': success
                }
            )
        
        else:
            return self._error_response(f"Unknown EEPROM action: {action}", request_id)
    
    def _handle_start_monitoring(self, request_id: str, params: Dict) -> APIResponse:
        """Start continuous monitoring"""
        
        if self.monitoring_active:
            return APIResponse(
                success=False,
                timestamp=time.time(),
                request_id=request_id,
                error="Monitoring already active"
            )
        
        self.monitoring_interval = params.get('interval', 1.0)
        devices_to_monitor = params.get('devices', list(self.devices.keys()))
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(devices_to_monitor,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        return APIResponse(
            success=True,
            timestamp=time.time(),
            request_id=request_id,
            data={
                'monitoring_active': True,
                'interval': self.monitoring_interval,
                'devices': devices_to_monitor
            }
        )
    
    def _handle_stop_monitoring(self, request_id: str) -> APIResponse:
        """Stop continuous monitoring"""
        
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        
        return APIResponse(
            success=True,
            timestamp=time.time(),
            request_id=request_id,
            data={'monitoring_active': False}
        )
    
    def _monitoring_loop(self, devices_to_monitor: List[str]):
        """Background monitoring loop"""
        
        while self.monitoring_active:
            try:
                monitoring_data = {
                    'timestamp': time.time(),
                    'devices': {}
                }
                
                for device_id in devices_to_monitor:
                    if device_id in self.devices:
                        device_data = self._collect_device_data(device_id)
                        monitoring_data['devices'][device_id] = device_data
                
                # Add to queue (remove oldest if full)
                try:
                    self.data_queue.put_nowait(monitoring_data)
                except queue.Full:
                    try:
                        self.data_queue.get_nowait()  # Remove oldest
                        self.data_queue.put_nowait(monitoring_data)
                    except queue.Empty:
                        pass
                
                # Trigger callbacks
                for callback in self.callbacks.get('monitoring_data', []):
                    try:
                        callback(monitoring_data)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(1.0)
    
    def _collect_device_data(self, device_id: str) -> Dict:
        """Collect current data from a specific device"""
        
        device = self.devices[device_id]
        
        try:
            if device_id == 'adc':
                channels = []
                for ch in range(8):
                    raw = device.read_channel(ch)
                    voltage = device.read_channel_voltage(ch)
                    channels.append({
                        'channel': ch,
                        'raw': raw,
                        'voltage': voltage
                    })
                return {
                    'type': 'adc',
                    'channels': channels,
                    'vref': device.vref,
                    'status': 'ok'
                }
            
            elif device_id == 'io':
                pins = []
                for pin in range(16):
                    state = device.read_pin(pin)
                    info = device.get_pin_info(pin)
                    pins.append({
                        'pin': pin,
                        'state': state,
                        'info': info
                    })
                return {
                    'type': 'io',
                    'pins': pins,
                    'status': 'ok'
                }
            
            elif device_id == 'rtc':
                datetime_info = device.read_datetime()
                return {
                    'type': 'rtc',
                    'datetime': datetime_info,
                    'status': 'ok' if datetime_info else 'error'
                }
            
            elif device_id == 'fan':
                rpm = device.read_fan_rpm()
                pwm = device.get_pwm_duty_cycle()
                fan_status = device.get_fan_status()
                return {
                    'type': 'fan',
                    'rpm': rpm,
                    'pwm_duty_cycle': pwm,
                    'fan_status': fan_status,
                    'status': 'ok' if rpm is not None else 'error'
                }
            
            elif device_id == 'eeprom':
                # Just test connectivity for monitoring
                test_byte = device._read_byte(0x0000)
                return {
                    'type': 'eeprom',
                    'test_read': test_byte,
                    'memory_size': device.MEMORY_SIZE,
                    'status': 'ok' if test_byte is not None else 'error'
                }
            
            else:
                return {'type': device_id, 'status': 'unknown'}
                
        except Exception as e:
            return {
                'type': device_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_monitoring_data(self, max_items: int = 1) -> List[Dict]:
        """
        Get monitoring data from queue
        
        Args:
            max_items (int): Maximum number of items to return
            
        Returns:
            List[Dict]: List of monitoring data
        """
        data = []
        for _ in range(max_items):
            try:
                item = self.data_queue.get_nowait()
                data.append(item)
            except queue.Empty:
                break
        return data
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register callback for events
        
        Args:
            event_type (str): Event type ('monitoring_data', 'device_error', etc.)
            callback (Callable): Callback function
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def disconnect_all(self):
        """Disconnect all devices and stop monitoring"""
        
        # Stop monitoring
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        
        # Disconnect devices
        for device in self.devices.values():
            try:
                device.disconnect()
            except Exception as e:
                print(f"Error disconnecting device: {e}")
        
        self.devices.clear()
        self.device_status.clear()
    
    def _error_response(self, message: str, request_id: str = None) -> APIResponse:
        """Create error response"""
        return APIResponse(
            success=False,
            timestamp=time.time(),
            request_id=request_id,
            error=message
        )

# Convenience functions for common operations

def create_api_server(host='localhost', port=8080, hmi_api=None):
    """
    Create a simple HTTP server for the JSON API
    Requires Flask: pip install flask flask-cors
    """
    try:
        from flask import Flask, request, jsonify
        from flask_cors import CORS
    except ImportError:
        raise ImportError("Flask and flask-cors required for API server. Install with: pip install flask flask-cors")
    
    if hmi_api is None:
        hmi_api = HMIJsonAPI()
    
    app = Flask(__name__)
    CORS(app)  # Enable CORS for web interfaces
    
    @app.route('/api/command', methods=['POST'])
    def handle_command():
        try:
            json_command = request.get_json()
            if isinstance(json_command, dict):
                json_command = json.dumps(json_command)
            
            response = hmi_api.process_json_command(json_command)
            return jsonify(json.loads(response))
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }), 500
    
    @app.route('/api/monitoring/data', methods=['GET'])
    def get_monitoring_data():
        max_items = request.args.get('max_items', 10, type=int)
        data = hmi_api.get_monitoring_data(max_items)
        return jsonify({
            'success': True,
            'timestamp': time.time(),
            'data': data
        })
    
    @app.route('/api/status', methods=['GET'])
    def get_status():
        status_command = json.dumps({'action': 'get_system_status'})
        response = hmi_api.process_json_command(status_command)
        return jsonify(json.loads(response))
    
    print(f"Starting HMI API server on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

def create_websocket_server(host='localhost', port=8081, hmi_api=None):
    """
    Create a WebSocket server for real-time communication
    Requires websockets: pip install websockets
    """
    try:
        import asyncio
        import websockets
        import json
    except ImportError:
        raise ImportError("websockets required for WebSocket server. Install with: pip install websockets")
    
    if hmi_api is None:
        hmi_api = HMIJsonAPI()
    
    async def handle_client(websocket, path):
        print(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    # Process command
                    response = hmi_api.process_json_command(message)
                    await websocket.send(response)
                    
                    # Send monitoring data if available
                    monitoring_data = hmi_api.get_monitoring_data(1)
                    if monitoring_data:
                        monitoring_response = {
                            'type': 'monitoring_data',
                            'timestamp': time.time(),
                            'data': monitoring_data[0]
                        }
                        await websocket.send(json.dumps(monitoring_response))
                        
                except Exception as e:
                    error_response = {
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time()
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {websocket.remote_address}")
    
    print(f"Starting HMI WebSocket server on ws://{host}:{port}")
    start_server = websockets.serve(handle_client, host, port)
    
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    # Example usage
    import sys
    
    # Create HMI API instance
    hmi = HMIJsonAPI()
    
    # Example JSON commands
    example_commands = [
        # Get system status
        '{"action": "get_system_status"}',
        
        # Get device list
        '{"action": "get_device_list"}',
        
        # Read ADC channel 0
        '{"action": "read_channel", "device": "adc", "params": {"channel": 0}}',
        
        # Read all ADC channels
        '{"action": "read_all_channels", "device": "adc"}',
        
        # Configure I/O pin as output
        '{"action": "configure_pin", "device": "io", "params": {"pin": 0, "direction": "output", "pullup": false}}',
        
        # Set I/O pin high
        '{"action": "write_pin", "device": "io", "params": {"pin": 0, "state": true}}',
        
        # Read RTC
        '{"action": "read_datetime", "device": "rtc"}',
        
        # Set fan PWM
        '{"action": "set_pwm", "device": "fan", "params": {"duty_cycle": 50}}',
        
        # Read fan status
        '{"action": "read_rpm", "device": "fan"}',
        
        # Read EEPROM
        '{"action": "read", "device": "eeprom", "params": {"address": 0, "length": 16}}',
        
        # Start monitoring
        '{"action": "start_monitoring", "params": {"interval": 2.0}}'
    ]
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            # Start HTTP API server
            create_api_server()
        elif sys.argv[1] == 'websocket':
            # Start WebSocket server
            create_websocket_server()
        else:
            print("Usage: python hmi_json_api.py [server|websocket]")
    else:
        # Interactive mode - demonstrate commands
        print("HMI JSON API - Interactive Demo")
        print("=" * 40)
        
        for i, cmd in enumerate(example_commands):
            print(f"\nCommand {i+1}: {cmd}")
            response = hmi.process_json_command(cmd)
            print(f"Response: {response}")
            
            if i < len(example_commands) - 1:
                input("Press Enter for next command...")
        
        # Cleanup
        hmi.disconnect_all()
