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
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import uuid
from collections import defaultdict, deque

# Import device classes (assumes they're available)
try:
    from ads7828_adc import ADS7828
    from pcal9555a_io import PCAL9555A
    from pcf85063a_rtc import PCF85063A
    from emc2301_fan_controller import EMC2301
    from at24cm01_eeprom import AT24CM01
except ImportError as e:
    print(f"Warning: Some device modules not available: {e}")

# Import AI-Vision system
try:
    from ai_vision_system import get_ai_vision_system, AIVisionSystem
    AI_VISION_AVAILABLE = True
    print("AI-Vision system available")
except ImportError as e:
    print(f"Warning: AI-Vision system not available: {e}")
    AI_VISION_AVAILABLE = False

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

@dataclass
class ADCDataPoint:
    """Single ADC data point for logging"""
    timestamp: float
    channel: int
    raw_value: int
    voltage: float
    vref: float

@dataclass
class LoggingConfig:
    """Configuration for data logging"""
    enabled: bool = False
    sample_interval: float = 1.0  # seconds
    max_memory_points: int = 3600  # 1 hour at 1Hz
    file_rotation_hours: int = 24
    log_directory: str = "logs"
    channels: List[int] = None  # None means all channels

class ADCDataLogger:
    """
    ADC Data Logger - handles time-series logging of ADC readings
    Supports both in-memory and file-based storage
    """

    def __init__(self, config: LoggingConfig = None):
        self.config = config or LoggingConfig()

        # In-memory data storage (channel -> deque of data points)
        self.memory_data: Dict[int, deque] = defaultdict(lambda: deque(maxlen=self.config.max_memory_points))

        # File logging
        self.current_log_file = None
        self.log_file_start_time = None
        self.logging_thread = None
        self.logging_active = False
        self.data_queue = queue.Queue(maxsize=10000)

        # Create log directory
        if self.config.enabled:
            os.makedirs(self.config.log_directory, exist_ok=True)

    def start_logging(self):
        """Start the background logging thread"""
        if self.logging_active:
            return

        self.logging_active = True
        self.logging_thread = threading.Thread(target=self._logging_worker, daemon=True)
        self.logging_thread.start()
        print("ADC logging started")

    def stop_logging(self):
        """Stop the background logging thread"""
        self.logging_active = False
        if self.logging_thread:
            self.logging_thread.join(timeout=5)
        if self.current_log_file:
            self.current_log_file.close()
            self.current_log_file = None
        print("ADC logging stopped")

    def log_adc_reading(self, data_point: ADCDataPoint):
        """Add an ADC reading to the logging queue"""
        if not self.config.enabled:
            return

        # Check if we should log this channel
        if self.config.channels is not None and data_point.channel not in self.config.channels:
            return

        # Add to memory storage
        self.memory_data[data_point.channel].append(data_point)

        # Add to file logging queue
        try:
            self.data_queue.put_nowait(data_point)
        except queue.Full:
            print("WARNING: ADC logging queue full, dropping data point")

    def get_recent_data(self, channel: int = None, max_points: int = None, time_range_seconds: int = None) -> Dict[int, List[ADCDataPoint]]:
        """Get recent data from memory storage"""
        result = {}

        channels_to_get = [channel] if channel is not None else list(self.memory_data.keys())

        for ch in channels_to_get:
            if ch not in self.memory_data:
                continue

            data = list(self.memory_data[ch])

            # Apply time range filter
            if time_range_seconds:
                cutoff_time = time.time() - time_range_seconds
                data = [dp for dp in data if dp.timestamp >= cutoff_time]

            # Apply max points limit
            if max_points:
                data = data[-max_points:]

            result[ch] = data

        return result

    def get_logging_stats(self) -> Dict:
        """Get statistics about the logging system"""
        stats = {
            'enabled': self.config.enabled,
            'active': self.logging_active,
            'sample_interval': self.config.sample_interval,
            'memory_points_per_channel': {ch: len(data) for ch, data in self.memory_data.items()},
            'total_memory_points': sum(len(data) for data in self.memory_data.values()),
            'queue_size': self.data_queue.qsize() if hasattr(self.data_queue, 'qsize') else 0,
            'current_log_file': os.path.basename(self.current_log_file.name) if self.current_log_file else None
        }
        return stats

    def export_data_csv(self, filename: str, channel: int = None, time_range_seconds: int = None) -> bool:
        """Export data to CSV file"""
        try:
            data = self.get_recent_data(channel=channel, time_range_seconds=time_range_seconds)

            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'datetime', 'channel', 'raw_value', 'voltage', 'vref'])

                # Combine all channels and sort by timestamp
                all_points = []
                for ch, points in data.items():
                    all_points.extend(points)

                all_points.sort(key=lambda x: x.timestamp)

                for point in all_points:
                    dt = datetime.fromtimestamp(point.timestamp)
                    writer.writerow([
                        point.timestamp,
                        dt.isoformat(),
                        point.channel,
                        point.raw_value,
                        point.voltage,
                        point.vref
                    ])

            return True

        except Exception as e:
            print(f"Failed to export CSV: {e}")
            return False

    def _logging_worker(self):
        """Background thread worker for file logging"""
        while self.logging_active:
            try:
                # Check if we need to rotate log file
                self._check_log_rotation()

                # Process queued data points
                try:
                    data_point = self.data_queue.get(timeout=1.0)
                    self._write_to_file(data_point)
                except queue.Empty:
                    continue

            except Exception as e:
                print(f"Error in logging worker: {e}")
                time.sleep(1)

    def _check_log_rotation(self):
        """Check if we need to rotate the log file"""
        current_time = time.time()

        if (self.current_log_file is None or
            self.log_file_start_time is None or
            (current_time - self.log_file_start_time) > (self.config.file_rotation_hours * 3600)):

            # Close current file
            if self.current_log_file:
                self.current_log_file.close()

            # Create new file
            timestamp = datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")
            filename = f"adc_data_{timestamp}.csv"
            filepath = os.path.join(self.config.log_directory, filename)

            self.current_log_file = open(filepath, 'w', newline='')
            self.log_file_start_time = current_time

            # Write header
            writer = csv.writer(self.current_log_file)
            writer.writerow(['timestamp', 'datetime', 'channel', 'raw_value', 'voltage', 'vref'])

            print(f"Started new log file: {filename}")

    def _write_to_file(self, data_point: ADCDataPoint):
        """Write a data point to the current log file"""
        if not self.current_log_file:
            return

        writer = csv.writer(self.current_log_file)
        dt = datetime.fromtimestamp(data_point.timestamp)
        writer.writerow([
            data_point.timestamp,
            dt.isoformat(),
            data_point.channel,
            data_point.raw_value,
            data_point.voltage,
            data_point.vref
        ])
        self.current_log_file.flush()

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
            'eeprom': {'class': AT24CM01, 'base_address': 0x56},
            'ai_vision': {'class': None, 'enabled': AI_VISION_AVAILABLE}
        }
        
        # API state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 1.0
        self.data_queue = queue.Queue(maxsize=1000)
        self.callbacks = {}  # Event callbacks
        
        # Device status tracking
        self.device_status = {}

        # ADC Data Logger
        logging_config = LoggingConfig(
            enabled=False,  # Changed to False - user must manually start logging
            sample_interval=2.0,
            max_memory_points=1800,  # 1 hour at 2 second intervals
            file_rotation_hours=24,
            log_directory="adc_logs"
        )
        self.adc_logger = ADCDataLogger(logging_config)

        # Initialize devices if requested
        if auto_connect:
            self.initialize_devices()

        # ADC logging is now manual - user must start it via the API

        # Initialize AI-Vision system
        if AI_VISION_AVAILABLE:
            self.ai_vision = get_ai_vision_system()
            try:
                if self.ai_vision.initialize():
                    print("AI-Vision system initialized successfully")
                    self.devices['ai_vision'] = self.ai_vision
                    self.device_status['ai_vision'] = DeviceStatus(
                        device_type="AIVisionSystem",
                        device_id="ai_vision",
                        connected=True,
                        last_update=time.time(),
                        capabilities=['object_detection', 'camera_streaming', 'real_time_inference']
                    )
                else:
                    print("Failed to initialize AI-Vision system")
            except Exception as e:
                print(f"Error initializing AI-Vision: {e}")
        else:
            self.ai_vision = None
    
    def initialize_devices(self) -> Dict[str, bool]:
        """
        Initialize and connect to all available devices
        
        Returns:
            Dict[str, bool]: Connection status for each device
        """
        connection_results = {}
        
        for device_id, config in self.device_configs.items():
            try:
                # Skip AI-Vision as it's handled separately
                if device_id == 'ai_vision':
                    continue

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
            elif device_id == 'ai_vision':
                return self._handle_ai_vision_command(device, action, params, request_id)
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
    
    def _handle_adc_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle ADC-specific commands"""
        
        if action == 'read_channel':
            channel = params.get('channel', 0)
            if not (0 <= channel <= 7):
                return self._error_response("Channel must be 0-7", request_id)

            # Use averaged reading for stability
            raw_value = device.read_channel_averaged(channel, samples=4)
            voltage = (raw_value / 4095.0) * device.vref
            timestamp = time.time()

            # Log the reading
            data_point = ADCDataPoint(
                timestamp=timestamp,
                channel=channel,
                raw_value=raw_value,
                voltage=voltage,
                vref=device.vref
            )
            self.adc_logger.log_adc_reading(data_point)

            return APIResponse(
                success=True,
                timestamp=timestamp,
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
            timestamp = time.time()

            for channel in range(8):
                # Use averaged reading for stability
                raw_value = device.read_channel_averaged(channel, samples=3)
                voltage = (raw_value / 4095.0) * device.vref
                channels_data.append({
                    'channel': channel,
                    'raw_value': raw_value,
                    'voltage': voltage
                })

                # Log each channel reading
                data_point = ADCDataPoint(
                    timestamp=timestamp,
                    channel=channel,
                    raw_value=raw_value,
                    voltage=voltage,
                    vref=device.vref
                )
                self.adc_logger.log_adc_reading(data_point)

            return APIResponse(
                success=True,
                timestamp=timestamp,
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
        
        elif action == 'get_logged_data':
            # Get parameters
            channel = params.get('channel')  # None means all channels
            max_points = params.get('max_points', 100)
            time_range_seconds = params.get('time_range_seconds')

            # Get data from logger
            data = self.adc_logger.get_recent_data(
                channel=channel,
                max_points=max_points,
                time_range_seconds=time_range_seconds
            )

            # Convert to JSON-serializable format
            result = {}
            for ch, points in data.items():
                result[str(ch)] = [
                    {
                        'timestamp': dp.timestamp,
                        'channel': dp.channel,
                        'raw_value': dp.raw_value,
                        'voltage': dp.voltage,
                        'vref': dp.vref
                    }
                    for dp in points
                ]

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'logged_data': result,
                    'logging_stats': self.adc_logger.get_logging_stats()
                }
            )

        elif action == 'start_logging':
            if not self.adc_logger.logging_active:
                self.adc_logger.config.enabled = True  # Enable logging config
                self.adc_logger.start_logging()

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'logging_active': self.adc_logger.logging_active}
            )

        elif action == 'stop_logging':
            if self.adc_logger.logging_active:
                self.adc_logger.config.enabled = False  # Disable logging config
                self.adc_logger.stop_logging()

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'logging_active': self.adc_logger.logging_active}
            )

        elif action == 'get_logging_stats':
            stats = self.adc_logger.get_logging_stats()

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data=stats
            )

        elif action == 'export_csv':
            filename = params.get('filename', f"adc_export_{int(time.time())}.csv")
            channel = params.get('channel')
            time_range_seconds = params.get('time_range_seconds')

            success = self.adc_logger.export_data_csv(
                filename=filename,
                channel=channel,
                time_range_seconds=time_range_seconds
            )

            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={'filename': filename, 'exported': success}
            )

        else:
            return self._error_response(f"Unknown ADC action: {action}", request_id)
    
    def _handle_io_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
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
    
    def _handle_rtc_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
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
    
    def _handle_fan_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
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
        
        elif action == 'get_status':
            rpm = device.read_fan_rpm()
            pwm = device.get_pwm_duty_cycle()
            fan_status = device.get_fan_status()

            # Calculate target RPM based on current PWM (rough approximation)
            target_rpm = int((pwm / 100.0) * 3000) if pwm else 0

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'rpm': rpm or 0,
                    'target_rpm': target_rpm,
                    'duty_cycle': pwm or 0,
                    'failure': False  # Could be enhanced to detect actual failures
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
    
    def _handle_eeprom_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
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

    def _handle_ai_vision_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle AI-Vision system commands"""

        if action == 'get_status':
            status = device.get_status()
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data=asdict(status)
            )

        elif action == 'list_cameras':
            cameras = device.camera_manager.detect_cameras()
            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'cameras': [asdict(cam) for cam in cameras]
                }
            )

        elif action == 'start':
            camera_id = params.get('camera_id', 0)
            model_name = params.get('model_name', 'yolo11n.pt')

            # Load model if different
            current_model = device.inference_engine.model_name
            if current_model != model_name:
                if not device.inference_engine.load_model(model_name):
                    return self._error_response(f"Failed to load model: {model_name}", request_id)

            success = device.start(camera_id)

            return APIResponse(
                success=success,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'active': device.active,
                    'camera_id': camera_id,
                    'model_name': model_name
                }
            )

        elif action == 'stop':
            device.stop()

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'active': device.active}
            )

        elif action == 'set_confidence':
            confidence = params.get('confidence', 0.5)
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                return self._error_response("Confidence must be between 0.0 and 1.0", request_id)

            device.inference_engine.set_confidence_threshold(confidence)

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'confidence_threshold': device.inference_engine.confidence_threshold}
            )

        elif action == 'get_frame':
            frame_data = device.get_latest_frame()
            if frame_data:
                # Encode frame as base64 for JSON transport
                frame_b64 = base64.b64encode(frame_data).decode('utf-8')
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'frame': frame_b64,
                        'format': 'jpeg',
                        'active': device.active
                    }
                )
            else:
                return APIResponse(
                    success=False,
                    timestamp=time.time(),
                    request_id=request_id,
                    error="No frame available"
                )

        elif action == 'get_detections':
            max_count = params.get('max_count', 10)
            detections = device.get_recent_detections(max_count)

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={
                    'detections': detections,
                    'count': len(detections)
                }
            )

        elif action == 'get_available_models':
            # List of common YOLO models
            models = [
                'yolo11n.pt',    # Nano - fastest
                'yolo11s.pt',    # Small
                'yolo11m.pt',    # Medium
                'yolo11l.pt',    # Large
                'yolo11x.pt'     # Extra Large - most accurate
            ]

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data={'available_models': models}
            )

        else:
            return self._error_response(f"Unknown AI-Vision action: {action}", request_id)

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
                    # Use faster averaging for monitoring (2 samples)
                    raw = device.read_channel_averaged(ch, samples=2)
                    voltage = (raw / 4095.0) * device.vref
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

    @app.route('/api/ai_vision/stream')
    def video_stream():
        """Video streaming endpoint for AI-Vision"""
        def generate_frames():
            while True:
                if hmi_api.ai_vision and hmi_api.ai_vision.active:
                    frame_data = hmi_api.ai_vision.get_latest_frame()
                    if frame_data:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    else:
                        time.sleep(0.1)
                else:
                    time.sleep(0.5)

        return app.response_class(
            generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    @app.route('/api/ai_vision/frame')
    def get_frame():
        """Get single frame as base64-encoded JPEG"""
        import base64

        if hmi_api.ai_vision and hmi_api.ai_vision.active:
            frame_data = hmi_api.ai_vision.get_latest_frame()
            if frame_data:
                # Encode frame data as base64
                frame_base64 = base64.b64encode(frame_data).decode('utf-8')
                return jsonify({
                    'success': True,
                    'timestamp': time.time(),
                    'frame': frame_base64,
                    'format': 'jpeg'
                })

        return jsonify({
            'success': False,
            'timestamp': time.time(),
            'error': 'No frame available'
        })

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
            create_api_server(port=8081)
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
