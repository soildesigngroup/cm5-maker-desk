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
import sqlite3
import subprocess
import signal
import shutil
import psutil
import re
import glob
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

# Import CAN interface
try:
    from can_interface import get_can_interface, CANInterface, CANBusConfig
    CAN_AVAILABLE = True
    print("CAN interface available")
except ImportError as e:
    print(f"Warning: CAN interface not available: {e}")
    CAN_AVAILABLE = False

# Import Automation engine
try:
    from automation_engine import get_automation_engine, AutomationEngine, AutomationRequest, Environment, Collection
    AUTOMATION_AVAILABLE = True
    print("Automation engine available")
except ImportError as e:
    print(f"Warning: Automation engine not available: {e}")
    AUTOMATION_AVAILABLE = False

# Import DIAG Agent (Log Monitor)
try:
    from log_monitor import LogMonitoringAgent, DatabaseManager, LogAnalyzer, ClaudeAnalyzer, AlertManager
    DIAG_AGENT_AVAILABLE = True
    print("DIAG Agent (Log Monitor) available")
except ImportError as e:
    print(f"Warning: DIAG Agent not available: {e}")
    DIAG_AGENT_AVAILABLE = False

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

class GPIOStatusController:
    """Controls GPIO pin to indicate app status"""

    def __init__(self, gpio_pin: int = 16):
        self.gpio_pin = gpio_pin
        self.is_running = False
        self.blink_thread = None
        self._stop_event = threading.Event()

    def start_status_blink(self):
        """Start blinking GPIO to indicate app is active"""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self.blink_thread = threading.Thread(target=self._blink_loop, daemon=True)
        self.blink_thread.start()
        print(f"Started GPIO {self.gpio_pin} status blinking")

    def stop_status_blink(self):
        """Stop blinking and set GPIO low"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self.blink_thread:
            self.blink_thread.join(timeout=3.0)

        # Ensure GPIO is set low when stopped
        self._set_gpio_low()
        print(f"Stopped GPIO {self.gpio_pin} status blinking")

    def _blink_loop(self):
        """Main blinking loop"""
        while not self._stop_event.is_set():
            try:
                # Set high
                self._set_gpio_high()
                if self._stop_event.wait(1.0):  # Wait 1 second or until stop event
                    break

                # Set low
                self._set_gpio_low()
                if self._stop_event.wait(1.0):  # Wait 1 second or until stop event
                    break

            except Exception as e:
                print(f"Error in GPIO blink loop: {e}")
                time.sleep(1.0)

    def _set_gpio_high(self):
        """Set GPIO pin high using pinctrl"""
        try:
            subprocess.run(['pinctrl', 'set', str(self.gpio_pin), 'op', 'dh'],
                         check=True, capture_output=True, timeout=5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Silently ignore GPIO errors to prevent app crashes
            pass

    def _set_gpio_low(self):
        """Set GPIO pin low using pinctrl"""
        try:
            subprocess.run(['pinctrl', 'set', str(self.gpio_pin), 'op', 'dl'],
                         check=True, capture_output=True, timeout=5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Silently ignore GPIO errors to prevent app crashes
            pass

class AudioInterface:
    """Controls TSCS42xx Audio CODEC via ALSA controls"""

    def __init__(self):
        self.device_name = "hw:0"  # Default ALSA device
        self.available_controls = {}
        self._refresh_controls()

    def connect(self) -> bool:
        """Connect to audio interface (ALSA)"""
        try:
            # Test if ALSA is available by listing controls
            result = subprocess.run(['amixer', '-c', '0', 'info'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._refresh_controls()
                print(f"Audio interface connected with {len(self.available_controls)} controls")
                return True
            else:
                print("Warning: Audio interface unavailable - no ALSA card 0")
                return False
        except Exception as e:
            print(f"Warning: Could not connect to audio interface: {e}")
            return False

    def _refresh_controls(self):
        """Scan available ALSA controls"""
        try:
            result = subprocess.run(['amixer', '-c', '0', 'controls'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and 'name=' in line:
                        # Parse control name
                        name_start = line.find("name='") + 6
                        name_end = line.find("'", name_start)
                        if name_start > 5 and name_end > name_start:
                            control_name = line[name_start:name_end]
                            self.available_controls[control_name] = True
        except Exception as e:
            print(f"Warning: Could not scan ALSA controls: {e}")

    def get_control_value(self, control_name: str) -> Optional[str]:
        """Get current value of an ALSA control"""
        try:
            result = subprocess.run(['amixer', '-c', '0', 'cget', f"name='{control_name}'"],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse the value from amixer output
                for line in result.stdout.split('\n'):
                    if ': values=' in line:
                        return line.split(': values=')[1].strip()
            return None
        except Exception as e:
            print(f"Error reading control {control_name}: {e}")
            return None

    def set_control_value(self, control_name: str, value: str) -> bool:
        """Set value of an ALSA control"""
        try:
            result = subprocess.run(['amixer', '-c', '0', 'cset', f"name='{control_name}'", value],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            print(f"Error setting control {control_name}: {e}")
            return False

    def get_volume_controls(self) -> Dict[str, Any]:
        """Get all volume-related controls"""
        volume_controls = {}
        volume_keywords = ['Volume', 'volume']

        for control_name in self.available_controls:
            if any(keyword in control_name for keyword in volume_keywords):
                value = self.get_control_value(control_name)
                volume_controls[control_name] = {
                    'value': value,
                    'type': 'volume'
                }
        return volume_controls

    def get_switch_controls(self) -> Dict[str, Any]:
        """Get all switch/enable controls"""
        switch_controls = {}
        switch_keywords = ['Switch', 'Enable', 'switch', 'enable']

        for control_name in self.available_controls:
            if any(keyword in control_name for keyword in switch_keywords):
                value = self.get_control_value(control_name)
                switch_controls[control_name] = {
                    'value': value,
                    'type': 'switch'
                }
        return switch_controls

    def get_eq_controls(self) -> Dict[str, Any]:
        """Get equalizer controls"""
        eq_controls = {}
        eq_keywords = ['EQ', 'eq', 'Equalizer']

        for control_name in self.available_controls:
            if any(keyword in control_name for keyword in eq_keywords):
                value = self.get_control_value(control_name)
                eq_controls[control_name] = {
                    'value': value,
                    'type': 'eq'
                }
        return eq_controls

    def get_all_controls(self) -> Dict[str, Any]:
        """Get all available audio controls with their current values"""
        all_controls = {}

        for control_name in self.available_controls:
            value = self.get_control_value(control_name)
            control_type = 'unknown'

            # Categorize control
            if any(keyword in control_name for keyword in ['Volume', 'volume']):
                control_type = 'volume'
            elif any(keyword in control_name for keyword in ['Switch', 'Enable', 'switch', 'enable']):
                control_type = 'switch'
            elif any(keyword in control_name for keyword in ['EQ', 'eq', 'Equalizer']):
                control_type = 'eq'
            elif any(keyword in control_name for keyword in ['Route', 'route']):
                control_type = 'routing'
            elif any(keyword in control_name for keyword in ['Comp', 'comp', 'Limiter', 'limiter']):
                control_type = 'dynamics'

            all_controls[control_name] = {
                'value': value,
                'type': control_type,
                'available': True
            }

        return all_controls

    def test_audio_device(self) -> bool:
        """Test if audio device is available"""
        try:
            # Test if we can access ALSA controls (more reliable than checking device names)
            result = subprocess.run(['amixer', '-c', '0', 'info'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # If we have available controls, the device is working
                return len(self.available_controls) > 0
            return False
        except Exception:
            return False

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
            'ai_vision': {'class': None, 'enabled': AI_VISION_AVAILABLE},
            'audio': {'class': AudioInterface, 'enabled': True}
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

        # GPIO Status Controller
        self.gpio_controller = GPIOStatusController(gpio_pin=16)

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
                elif device_id == 'audio':
                    device = device_class()
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
            'eeprom': ['read', 'write', 'read_string', 'write_string', 'erase', 'test', 'get_info'],
            'audio': ['get_status', 'get_all_controls', 'get_volume_controls', 'get_switch_controls', 'get_eq_controls', 'set_control', 'get_control', 'refresh_controls']
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
            elif action == 'get_storage_info':
                response = self._handle_get_storage_info(request_id)
            elif action == 'format_drive':
                response = self._handle_format_drive(request_id, params)
            elif action == 'test_storage_speed':
                response = self._handle_test_storage_speed(request_id, params)
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

    def _handle_get_storage_info(self, request_id: str) -> APIResponse:
        """Get storage information including NVMe PCIe drives"""
        try:
            storage_data = self._get_storage_info()

            return APIResponse(
                success=True,
                timestamp=time.time(),
                request_id=request_id,
                data=storage_data
            )
        except Exception as e:
            return self._error_response(f"Storage info error: {str(e)}", request_id)

    def _handle_format_drive(self, request_id: str, params: Dict) -> APIResponse:
        """Handle drive formatting requests"""
        try:
            device_path = params.get('device_path')
            filesystem = params.get('filesystem', 'ext4')
            label = params.get('label', 'ExternalDrive')

            if not device_path:
                return self._error_response("Missing device_path parameter", request_id)

            # Security check - only allow NVMe devices
            if not device_path.startswith('/dev/nvme'):
                return self._error_response("Only NVMe devices are allowed for formatting", request_id)

            # Verify device exists
            if not os.path.exists(device_path):
                return self._error_response(f"Device {device_path} not found", request_id)

            # Format the drive
            format_result = self._format_drive(device_path, filesystem, label)

            if format_result['success']:
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'message': f"Successfully formatted {device_path} with {filesystem}",
                        'device_path': device_path,
                        'filesystem': filesystem,
                        'label': label,
                        'mount_point': format_result.get('mount_point')
                    }
                )
            else:
                return self._error_response(f"Format failed: {format_result.get('error', 'Unknown error')}", request_id)

        except Exception as e:
            return self._error_response(f"Format drive error: {str(e)}", request_id)

    def _format_drive(self, device_path: str, filesystem: str, label: str) -> Dict:
        """Format a drive with the specified filesystem"""
        try:
            # Unmount if mounted
            try:
                subprocess.run(['sudo', 'umount', device_path], capture_output=True, timeout=10)
            except:
                pass  # Device might not be mounted

            # Create partition table (GPT)
            print(f"Creating partition table on {device_path}...")
            result = subprocess.run(['sudo', 'parted', '-s', device_path, 'mklabel', 'gpt'],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {'success': False, 'error': f"Failed to create partition table: {result.stderr}"}

            # Create partition
            print(f"Creating partition on {device_path}...")
            result = subprocess.run(['sudo', 'parted', '-s', device_path, 'mkpart', 'primary', '0%', '100%'],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {'success': False, 'error': f"Failed to create partition: {result.stderr}"}

            # Wait for partition to appear
            partition_path = f"{device_path}p1"
            for i in range(10):  # Wait up to 10 seconds
                if os.path.exists(partition_path):
                    break
                time.sleep(1)

            if not os.path.exists(partition_path):
                return {'success': False, 'error': f"Partition {partition_path} did not appear"}

            # Format with filesystem
            print(f"Formatting {partition_path} with {filesystem}...")
            if filesystem == 'ext4':
                cmd = ['sudo', 'mkfs.ext4', '-F', '-L', label, partition_path]
            elif filesystem == 'fat32':
                cmd = ['sudo', 'mkfs.fat', '-F', '32', '-n', label, partition_path]
            elif filesystem == 'ntfs':
                cmd = ['sudo', 'mkfs.ntfs', '-Q', '-L', label, partition_path]
            else:
                return {'success': False, 'error': f"Unsupported filesystem: {filesystem}"}

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return {'success': False, 'error': f"Failed to format: {result.stderr}"}

            # Create mount point and mount
            mount_point = f"/media/{os.getenv('USER', 'user')}/{label}"
            try:
                subprocess.run(['sudo', 'mkdir', '-p', mount_point], capture_output=True, timeout=10)
                result = subprocess.run(['sudo', 'mount', partition_path, mount_point],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    print(f"Warning: Failed to mount {partition_path}: {result.stderr}")
                    mount_point = None
            except Exception as e:
                print(f"Warning: Failed to create/mount {mount_point}: {e}")
                mount_point = None

            return {
                'success': True,
                'device_path': device_path,
                'partition_path': partition_path,
                'filesystem': filesystem,
                'label': label,
                'mount_point': mount_point
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_test_storage_speed(self, request_id: str, params: Dict) -> APIResponse:
        """Handle storage speed test requests"""
        try:
            device_path = params.get('device_path')
            test_size = params.get('test_size', '100M')  # Default 100MB test

            if not device_path:
                return self._error_response("Device path is required", request_id)

            # Security check - only allow mounted devices or known storage devices
            partitions = psutil.disk_partitions()
            valid_devices = [p.device for p in partitions]

            # Also allow testing the raw block device (e.g., /dev/nvme0n1)
            import re
            base_device = re.sub(r'p?\d+$', '', device_path)
            if device_path not in valid_devices and base_device not in [re.sub(r'p?\d+$', '', d) for d in valid_devices]:
                return self._error_response(f"Device {device_path} is not accessible or not mounted", request_id)

            # Run the speed test
            speed_test_result = self._test_storage_speed(device_path, test_size)

            if speed_test_result['success']:
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=speed_test_result
                )
            else:
                return self._error_response(f"Speed test failed: {speed_test_result.get('error', 'Unknown error')}", request_id)

        except Exception as e:
            return self._error_response(f"Speed test error: {str(e)}", request_id)

    def _test_storage_speed(self, device_path: str, test_size: str = '100M') -> Dict:
        """Test storage read/write speed using dd command"""
        try:
            # Get mount point for the device
            partitions = psutil.disk_partitions()
            mount_point = None
            device_name = device_path.split('/')[-1]

            for partition in partitions:
                if partition.device == device_path:
                    mount_point = partition.mountpoint
                    break

            if not mount_point:
                return {'success': False, 'error': f'Device {device_path} is not mounted'}

            # Create a temporary test directory using sudo
            test_dir = os.path.join(mount_point, '.speed_test_tmp')
            subprocess.run(['sudo', 'mkdir', '-p', test_dir], check=True)

            test_file = os.path.join(test_dir, 'speedtest.tmp')

            results = {
                'success': True,
                'device_path': device_path,
                'device_name': device_name,
                'mount_point': mount_point,
                'test_size': test_size,
                'write_speed_mbps': 0,
                'read_speed_mbps': 0,
                'write_time_seconds': 0,
                'read_time_seconds': 0
            }

            # Write test
            print(f"Testing write speed for {device_path}...")
            start_time = time.time()
            write_result = subprocess.run([
                'sudo', 'dd', f'if=/dev/zero', f'of={test_file}',
                f'bs=1M', f'count={test_size[:-1]}', 'conv=fdatasync'
            ], capture_output=True, text=True, timeout=120)

            write_time = time.time() - start_time
            results['write_time_seconds'] = round(write_time, 2)

            if write_result.returncode == 0:
                # Parse dd output for write speed
                dd_output = write_result.stderr
                # Extract speed from dd output (e.g., "104857600 bytes (105 MB, 100 MiB) copied, 0.123456 s, 849 MB/s")
                import re
                speed_match = re.search(r'(\d+(?:\.\d+)?)\s*(MB/s|GB/s)', dd_output)
                if speed_match:
                    speed_value = float(speed_match.group(1))
                    speed_unit = speed_match.group(2)
                    if speed_unit == 'GB/s':
                        speed_value *= 1000  # Convert to MB/s
                    results['write_speed_mbps'] = round(speed_value, 2)
                else:
                    # Fallback calculation
                    size_bytes = int(test_size[:-1]) * 1024 * 1024  # Convert MB to bytes
                    results['write_speed_mbps'] = round((size_bytes / write_time) / (1024 * 1024), 2)

            # Read test
            print(f"Testing read speed for {device_path}...")
            start_time = time.time()
            read_result = subprocess.run([
                'sudo', 'dd', f'if={test_file}', f'of=/dev/null',
                f'bs=1M'
            ], capture_output=True, text=True, timeout=120)

            read_time = time.time() - start_time
            results['read_time_seconds'] = round(read_time, 2)

            if read_result.returncode == 0:
                # Parse dd output for read speed
                dd_output = read_result.stderr
                speed_match = re.search(r'(\d+(?:\.\d+)?)\s*(MB/s|GB/s)', dd_output)
                if speed_match:
                    speed_value = float(speed_match.group(1))
                    speed_unit = speed_match.group(2)
                    if speed_unit == 'GB/s':
                        speed_value *= 1000  # Convert to MB/s
                    results['read_speed_mbps'] = round(speed_value, 2)
                else:
                    # Fallback calculation
                    size_bytes = int(test_size[:-1]) * 1024 * 1024  # Convert MB to bytes
                    results['read_speed_mbps'] = round((size_bytes / read_time) / (1024 * 1024), 2)

            # Clean up test file
            try:
                subprocess.run(['sudo', 'rm', '-f', test_file], check=False)
                subprocess.run(['sudo', 'rmdir', test_dir], check=False)
            except:
                pass  # Ignore cleanup errors

            return results

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Speed test timed out'}
        except Exception as e:
            # Clean up test file on error
            try:
                if 'test_file' in locals():
                    subprocess.run(['sudo', 'rm', '-f', test_file], check=False)
                if 'test_dir' in locals():
                    subprocess.run(['sudo', 'rmdir', test_dir], check=False)
            except:
                pass
            return {'success': False, 'error': str(e)}

    def _get_storage_info(self) -> Dict:
        """Get detailed storage information including NVMe detection"""

        storage_info = {
            'timestamp': time.time(),
            'devices': [],
            'nvme_devices': [],
            'unformatted_devices': [],
            'external_connected': False,
            'total_external_capacity': 0,
            'total_external_used': 0,
            'total_external_available': 0
        }

        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions()

            for partition in partitions:
                try:
                    # Get usage info
                    usage = psutil.disk_usage(partition.mountpoint)

                    # Determine if this is an NVMe device
                    is_nvme = 'nvme' in partition.device.lower()

                    # Determine if this is likely external storage
                    # Check if it's not root filesystem and is NVMe
                    is_external = (
                        is_nvme and
                        partition.mountpoint not in ['/', '/boot', '/boot/efi', '/boot/firmware'] and
                        not partition.mountpoint.startswith('/snap') and
                        not partition.mountpoint.startswith('/sys') and
                        not partition.mountpoint.startswith('/proc') and
                        not partition.mountpoint.startswith('/dev') and
                        not partition.mountpoint.startswith('/run')
                    )

                    # Additional check for external NVMe - look for PCIe NVMe devices
                    if is_nvme:
                        # Check if this is likely a PCIe NVMe (not eMMC or built-in storage)
                        device_path = partition.device
                        if '/dev/nvme' in device_path:
                            # Read NVMe info to determine if it's PCIe
                            try:
                                nvme_info = self._get_nvme_device_info(device_path)
                                if nvme_info.get('is_pcie', False):
                                    is_external = True
                            except:
                                pass

                    device_info = {
                        'name': os.path.basename(partition.device),
                        'mountpoint': partition.mountpoint,
                        'filesystem': partition.fstype,
                        'size': usage.total,
                        'used': usage.used,
                        'available': usage.free,
                        'use_percent': round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0,
                        'device_path': partition.device,
                        'is_nvme': is_nvme,
                        'is_external': is_external
                    }

                    storage_info['devices'].append(device_info)

                    # Add to NVMe devices list if applicable
                    if is_nvme:
                        storage_info['nvme_devices'].append(device_info)

                    # Add to external totals if external
                    if is_external:
                        storage_info['external_connected'] = True
                        storage_info['total_external_capacity'] += usage.total
                        storage_info['total_external_used'] += usage.used
                        storage_info['total_external_available'] += usage.free

                except (PermissionError, FileNotFoundError, OSError):
                    # Skip partitions we can't access
                    continue

            # Additional NVMe device detection using system info
            nvme_devices = self._detect_nvme_devices()
            if nvme_devices:
                storage_info['external_connected'] = True

            # Detect unformatted drives
            unformatted_devices = self._detect_unformatted_drives()
            storage_info['unformatted_devices'] = unformatted_devices
            if unformatted_devices:
                storage_info['external_connected'] = True

        except Exception as e:
            print(f"Error getting storage info: {e}")

        return storage_info

    def _get_nvme_device_info(self, device_path: str) -> Dict:
        """Get detailed info about an NVMe device"""
        nvme_info = {'is_pcie': False}

        try:
            # Extract NVMe device identifier (e.g., nvme0 from /dev/nvme0n1)
            match = re.search(r'nvme(\d+)', device_path)
            if match:
                nvme_num = match.group(1)

                # Check if this is a PCIe NVMe device
                pcie_path = f"/sys/class/nvme/nvme{nvme_num}/device/subsystem"
                if os.path.exists(pcie_path):
                    # Read the subsystem link to determine if it's PCIe
                    try:
                        subsystem = os.readlink(pcie_path)
                        if 'pci' in subsystem:
                            nvme_info['is_pcie'] = True
                    except:
                        pass

                # Try to read NVMe model and other info
                try:
                    model_path = f"/sys/class/nvme/nvme{nvme_num}/model"
                    if os.path.exists(model_path):
                        with open(model_path, 'r') as f:
                            nvme_info['model'] = f.read().strip()
                except:
                    pass

        except Exception as e:
            print(f"Error getting NVMe device info: {e}")

        return nvme_info

    def _detect_nvme_devices(self) -> List[Dict]:
        """Detect NVMe devices using system information"""
        nvme_devices = []

        try:
            # Look for NVMe devices in /sys/class/nvme/
            nvme_dirs = glob.glob('/sys/class/nvme/nvme*')

            for nvme_dir in nvme_dirs:
                if os.path.isdir(nvme_dir):
                    device_info = {}

                    # Get device model
                    model_file = os.path.join(nvme_dir, 'model')
                    if os.path.exists(model_file):
                        try:
                            with open(model_file, 'r') as f:
                                device_info['model'] = f.read().strip()
                        except:
                            pass

                    # Check if it's PCIe
                    device_subsystem = os.path.join(nvme_dir, 'device', 'subsystem')
                    if os.path.exists(device_subsystem):
                        try:
                            subsystem = os.readlink(device_subsystem)
                            device_info['is_pcie'] = 'pci' in subsystem
                        except:
                            device_info['is_pcie'] = False

                    nvme_devices.append(device_info)

        except Exception as e:
            print(f"Error detecting NVMe devices: {e}")

        return nvme_devices

    def _detect_unformatted_drives(self) -> List[Dict]:
        """Detect unformatted drives that could be formatted"""
        unformatted_devices = []

        try:
            # Use lsblk to find block devices without filesystems
            result = subprocess.run(['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,FSTYPE,MODEL,SERIAL'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lsblk_data = json.loads(result.stdout)

                for device in lsblk_data.get('blockdevices', []):
                    # Check if it's a disk (not partition) without filesystem
                    # Also check if it has children (partitions) - if it does, it's formatted
                    has_partitions = device.get('children') and len(device.get('children', [])) > 0
                    if (device.get('type') == 'disk' and
                        not device.get('fstype') and
                        not has_partitions and
                        'nvme' in device.get('name', '').lower()):

                        # Get device size in bytes
                        try:
                            size_result = subprocess.run(['lsblk', '-b', '-d', '-n', '-o', 'SIZE', f"/dev/{device['name']}"],
                                                       capture_output=True, text=True, timeout=5)
                            size_bytes = int(size_result.stdout.strip()) if size_result.returncode == 0 else 0
                        except:
                            size_bytes = 0

                        # Check if it's an NVMe PCIe device
                        is_pcie = False
                        if 'nvme' in device.get('name', ''):
                            nvme_match = re.search(r'nvme(\d+)', device['name'])
                            if nvme_match:
                                nvme_num = nvme_match.group(1)
                                pcie_path = f"/sys/class/nvme/nvme{nvme_num}/device/subsystem"
                                if os.path.exists(pcie_path):
                                    try:
                                        subsystem = os.readlink(pcie_path)
                                        is_pcie = 'pci' in subsystem
                                    except:
                                        pass

                        device_info = {
                            'name': device.get('name', ''),
                            'device_path': f"/dev/{device.get('name', '')}",
                            'size': size_bytes,
                            'model': device.get('model', 'Unknown'),
                            'serial': device.get('serial', 'Unknown'),
                            'is_nvme': 'nvme' in device.get('name', '').lower(),
                            'is_pcie': is_pcie,
                            'needs_formatting': True
                        }

                        unformatted_devices.append(device_info)

        except Exception as e:
            print(f"Error detecting unformatted drives: {e}")

        return unformatted_devices

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
            elif device_id == 'can':
                return self._handle_can_command(device, action, params, request_id)
            elif device_id == 'automation':
                return self._handle_automation_command(device, action, params, request_id)
            elif device_id == 'audio':
                return self._handle_audio_command(device, action, params, request_id)
            elif device_id == 'diag_agent':
                return self._handle_diag_agent_command(device, action, params, request_id)
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

            # Load model if different and YOLO is available
            current_model = device.inference_engine.model_name
            if current_model != model_name:
                if not device.inference_engine.load_model(model_name):
                    # Allow camera-only mode if YOLO model loading fails
                    pass  # Continue in camera-only mode

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

    def _handle_can_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle CAN interface commands"""

        if not CAN_AVAILABLE:
            return self._error_response("CAN interface not available", request_id)

        try:
            can_interface = get_can_interface()

            if action == 'get_status':
                status = can_interface.get_status()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=status
                )

            elif action == 'get_interfaces':
                interfaces = can_interface.get_available_interfaces()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'interfaces': interfaces}
                )

            elif action == 'connect':
                interface = params.get('interface', 'cantact')
                channel = params.get('channel', 'can0')
                bitrate = params.get('bitrate', 250000)

                config = CANBusConfig(
                    interface=interface,
                    channel=channel,
                    bitrate=bitrate
                )

                success = can_interface.connect(config)
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'connected': success,
                        'config': {
                            'interface': interface,
                            'channel': channel,
                            'bitrate': bitrate
                        }
                    }
                )

            elif action == 'disconnect':
                can_interface.disconnect()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'connected': False}
                )

            elif action == 'send_message':
                arbitration_id = params.get('arbitration_id')
                data = params.get('data', [])
                is_extended_id = params.get('is_extended_id', False)

                if arbitration_id is None:
                    return self._error_response("arbitration_id is required", request_id)

                # Convert hex string to int if needed
                if isinstance(arbitration_id, str):
                    arbitration_id = int(arbitration_id, 16) if arbitration_id.startswith('0x') else int(arbitration_id)

                # Convert hex strings in data array to ints
                data_bytes = []
                for byte in data:
                    if isinstance(byte, str):
                        data_bytes.append(int(byte, 16) if byte.startswith('0x') else int(byte))
                    else:
                        data_bytes.append(int(byte))

                success = can_interface.send_message(arbitration_id, data_bytes, is_extended_id)
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'sent': success,
                        'arbitration_id': hex(arbitration_id),
                        'data': [hex(b) for b in data_bytes]
                    }
                )

            elif action == 'get_messages':
                count = params.get('count', 50)
                messages = can_interface.get_messages(count)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'messages': messages,
                        'count': len(messages)
                    }
                )

            elif action == 'clear_messages':
                can_interface.clear_messages()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'cleared': True}
                )

            elif action == 'cli_command':
                command = params.get('command', '')
                result = can_interface.execute_cli_command(command)
                return APIResponse(
                    success=result.get('success', False),
                    timestamp=time.time(),
                    request_id=request_id,
                    data=result
                )

            else:
                return self._error_response(f"Unknown CAN action: {action}", request_id)

        except Exception as e:
            return self._error_response(f"CAN command error: {str(e)}", request_id)

    def _handle_automation_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle Automation engine commands"""

        if not AUTOMATION_AVAILABLE:
            return self._error_response("Automation engine not available", request_id)

        try:
            automation_engine = get_automation_engine()

            if action == 'get_status':
                status = automation_engine.get_status()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=status
                )

            elif action == 'create_environment':
                name = params.get('name', '')
                variables = params.get('variables', {})
                base_url = params.get('base_url', '')

                if not name:
                    return self._error_response("Environment name is required", request_id)

                env = automation_engine.create_environment(name, variables, base_url)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=env.to_dict()
                )

            elif action == 'list_environments':
                environments = [env.to_dict() for env in automation_engine.environments.values()]
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'environments': environments}
                )

            elif action == 'set_active_environment':
                env_id = params.get('environment_id')
                if not env_id:
                    return self._error_response("environment_id is required", request_id)

                success = automation_engine.set_active_environment(env_id)
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'active': success}
                )

            elif action == 'create_collection':
                name = params.get('name', '')
                description = params.get('description', '')

                if not name:
                    return self._error_response("Collection name is required", request_id)

                collection = automation_engine.create_collection(name, description)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=collection.to_dict()
                )

            elif action == 'list_collections':
                collections = [col.to_dict() for col in automation_engine.collections.values()]
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'collections': collections}
                )

            elif action == 'add_request':
                collection_id = params.get('collection_id')
                request_data = params.get('request', {})

                if not collection_id:
                    return self._error_response("collection_id is required", request_id)

                # Create automation request
                auto_request = AutomationRequest(
                    name=request_data.get('name', ''),
                    method=request_data.get('method', 'GET'),
                    url=request_data.get('url', ''),
                    headers=request_data.get('headers', {}),
                    body=request_data.get('body'),
                    body_type=request_data.get('body_type', 'json'),
                    auth_type=request_data.get('auth_type', 'none'),
                    auth_config=request_data.get('auth_config', {}),
                    timeout=request_data.get('timeout', 30.0)
                )

                success = automation_engine.add_request_to_collection(collection_id, auto_request)
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'added': success, 'request_id': auto_request.id}
                )

            elif action == 'execute_request':
                request_data = params.get('request', {})
                environment_id = params.get('environment_id')

                # Create temporary request
                auto_request = AutomationRequest(
                    name=request_data.get('name', ''),
                    method=request_data.get('method', 'GET'),
                    url=request_data.get('url', ''),
                    headers=request_data.get('headers', {}),
                    body=request_data.get('body'),
                    body_type=request_data.get('body_type', 'json'),
                    auth_type=request_data.get('auth_type', 'none'),
                    auth_config=request_data.get('auth_config', {}),
                    timeout=request_data.get('timeout', 30.0)
                )

                environment = None
                if environment_id and environment_id in automation_engine.environments:
                    environment = automation_engine.environments[environment_id]

                response = automation_engine.execute_request(auto_request, environment)
                return APIResponse(
                    success=response.error is None,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=response.to_dict()
                )

            elif action == 'run_collection':
                collection_id = params.get('collection_id')
                environment_id = params.get('environment_id')

                if not collection_id:
                    return self._error_response("collection_id is required", request_id)

                results = automation_engine.run_collection(collection_id, environment_id)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'results': [result.to_dict() for result in results],
                        'total': len(results),
                        'passed': sum(1 for r in results if r.success),
                        'failed': sum(1 for r in results if not r.success)
                    }
                )

            elif action == 'import_collection':
                collection_data = params.get('collection_data', {})
                collection = automation_engine.import_insomnia_collection(collection_data)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=collection.to_dict()
                )

            elif action == 'clear_results':
                automation_engine.clear_results()
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'cleared': True}
                )

            elif action == 'get_collection':
                collection_id = params.get('collection_id')
                if not collection_id:
                    return self._error_response("collection_id is required", request_id)

                if collection_id in automation_engine.collections:
                    collection = automation_engine.collections[collection_id]
                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=collection.to_dict()
                    )
                else:
                    return self._error_response("Collection not found", request_id)

            # JSON Library Management endpoints
            elif action == 'upload_json_library':
                name = params.get('name', '')
                content = params.get('content', {})
                library_type = params.get('type', 'schema')

                if not name:
                    return self._error_response("Library name is required", request_id)

                if not content:
                    return self._error_response("Library content is required", request_id)

                library = automation_engine.upload_json_library(name, content, library_type)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=library.to_dict()
                )

            elif action == 'list_json_libraries':
                libraries = [lib.to_dict() for lib in automation_engine.json_libraries.values()]
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'libraries': libraries}
                )

            elif action == 'get_json_library':
                library_id = params.get('library_id')
                if not library_id:
                    return self._error_response("library_id is required", request_id)

                if library_id in automation_engine.json_libraries:
                    library = automation_engine.json_libraries[library_id]
                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=library.to_dict()
                    )
                else:
                    return self._error_response("JSON library not found", request_id)

            elif action == 'delete_json_library':
                library_id = params.get('library_id')
                if not library_id:
                    return self._error_response("library_id is required", request_id)

                success = automation_engine.delete_json_library(library_id)
                return APIResponse(
                    success=success,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'deleted': success}
                )

            elif action == 'validate_json':
                schema_id = params.get('schema_id')
                data = params.get('data', {})

                if not schema_id:
                    return self._error_response("schema_id is required", request_id)

                result = automation_engine.validate_json_with_schema(schema_id, data)
                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=result
                )

            elif action == 'generate_mock_data':
                template_id = params.get('template_id')
                variables = params.get('variables', {})

                if not template_id:
                    return self._error_response("template_id is required", request_id)

                result = automation_engine.generate_mock_data(template_id, variables)
                return APIResponse(
                    success=result is not None,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={'mock_data': result} if result else None,
                    error="Failed to generate mock data" if result is None else None
                )

            else:
                return self._error_response(f"Unknown Automation action: {action}", request_id)

        except Exception as e:
            return self._error_response(f"Automation command error: {str(e)}", request_id)

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

        # Stop GPIO status indicator
        if hasattr(self, 'gpio_controller'):
            self.gpio_controller.stop_status_blink()

    def _handle_diag_agent_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle DIAG Agent (Log Monitor) commands"""
        if not DIAG_AGENT_AVAILABLE:
            return self._error_response("DIAG Agent not available", request_id)

        try:
            if action == 'get_status':
                # Get overall status of the DIAG Agent
                try:
                    # Initialize or get existing agent instance
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    # Get database status
                    db_manager = self._diag_agent.db_manager

                    # Query recent analyses
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()

                        # Get overall health score (average of recent analyses)
                        cursor.execute("""
                            SELECT AVG(health_score) FROM analyses
                            WHERE timestamp > datetime('now', '-24 hours') AND health_score IS NOT NULL
                        """)
                        avg_health = cursor.fetchone()[0] or 8

                        # Get monitored files count
                        monitored_files = len([f for f in self._diag_agent.config['log_files'] if f.get('enabled', True)])

                        # Get total analyses count
                        cursor.execute("SELECT COUNT(*) FROM analyses")
                        total_analyses = cursor.fetchone()[0]

                        # Get active alerts count
                        cursor.execute("SELECT COUNT(*) FROM alerts WHERE resolved = 0")
                        active_alerts = cursor.fetchone()[0]

                        # Get last analysis timestamp
                        cursor.execute("SELECT timestamp FROM analyses ORDER BY timestamp DESC LIMIT 1")
                        last_analysis = cursor.fetchone()
                        last_analysis = last_analysis[0] if last_analysis else None

                        # Get errors in last 24h
                        cursor.execute("""
                            SELECT SUM(error_count) FROM analyses
                            WHERE timestamp > datetime('now', '-24 hours')
                        """)
                        errors_24h = cursor.fetchone()[0] or 0

                        # Get average response time
                        cursor.execute("""
                            SELECT AVG(avg_response_time) FROM analyses
                            WHERE timestamp > datetime('now', '-24 hours') AND avg_response_time > 0
                        """)
                        avg_response_time = cursor.fetchone()[0] or 0

                    # Check AI agent status
                    ai_online = False
                    ai_status_message = "API key not configured"

                    try:
                        # Quick API key validation
                        if 'claude' in self._diag_agent.config and 'api_key' in self._diag_agent.config['claude']:
                            api_key = self._diag_agent.config['claude']['api_key']
                            if api_key and api_key != "your-api-key-here" and len(api_key) > 10:
                                # Test Claude API connection (quick test)
                                claude_analyzer = ClaudeAnalyzer(self._diag_agent.config)
                                test_response = claude_analyzer.analyze_logs("test", {'error_count': 0}, 'status_check')
                                ai_online = test_response is not None and 'error' not in str(test_response).lower()
                                ai_status_message = "Claude AI is online and accessible" if ai_online else "Claude API connection failed"
                            else:
                                ai_status_message = "API key not configured or invalid"
                    except Exception as e:
                        ai_online = False
                        ai_status_message = f"AI status check failed: {str(e)}"

                    status_data = {
                        'service_running': True,  # If we got here, service is running
                        'overall_health_score': round(avg_health, 1),
                        'monitored_files': monitored_files,
                        'total_analyses': total_analyses,
                        'active_alerts': active_alerts,
                        'last_analysis': last_analysis,
                        'errors_24h': int(errors_24h),
                        'avg_response_time': round(avg_response_time, 2) if avg_response_time else 0,
                        'api_calls_today': 0,  # TODO: Track API calls
                        'next_scheduled_analysis': None,  # TODO: Get from scheduler
                        'ai_online': ai_online,
                        'ai_status_message': ai_status_message
                    }

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=status_data
                    )

                except Exception as e:
                    return self._error_response(f"Failed to get DIAG Agent status: {str(e)}", request_id)

            elif action == 'get_analyses':
                limit = params.get('limit', 50)

                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    db_manager = self._diag_agent.db_manager

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, timestamp, log_file, health_score, error_count, warning_count,
                                   avg_response_time, ai_triggered, analysis_text
                            FROM analyses
                            ORDER BY timestamp DESC
                            LIMIT ?
                        """, (limit,))

                        analyses = []
                        for row in cursor.fetchall():
                            analysis_data = None
                            summary = None

                            if row[8]:  # analysis_text
                                try:
                                    analysis_json = json.loads(row[8])
                                    analysis_data = analysis_json
                                    summary = analysis_json.get('summary', 'No summary available')
                                except:
                                    summary = "Analysis data parsing error"

                            analyses.append({
                                'id': str(row[0]),
                                'timestamp': row[1],
                                'log_file': row[2],
                                'health_score': row[3] or 5,
                                'error_count': row[4] or 0,
                                'warning_count': row[5] or 0,
                                'avg_response_time': row[6] or 0,
                                'ai_triggered': bool(row[7]),
                                'summary': summary,
                                'analysis_data': analysis_data
                            })

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=analyses
                    )

                except Exception as e:
                    return self._error_response(f"Failed to get analyses: {str(e)}", request_id)

            elif action == 'get_alerts':
                resolved = params.get('resolved', False)

                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    db_manager = self._diag_agent.db_manager

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, timestamp, alert_type, severity, message, log_file, health_score, resolved
                            FROM alerts
                            WHERE resolved = ?
                            ORDER BY timestamp DESC
                        """, (1 if resolved else 0,))

                        alerts = []
                        for row in cursor.fetchall():
                            alerts.append({
                                'id': str(row[0]),
                                'timestamp': row[1],
                                'alert_type': row[2],
                                'severity': row[3],
                                'message': row[4],
                                'log_file': row[5],
                                'health_score': row[6],
                                'resolved': bool(row[7])
                            })

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=alerts
                    )

                except Exception as e:
                    return self._error_response(f"Failed to get alerts: {str(e)}", request_id)

            elif action == 'get_config':
                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    config = self._diag_agent.config.copy()

                    # Mask sensitive data
                    if 'claude' in config and 'api_key' in config['claude']:
                        config['claude']['api_key'] = '***masked***'

                    # Transform to match frontend interface
                    config_data = {
                        'claude_api_key': '***masked***',
                        'check_interval': config.get('monitoring', {}).get('check_interval_minutes', 15),
                        'error_threshold': config.get('analysis_thresholds', {}).get('error_count', 10),
                        'response_time_threshold': config.get('analysis_thresholds', {}).get('avg_response_time', 2000),
                        'high_activity_threshold': config.get('analysis_thresholds', {}).get('high_activity', 1000),
                        'email_enabled': config.get('email', {}).get('enabled', False),
                        'log_files': config.get('log_files', []),
                        'alert_thresholds': config.get('alert_thresholds', {})
                    }

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=config_data
                    )

                except Exception as e:
                    return self._error_response(f"Failed to get config: {str(e)}", request_id)

            elif action == 'start_analysis':
                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    # Run a single analysis cycle
                    results = self._diag_agent.run_analysis_cycle()

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={
                            'message': f'Analysis completed for {len(results)} log files',
                            'results': len(results)
                        }
                    )

                except Exception as e:
                    return self._error_response(f"Failed to start analysis: {str(e)}", request_id)

            elif action == 'send_test_alert':
                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    # Create a test analysis result
                    test_analysis = {
                        'health_score': 8,
                        'summary': 'Test alert from DIAG Agent HMI interface',
                        'critical_issues': [],
                        'recommendations': {'info': ['This is a test alert to verify email functionality']},
                        'trend_analysis': 'Test alert - all systems normal'
                    }
                    test_metrics = {'error_count': 0, 'avg_response_time': 150.0, 'total_lines': 100}

                    self._diag_agent.alert_manager.send_alert(
                        'test_alert', 'INFO', 'Test alert from HMI interface',
                        test_analysis, test_metrics, 'hmi_interface'
                    )

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={'message': 'Test alert sent successfully'}
                    )

                except Exception as e:
                    return self._error_response(f"Failed to send test alert: {str(e)}", request_id)

            elif action == 'validate_api_key':
                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    # Test Claude API connection
                    claude_analyzer = ClaudeAnalyzer(self._diag_agent.config)

                    # Simple test to validate API key
                    test_content = "Test log entry for API validation"
                    test_response = claude_analyzer.analyze_logs(test_content, {'error_count': 0}, 'test_validation')

                    ai_online = test_response is not None and 'error' not in str(test_response).lower()

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={
                            'ai_online': ai_online,
                            'api_key_valid': ai_online,
                            'message': 'API key is valid and Claude is accessible' if ai_online else 'API key invalid or Claude inaccessible'
                        }
                    )

                except Exception as e:
                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={
                            'ai_online': False,
                            'api_key_valid': False,
                            'message': f'API validation failed: {str(e)}'
                        }
                    )

            elif action == 'send_chat_message':
                try:
                    message = params.get('message', '')
                    if not message.strip():
                        return self._error_response("Chat message cannot be empty", request_id)

                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    # Get system context for AI
                    db_manager = self._diag_agent.db_manager
                    context = {}

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()

                        # Get recent analyses for context
                        cursor.execute("""
                            SELECT * FROM analyses
                            ORDER BY timestamp DESC
                            LIMIT 5
                        """)
                        context['recent_analyses'] = [dict(row) for row in cursor.fetchall()]

                        # Get active alerts
                        cursor.execute("""
                            SELECT * FROM alerts
                            WHERE resolved = 0
                            ORDER BY timestamp DESC
                        """)
                        context['active_alerts'] = [dict(row) for row in cursor.fetchall()]

                    # Use Claude analyzer for chat response
                    claude_analyzer = ClaudeAnalyzer(self._diag_agent.config)

                    # Create diagnostic prompt
                    chat_prompt = f"""
You are a diagnostic AI assistant for a Raspberry Pi CM5 system. A user has asked: "{message}"

System Context:
- Recent analyses: {len(context['recent_analyses'])}
- Active alerts: {len(context['active_alerts'])}

Please provide a helpful, technical response focusing on system diagnostics, monitoring, and troubleshooting.
If the user is asking about system health, refer to the context data provided.
Keep responses concise but informative.
"""

                    response = claude_analyzer.analyze_logs(chat_prompt, {}, 'chat_interaction')

                    if response and isinstance(response, dict):
                        ai_response = response.get('summary', 'I apologize, but I was unable to process your request properly.')
                    else:
                        ai_response = str(response) if response else 'I apologize, but I cannot provide a response at this time. Please check the AI service configuration.'

                    # Store chat message in database
                    chat_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()

                        # Create chat_messages table if it doesn't exist
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS chat_messages (
                                id TEXT PRIMARY KEY,
                                timestamp TEXT NOT NULL,
                                message TEXT NOT NULL,
                                response TEXT NOT NULL,
                                role TEXT NOT NULL,
                                context TEXT
                            )
                        """)

                        # Insert chat message
                        cursor.execute("""
                            INSERT INTO chat_messages (id, timestamp, message, response, role, context)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (chat_id, timestamp, message, ai_response, 'user', json.dumps(context)))

                    chat_message = {
                        'id': chat_id,
                        'timestamp': timestamp,
                        'message': message,
                        'response': ai_response,
                        'role': 'user',
                        'context': context
                    }

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=chat_message
                    )

                except Exception as e:
                    return self._error_response(f"Failed to send chat message: {str(e)}", request_id)

            elif action == 'get_chat_history':
                try:
                    limit = params.get('limit', 50)

                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    db_manager = self._diag_agent.db_manager

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()

                        # Create table if it doesn't exist
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS chat_messages (
                                id TEXT PRIMARY KEY,
                                timestamp TEXT NOT NULL,
                                message TEXT NOT NULL,
                                response TEXT NOT NULL,
                                role TEXT NOT NULL,
                                context TEXT
                            )
                        """)

                        cursor.execute("""
                            SELECT id, timestamp, message, response, role, context
                            FROM chat_messages
                            ORDER BY timestamp DESC
                            LIMIT ?
                        """, (limit,))

                        chat_history = []
                        for row in cursor.fetchall():
                            context_data = {}
                            try:
                                context_data = json.loads(row[5]) if row[5] else {}
                            except:
                                pass

                            chat_history.append({
                                'id': row[0],
                                'timestamp': row[1],
                                'message': row[2],
                                'response': row[3],
                                'role': row[4],
                                'context': context_data
                            })

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data=chat_history
                    )

                except Exception as e:
                    return self._error_response(f"Failed to get chat history: {str(e)}", request_id)

            elif action == 'clear_chat_history':
                try:
                    if not hasattr(self, '_diag_agent'):
                        self._diag_agent = LogMonitoringAgent()

                    db_manager = self._diag_agent.db_manager

                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM chat_messages")
                        deleted_count = cursor.rowcount

                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={
                            'success': True,
                            'deleted_messages': deleted_count
                        }
                    )

                except Exception as e:
                    return self._error_response(f"Failed to clear chat history: {str(e)}", request_id)

            else:
                return self._error_response(f"Unknown DIAG Agent action: {action}", request_id)

        except Exception as e:
            return self._error_response(f"DIAG Agent command failed: {str(e)}", request_id)

    def _handle_audio_command(self, device, action: str, params: Dict, request_id: str) -> APIResponse:
        """Handle Audio Output commands"""
        try:
            if action == 'get_status':
                # Get audio device status
                audio_available = device.test_audio_device() if device else False
                total_controls = len(device.available_controls) if device else 0

                # Count different types of controls
                volume_controls = len(device.get_volume_controls()) if device else 0
                switch_controls = len(device.get_switch_controls()) if device else 0
                eq_controls = len(device.get_eq_controls()) if device else 0

                status_data = {
                    'connected': audio_available,
                    'card_id': 0,
                    'card_name': device.device_name if device else 'hw:0',
                    'total_controls': total_controls,
                    'volume_controls': volume_controls,
                    'switch_controls': switch_controls,
                    'eq_controls': eq_controls,
                    'last_refresh': time.time()
                }

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=status_data
                )

            elif action == 'get_all_controls':
                # Get all available audio controls
                if not device:
                    return self._error_response("Audio device not available", request_id)

                controls = device.get_all_controls()

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=controls
                )

            elif action == 'get_volume_controls':
                # Get volume controls only
                if not device:
                    return self._error_response("Audio device not available", request_id)

                volume_controls_dict = device.get_volume_controls()

                # Convert to array format expected by React component
                volume_controls = []
                for name, control in volume_controls_dict.items():
                    volume_controls.append({
                        'name': name,
                        'type': control.get('type', 'volume'),
                        'value': control.get('value', '0')
                    })

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=volume_controls
                )

            elif action == 'get_switch_controls':
                # Get switch/enable controls
                if not device:
                    return self._error_response("Audio device not available", request_id)

                switch_controls_dict = device.get_switch_controls()

                # Convert to array format expected by React component
                switch_controls = []
                for name, control in switch_controls_dict.items():
                    switch_controls.append({
                        'name': name,
                        'type': control.get('type', 'switch'),
                        'value': control.get('value', '0')
                    })

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=switch_controls
                )

            elif action == 'get_eq_controls':
                # Get equalizer controls
                if not device:
                    return self._error_response("Audio device not available", request_id)

                eq_controls_dict = device.get_eq_controls()

                # Convert to array format expected by React component
                eq_controls = []
                for name, control in eq_controls_dict.items():
                    eq_controls.append({
                        'name': name,
                        'type': control.get('type', 'eq'),
                        'value': control.get('value', '0')
                    })

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data=eq_controls
                )

            elif action == 'set_control':
                # Set a specific audio control
                if not device:
                    return self._error_response("Audio device not available", request_id)

                control_name = params.get('control_name')
                value = params.get('value')

                if not control_name or value is None:
                    return self._error_response("Missing control_name or value parameter", request_id)

                success = device.set_control_value(control_name, str(value))

                if success:
                    # Get the updated value to confirm
                    updated_value = device.get_control_value(control_name)
                    return APIResponse(
                        success=True,
                        timestamp=time.time(),
                        request_id=request_id,
                        data={
                            'control_name': control_name,
                            'value': updated_value,
                            'set_success': True
                        }
                    )
                else:
                    return self._error_response(f"Failed to set control '{control_name}'", request_id)

            elif action == 'get_control':
                # Get value of a specific control
                if not device:
                    return self._error_response("Audio device not available", request_id)

                control_name = params.get('control_name')
                if not control_name:
                    return self._error_response("Missing control_name parameter", request_id)

                value = device.get_control_value(control_name)

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'control_name': control_name,
                        'value': value
                    }
                )

            elif action == 'refresh_controls':
                # Refresh the list of available controls
                if not device:
                    return self._error_response("Audio device not available", request_id)

                device._refresh_controls()
                control_count = len(device.available_controls)

                return APIResponse(
                    success=True,
                    timestamp=time.time(),
                    request_id=request_id,
                    data={
                        'message': f'Refreshed audio controls, found {control_count} controls',
                        'control_count': control_count
                    }
                )

            else:
                return self._error_response(f"Unknown audio action: {action}", request_id)

        except Exception as e:
            return self._error_response(f"Audio command failed: {str(e)}", request_id)

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

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down gracefully...")
        hmi_api.disconnect_all()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    # Start GPIO status indicator
    print(f"Starting GPIO status indicator on pin {hmi_api.gpio_controller.gpio_pin}")
    hmi_api.gpio_controller.start_status_blink()

    print(f"Starting HMI API server on http://{host}:{port}")

    try:
        app.run(host=host, port=port, debug=False)
    finally:
        # Cleanup on shutdown
        print("Shutting down HMI API server...")
        hmi_api.disconnect_all()

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
