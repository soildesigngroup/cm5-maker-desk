#!/usr/bin/env python3
"""
Audio System Management Module
Provides comprehensive audio control for the Raspberry Pi CM5 HMI system
Supports ALSA and PulseAudio backends with volume control, device selection, and status monitoring
"""

import subprocess
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os
import time

class AudioBackend(Enum):
    """Supported audio backends"""
    ALSA = "alsa"
    PULSEAUDIO = "pulseaudio"
    AUTO = "auto"

@dataclass
class AudioDevice:
    """Audio device information"""
    device_id: str
    name: str
    type: str  # 'output', 'input', 'duplex'
    default: bool = False
    active: bool = False
    volume: Optional[int] = None
    muted: bool = False
    channels: int = 2
    sample_rate: Optional[int] = None
    backend: str = "unknown"

@dataclass
class AudioStatus:
    """Current audio system status"""
    backend: str
    available_backends: List[str]
    devices: List[AudioDevice]
    default_output: Optional[str] = None
    default_input: Optional[str] = None
    master_volume: int = 50
    master_muted: bool = False
    system_sounds: bool = True

class AudioSystemError(Exception):
    """Audio system specific exceptions"""
    pass

class AudioSystem:
    """
    Audio System Management Class
    Provides unified interface for audio control across different backends
    """

    def __init__(self, preferred_backend: AudioBackend = AudioBackend.AUTO):
        self.logger = logging.getLogger(__name__)
        self.preferred_backend = preferred_backend
        self.current_backend = None
        self.devices = {}
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the best available audio backend"""
        if self.preferred_backend == AudioBackend.AUTO:
            # Try PulseAudio first, fallback to ALSA
            if self._is_pulseaudio_available():
                self.current_backend = AudioBackend.PULSEAUDIO
                self.logger.info("Using PulseAudio backend")
            elif self._is_alsa_available():
                self.current_backend = AudioBackend.ALSA
                self.logger.info("Using ALSA backend")
            else:
                raise AudioSystemError("No supported audio backend found")
        else:
            self.current_backend = self.preferred_backend
            if not self._is_backend_available(self.current_backend):
                raise AudioSystemError(f"Requested backend {self.current_backend.value} not available")

    def _is_pulseaudio_available(self) -> bool:
        """Check if PulseAudio is available and running"""
        try:
            result = subprocess.run(['pulseaudio', '--check'],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _is_alsa_available(self) -> bool:
        """Check if ALSA is available"""
        try:
            result = subprocess.run(['aplay', '--list-devices'],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _is_backend_available(self, backend: AudioBackend) -> bool:
        """Check if specific backend is available"""
        if backend == AudioBackend.PULSEAUDIO:
            return self._is_pulseaudio_available()
        elif backend == AudioBackend.ALSA:
            return self._is_alsa_available()
        return False

    def get_audio_status(self) -> AudioStatus:
        """Get current audio system status"""
        try:
            devices = self.list_audio_devices()
            available_backends = []

            if self._is_pulseaudio_available():
                available_backends.append("pulseaudio")
            if self._is_alsa_available():
                available_backends.append("alsa")

            master_volume, master_muted = self.get_master_volume()

            # Find default devices
            default_output = None
            default_input = None
            for device in devices:
                if device.default and device.type == 'output':
                    default_output = device.device_id
                elif device.default and device.type == 'input':
                    default_input = device.device_id

            return AudioStatus(
                backend=self.current_backend.value,
                available_backends=available_backends,
                devices=devices,
                default_output=default_output,
                default_input=default_input,
                master_volume=master_volume,
                master_muted=master_muted,
                system_sounds=True
            )
        except Exception as e:
            self.logger.error(f"Error getting audio status: {e}")
            raise AudioSystemError(f"Failed to get audio status: {e}")

    def list_audio_devices(self) -> List[AudioDevice]:
        """List all available audio devices"""
        if self.current_backend == AudioBackend.PULSEAUDIO:
            return self._list_pulseaudio_devices()
        elif self.current_backend == AudioBackend.ALSA:
            return self._list_alsa_devices()
        else:
            raise AudioSystemError("No audio backend initialized")

    def _list_pulseaudio_devices(self) -> List[AudioDevice]:
        """List PulseAudio devices"""
        devices = []
        try:
            # List sinks (output devices)
            result = subprocess.run(['pactl', 'list', 'short', 'sinks'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            device_id = parts[1]
                            name = parts[1].split('.')[-1] if '.' in parts[1] else parts[1]
                            volume, muted = self._get_pulseaudio_sink_volume(device_id)
                            devices.append(AudioDevice(
                                device_id=device_id,
                                name=name,
                                type='output',
                                volume=volume,
                                muted=muted,
                                backend='pulseaudio'
                            ))

            # List sources (input devices)
            result = subprocess.run(['pactl', 'list', 'short', 'sources'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and not '.monitor' in line:  # Skip monitor sources
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            device_id = parts[1]
                            name = parts[1].split('.')[-1] if '.' in parts[1] else parts[1]
                            devices.append(AudioDevice(
                                device_id=device_id,
                                name=name,
                                type='input',
                                backend='pulseaudio'
                            ))

        except Exception as e:
            self.logger.error(f"Error listing PulseAudio devices: {e}")

        return devices

    def _list_alsa_devices(self) -> List[AudioDevice]:
        """List ALSA devices"""
        devices = []
        try:
            # List playback devices
            result = subprocess.run(['aplay', '--list-devices'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'card' in line and 'device' in line:
                        match = re.search(r'card (\d+).*device (\d+)', line)
                        if match:
                            card, device = match.groups()
                            device_id = f"hw:{card},{device}"
                            name = f"Card {card} Device {device}"
                            devices.append(AudioDevice(
                                device_id=device_id,
                                name=name,
                                type='output',
                                backend='alsa'
                            ))

            # List capture devices
            result = subprocess.run(['arecord', '--list-devices'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'card' in line and 'device' in line:
                        match = re.search(r'card (\d+).*device (\d+)', line)
                        if match:
                            card, device = match.groups()
                            device_id = f"hw:{card},{device}"
                            name = f"Card {card} Device {device}"
                            devices.append(AudioDevice(
                                device_id=device_id,
                                name=name,
                                type='input',
                                backend='alsa'
                            ))

        except Exception as e:
            self.logger.error(f"Error listing ALSA devices: {e}")

        return devices

    def get_master_volume(self) -> Tuple[int, bool]:
        """Get master volume level and mute status"""
        if self.current_backend == AudioBackend.PULSEAUDIO:
            return self._get_pulseaudio_master_volume()
        elif self.current_backend == AudioBackend.ALSA:
            return self._get_alsa_master_volume()
        else:
            return 50, False

    def _get_pulseaudio_master_volume(self) -> Tuple[int, bool]:
        """Get PulseAudio master volume"""
        try:
            # Get default sink volume
            result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                                  capture_output=True, text=True, timeout=5)
            volume = 50
            if result.returncode == 0:
                # Parse volume percentage
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    volume = int(match.group(1))

            # Get mute status
            result = subprocess.run(['pactl', 'get-sink-mute', '@DEFAULT_SINK@'],
                                  capture_output=True, text=True, timeout=5)
            muted = False
            if result.returncode == 0:
                muted = 'yes' in result.stdout.lower()

            return volume, muted
        except Exception as e:
            self.logger.error(f"Error getting PulseAudio master volume: {e}")
            return 50, False

    def _get_alsa_master_volume(self) -> Tuple[int, bool]:
        """Get ALSA master volume"""
        try:
            result = subprocess.run(['amixer', 'get', 'Master'],
                                  capture_output=True, text=True, timeout=5)
            volume = 50
            muted = False

            if result.returncode == 0:
                # Parse volume percentage
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    volume = int(match.group(1))

                # Check mute status
                muted = '[off]' in result.stdout

            return volume, muted
        except Exception as e:
            self.logger.error(f"Error getting ALSA master volume: {e}")
            return 50, False

    def set_master_volume(self, volume: int) -> bool:
        """Set master volume level (0-100)"""
        volume = max(0, min(100, volume))

        if self.current_backend == AudioBackend.PULSEAUDIO:
            return self._set_pulseaudio_master_volume(volume)
        elif self.current_backend == AudioBackend.ALSA:
            return self._set_alsa_master_volume(volume)
        else:
            return False

    def _set_pulseaudio_master_volume(self, volume: int) -> bool:
        """Set PulseAudio master volume"""
        try:
            result = subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume}%'],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error setting PulseAudio master volume: {e}")
            return False

    def _set_alsa_master_volume(self, volume: int) -> bool:
        """Set ALSA master volume"""
        try:
            result = subprocess.run(['amixer', 'set', 'Master', f'{volume}%'],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error setting ALSA master volume: {e}")
            return False

    def set_master_mute(self, muted: bool) -> bool:
        """Set master mute status"""
        if self.current_backend == AudioBackend.PULSEAUDIO:
            return self._set_pulseaudio_master_mute(muted)
        elif self.current_backend == AudioBackend.ALSA:
            return self._set_alsa_master_mute(muted)
        else:
            return False

    def _set_pulseaudio_master_mute(self, muted: bool) -> bool:
        """Set PulseAudio master mute"""
        try:
            mute_arg = '1' if muted else '0'
            result = subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', mute_arg],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error setting PulseAudio master mute: {e}")
            return False

    def _set_alsa_master_mute(self, muted: bool) -> bool:
        """Set ALSA master mute"""
        try:
            mute_arg = 'mute' if muted else 'unmute'
            result = subprocess.run(['amixer', 'set', 'Master', mute_arg],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error setting ALSA master mute: {e}")
            return False

    def _get_pulseaudio_sink_volume(self, sink_name: str) -> Tuple[int, bool]:
        """Get volume and mute status for specific PulseAudio sink"""
        try:
            # Get volume
            result = subprocess.run(['pactl', 'get-sink-volume', sink_name],
                                  capture_output=True, text=True, timeout=5)
            volume = 50
            if result.returncode == 0:
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    volume = int(match.group(1))

            # Get mute status
            result = subprocess.run(['pactl', 'get-sink-mute', sink_name],
                                  capture_output=True, text=True, timeout=5)
            muted = False
            if result.returncode == 0:
                muted = 'yes' in result.stdout.lower()

            return volume, muted
        except Exception:
            return 50, False

    def set_default_output_device(self, device_id: str) -> bool:
        """Set default output device"""
        if self.current_backend == AudioBackend.PULSEAUDIO:
            try:
                result = subprocess.run(['pactl', 'set-default-sink', device_id],
                                      capture_output=True, timeout=5)
                return result.returncode == 0
            except Exception as e:
                self.logger.error(f"Error setting default output device: {e}")
                return False
        elif self.current_backend == AudioBackend.ALSA:
            # ALSA default device setting is more complex, typically done via .asoundrc
            self.logger.warning("ALSA default device setting not implemented")
            return False
        else:
            return False

    def play_test_sound(self, device_id: Optional[str] = None) -> bool:
        """Play a test sound on specified device or default output"""
        try:
            if self.current_backend == AudioBackend.PULSEAUDIO:
                cmd = ['paplay']
                if device_id:
                    cmd.extend(['--device', device_id])
                cmd.append('/usr/share/sounds/alsa/Front_Left.wav')
            else:  # ALSA
                cmd = ['aplay']
                if device_id:
                    cmd.extend(['-D', device_id])
                cmd.append('/usr/share/sounds/alsa/Front_Left.wav')

            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error playing test sound: {e}")
            return False

    def get_audio_info(self) -> Dict[str, Any]:
        """Get comprehensive audio system information"""
        try:
            status = self.get_audio_status()
            return {
                'status': asdict(status),
                'backend_info': {
                    'current': self.current_backend.value,
                    'pulseaudio_running': self._is_pulseaudio_available(),
                    'alsa_available': self._is_alsa_available()
                },
                'system_info': self._get_system_audio_info()
            }
        except Exception as e:
            self.logger.error(f"Error getting audio info: {e}")
            return {'error': str(e)}

    def _get_system_audio_info(self) -> Dict[str, Any]:
        """Get system-level audio information"""
        info = {}
        try:
            # Check for audio hardware
            result = subprocess.run(['lspci', '-v'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                audio_devices = []
                for line in result.stdout.split('\n'):
                    if 'audio' in line.lower() or 'sound' in line.lower():
                        audio_devices.append(line.strip())
                info['pci_audio_devices'] = audio_devices

            # Check loaded audio modules
            result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                audio_modules = []
                for line in result.stdout.split('\n'):
                    if any(module in line for module in ['snd', 'audio', 'sound']):
                        audio_modules.append(line.split()[0])
                info['loaded_audio_modules'] = audio_modules

        except Exception as e:
            self.logger.error(f"Error getting system audio info: {e}")
            info['error'] = str(e)

        return info

# Global audio system instance
_audio_system = None

def get_audio_system(backend: AudioBackend = AudioBackend.AUTO) -> AudioSystem:
    """Get or create global audio system instance"""
    global _audio_system
    if _audio_system is None:
        _audio_system = AudioSystem(backend)
    return _audio_system

# Testing and demo functions
def test_audio_system():
    """Test audio system functionality"""
    print("Testing Audio System...")

    try:
        audio = get_audio_system()
        print(f"✅ Audio system initialized with {audio.current_backend.value} backend")

        # Test getting status
        status = audio.get_audio_status()
        print(f"✅ Audio status: {len(status.devices)} devices found")

        # Test volume control
        current_volume, muted = audio.get_master_volume()
        print(f"✅ Current volume: {current_volume}%, muted: {muted}")

        # List devices
        devices = audio.list_audio_devices()
        print(f"✅ Found {len(devices)} audio devices:")
        for device in devices:
            print(f"   - {device.name} ({device.type}) - {device.backend}")

        print("✅ Audio system test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Audio system test failed: {e}")
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Run tests
    test_audio_system()