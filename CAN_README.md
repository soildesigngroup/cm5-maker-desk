# CAN Bus Interface

This application now includes full CAN (Controller Area Network) bus support using the open-source CANtact implementation and python-can library.

## Features

### Backend (Python)
- **CAN Interface Module** (`can_interface.py`): Core CAN communication handling
- **CANtact Integration**: Support for CANtact hardware and other CAN interfaces
- **Multiple Interface Support**: Supports various CAN hardware (CANtact, SocketCAN, PCAN, Vector, etc.)
- **Message History**: Automatic logging and retrieval of CAN messages
- **CLI Commands**: Built-in command-line interface for CAN operations
- **WebSocket/HTTP API**: Real-time CAN communication via web interface

### Frontend (React/TypeScript)
- **CAN Tab**: Dedicated interface positioned before AI Vision tab
- **Connection Management**: Easy interface selection and configuration
- **Message Sending**: Interactive CAN message transmission
- **Real-time Monitoring**: Live CAN message display with auto-refresh
- **CLI Console**: Toggle-able command-line interface for advanced operations
- **Message History**: Persistent message logging and viewing

## Installation

### Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `python-can`: Core CAN bus library
- `cantact`: CANtact hardware support
- `flask`: Web API framework
- `flask-cors`: CORS support
- `websockets`: Real-time communication

### Hardware Support

#### CANtact
- Official CANtact hardware devices
- USB CAN interface
- Cross-platform support (Windows, macOS, Linux)

#### SocketCAN (Linux)
- Native Linux CAN support
- Virtual CAN interfaces for testing
- Hardware CAN controllers

#### Other Interfaces
- PCAN (Peak System)
- Vector CANoe/CANalyzer
- Serial CAN adapters

## Usage

### Starting the Server
```bash
# HTTP API server (port 8081)
python3 hmi_json_api.py server

# WebSocket server (port 8081)
python3 hmi_json_api.py websocket
```

### Web Interface
1. Navigate to the **CAN** tab in the HMI interface
2. Select your CAN interface (default: CANtact)
3. Configure channel and bitrate
4. Click **Connect** to establish CAN bus connection
5. Use the interface to send/receive messages

### CLI Console
- Toggle the CLI console using the **Enable** switch
- Available commands:
  - `status` - Show connection status
  - `connect <interface> [channel] [bitrate]` - Connect to CAN bus
  - `disconnect` - Disconnect from CAN bus
  - `send <id> <data_bytes...>` - Send CAN message
  - `clear` - Clear message history
  - `help` - Show available commands

### API Endpoints

#### CAN Status
```http
GET /api/command
Content-Type: application/json

{
  "action": "get_status",
  "device": "can",
  "request_id": "can_status_123"
}
```

#### Connect to CAN Bus
```http
GET /api/command
Content-Type: application/json

{
  "action": "connect",
  "device": "can",
  "params": {
    "interface": "cantact",
    "channel": "can0",
    "bitrate": 250000
  },
  "request_id": "can_connect_123"
}
```

#### Send CAN Message
```http
GET /api/command
Content-Type: application/json

{
  "action": "send_message",
  "device": "can",
  "params": {
    "arbitration_id": "0x123",
    "data": ["0x01", "0x02", "0x03", "0x04"],
    "is_extended_id": false
  },
  "request_id": "can_send_123"
}
```

#### Get Messages
```http
GET /api/command
Content-Type: application/json

{
  "action": "get_messages",
  "device": "can",
  "params": {
    "count": 50
  },
  "request_id": "can_messages_123"
}
```

## Configuration

### Default Settings
- **Interface**: CANtact
- **Channel**: can0
- **Bitrate**: 250000 bps (250 kbps)
- **Extended ID**: Disabled
- **Receive Own Messages**: Enabled

### Supported Bitrates
- 125 kbps
- 250 kbps (default)
- 500 kbps
- 1 Mbps

## Testing

### Without Hardware
```bash
python3 test_can_interface.py
```

This test will verify the CAN interface functionality without requiring actual hardware.

### With Virtual CAN (Linux)
```bash
# Create virtual CAN interface
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Test with virtual interface
python3 test_can_interface.py
```

## Architecture

### Backend Components
- `can_interface.py`: Core CAN functionality
- `hmi_json_api.py`: API integration
- `CANInterface` class: Main interface management
- `CANMessage` dataclass: Message structure
- `CANBusConfig` dataclass: Configuration structure

### Frontend Components
- `src/components/hmi/CAN.tsx`: React component
- `src/services/hmi-api.ts`: TypeScript API client
- CAN types and interfaces
- Real-time message handling

## Security Considerations
- CAN bus access requires appropriate system permissions
- Message validation prevents malformed CAN frames
- Connection timeout handling
- Error logging and handling

## Troubleshooting

### Common Issues
1. **Permission Denied**: Ensure user has access to CAN hardware
2. **No Device Found**: Verify CAN hardware is connected and recognized
3. **Connection Failed**: Check interface name and hardware compatibility
4. **Import Errors**: Install all required dependencies

### Debug Mode
Enable detailed logging by setting the Python logging level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with CANtact

This implementation follows the CANtact project structure and API patterns:
- Compatible with CANtact hardware devices
- Uses python-can library for standardized interface
- Supports CANtact-specific features and configurations
- Cross-platform compatibility maintained

For more information about CANtact, visit: https://github.com/linklayer/cantact