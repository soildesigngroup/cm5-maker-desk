#!/usr/bin/env python3
"""
CAN Interface Module
Provides CAN bus communication capabilities using python-can library
Supports CANtact and other CAN interfaces
"""

import can
import time
import threading
import queue
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CANMessage:
    """CAN message structure"""
    arbitration_id: int
    data: List[int]
    timestamp: float
    is_extended_id: bool = False
    is_remote_frame: bool = False
    dlc: int = 8

    def to_dict(self) -> Dict[str, Any]:
        return {
            'arbitration_id': hex(self.arbitration_id),
            'data': [hex(b) for b in self.data],
            'timestamp': self.timestamp,
            'is_extended_id': self.is_extended_id,
            'is_remote_frame': self.is_remote_frame,
            'dlc': self.dlc,
            'formatted_time': datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S.%f')[:-3]
        }

@dataclass
class CANBusConfig:
    """CAN bus configuration"""
    interface: str = 'cantact'
    channel: str = 'can0'
    bitrate: int = 250000
    receive_own_messages: bool = True
    filters: Optional[List[Dict]] = None

class CANInterface:
    """CAN Interface management class"""

    def __init__(self):
        self.bus: Optional[can.Bus] = None
        self.config: Optional[CANBusConfig] = None
        self.is_connected = False
        self.message_queue = queue.Queue(maxsize=1000)
        self.receive_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.message_listeners: List[Callable] = []
        self.message_history: List[CANMessage] = []
        self.max_history = 1000

    def get_available_interfaces(self) -> List[str]:
        """Get list of available CAN interfaces"""
        interfaces = []

        # Check for common interfaces
        common_interfaces = ['cantact', 'socketcan', 'pcan', 'vector', 'serial']

        for interface in common_interfaces:
            try:
                # Try to create a bus instance to check availability
                test_bus = can.Bus(interface=interface, channel='test', dry_run=True)
                interfaces.append(interface)
                test_bus.shutdown()
            except Exception:
                continue

        return interfaces if interfaces else ['cantact']  # Default fallback

    def connect(self, config: CANBusConfig) -> bool:
        """Connect to CAN bus"""
        try:
            if self.is_connected:
                self.disconnect()

            self.config = config

            # Create bus instance
            bus_kwargs = {
                'interface': config.interface,
                'channel': config.channel,
                'bitrate': config.bitrate,
                'receive_own_messages': config.receive_own_messages
            }

            if config.filters:
                bus_kwargs['can_filters'] = config.filters

            self.bus = can.Bus(**bus_kwargs)
            self.is_connected = True

            # Start receive thread
            self.stop_event.clear()
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()

            logger.info(f"Connected to CAN bus: {config.interface}:{config.channel} @ {config.bitrate}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to CAN bus: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from CAN bus"""
        try:
            if self.receive_thread and self.receive_thread.is_alive():
                self.stop_event.set()
                self.receive_thread.join(timeout=2)

            if self.bus:
                self.bus.shutdown()
                self.bus = None

            self.is_connected = False
            logger.info("Disconnected from CAN bus")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def send_message(self, arbitration_id: int, data: List[int],
                    is_extended_id: bool = False, timeout: float = 1.0) -> bool:
        """Send CAN message"""
        try:
            if not self.is_connected or not self.bus:
                raise Exception("Not connected to CAN bus")

            # Validate data
            if len(data) > 8:
                raise ValueError("CAN data length cannot exceed 8 bytes")

            # Create message
            msg = can.Message(
                arbitration_id=arbitration_id,
                data=data,
                is_extended_id=is_extended_id
            )

            # Send message
            self.bus.send(msg, timeout=timeout)

            # Add to history
            can_msg = CANMessage(
                arbitration_id=arbitration_id,
                data=data,
                timestamp=time.time(),
                is_extended_id=is_extended_id,
                dlc=len(data)
            )
            self._add_to_history(can_msg)

            logger.debug(f"Sent CAN message: ID={hex(arbitration_id)}, Data={[hex(b) for b in data]}")
            return True

        except Exception as e:
            logger.error(f"Failed to send CAN message: {e}")
            return False

    def _receive_messages(self):
        """Background thread for receiving messages"""
        try:
            while not self.stop_event.is_set() and self.bus:
                try:
                    # Receive message with timeout
                    msg = self.bus.recv(timeout=0.1)
                    if msg:
                        can_msg = CANMessage(
                            arbitration_id=msg.arbitration_id,
                            data=list(msg.data),
                            timestamp=msg.timestamp if msg.timestamp else time.time(),
                            is_extended_id=msg.is_extended_id,
                            is_remote_frame=msg.is_remote_frame,
                            dlc=msg.dlc
                        )

                        # Add to history and queue
                        self._add_to_history(can_msg)

                        try:
                            self.message_queue.put_nowait(can_msg)
                        except queue.Full:
                            # Remove oldest message if queue is full
                            try:
                                self.message_queue.get_nowait()
                                self.message_queue.put_nowait(can_msg)
                            except queue.Empty:
                                pass

                        # Notify listeners
                        for listener in self.message_listeners:
                            try:
                                listener(can_msg)
                            except Exception as e:
                                logger.error(f"Error in message listener: {e}")

                except Exception as e:
                    if not self.stop_event.is_set():
                        logger.error(f"Error receiving CAN message: {e}")
                        time.sleep(0.1)

        except Exception as e:
            logger.error(f"Receive thread error: {e}")

    def _add_to_history(self, message: CANMessage):
        """Add message to history"""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_messages(self, count: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages"""
        recent_messages = self.message_history[-count:] if count > 0 else self.message_history
        return [msg.to_dict() for msg in recent_messages]

    def clear_messages(self):
        """Clear message history"""
        self.message_history.clear()
        # Clear queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break

    def add_message_listener(self, listener: Callable[[CANMessage], None]):
        """Add message listener"""
        self.message_listeners.append(listener)

    def remove_message_listener(self, listener: Callable[[CANMessage], None]):
        """Remove message listener"""
        if listener in self.message_listeners:
            self.message_listeners.remove(listener)

    def get_status(self) -> Dict[str, Any]:
        """Get interface status"""
        return {
            'connected': self.is_connected,
            'config': asdict(self.config) if self.config else None,
            'message_count': len(self.message_history),
            'queue_size': self.message_queue.qsize(),
            'available_interfaces': self.get_available_interfaces()
        }

    def execute_cli_command(self, command: str) -> Dict[str, Any]:
        """Execute CLI-style commands"""
        try:
            parts = command.strip().split()
            if not parts:
                return {'success': False, 'error': 'Empty command'}

            cmd = parts[0].lower()

            if cmd == 'status':
                return {'success': True, 'data': self.get_status()}

            elif cmd == 'connect':
                if len(parts) < 2:
                    return {'success': False, 'error': 'Usage: connect <interface> [channel] [bitrate]'}

                interface = parts[1]
                channel = parts[2] if len(parts) > 2 else 'can0'
                bitrate = int(parts[3]) if len(parts) > 3 else 250000

                config = CANBusConfig(interface=interface, channel=channel, bitrate=bitrate)
                success = self.connect(config)
                return {'success': success, 'message': f'Connected to {interface}:{channel}' if success else 'Connection failed'}

            elif cmd == 'disconnect':
                self.disconnect()
                return {'success': True, 'message': 'Disconnected'}

            elif cmd == 'send':
                if len(parts) < 3:
                    return {'success': False, 'error': 'Usage: send <id> <data_bytes...>'}

                try:
                    arbitration_id = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    data = [int(b, 16) if b.startswith('0x') else int(b) for b in parts[2:]]

                    success = self.send_message(arbitration_id, data)
                    return {'success': success, 'message': f'Sent message ID={hex(arbitration_id)}' if success else 'Send failed'}

                except ValueError as e:
                    return {'success': False, 'error': f'Invalid parameters: {e}'}

            elif cmd == 'clear':
                self.clear_messages()
                return {'success': True, 'message': 'Message history cleared'}

            elif cmd == 'help':
                help_text = """
Available commands:
  status - Show connection status
  connect <interface> [channel] [bitrate] - Connect to CAN bus
  disconnect - Disconnect from CAN bus
  send <id> <data_bytes...> - Send CAN message
  clear - Clear message history
  help - Show this help
                """.strip()
                return {'success': True, 'message': help_text}

            else:
                return {'success': False, 'error': f'Unknown command: {cmd}'}

        except Exception as e:
            return {'success': False, 'error': f'Command error: {str(e)}'}

# Global CAN interface instance
_can_interface = None

def get_can_interface() -> CANInterface:
    """Get global CAN interface instance"""
    global _can_interface
    if _can_interface is None:
        _can_interface = CANInterface()
    return _can_interface