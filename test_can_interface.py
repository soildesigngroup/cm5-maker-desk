#!/usr/bin/env python3
"""
Test script for CAN interface functionality
This script demonstrates basic CAN operations
"""

import time
import json
from can_interface import get_can_interface, CANBusConfig

def test_can_interface():
    """Test basic CAN interface functionality"""
    print("=" * 50)
    print("CAN Interface Test")
    print("=" * 50)

    # Get CAN interface instance
    can_interface = get_can_interface()

    # Test 1: Get available interfaces
    print("\n1. Available CAN interfaces:")
    interfaces = can_interface.get_available_interfaces()
    for i, interface in enumerate(interfaces):
        print(f"   {i+1}. {interface}")

    # Test 2: Get status (should be disconnected initially)
    print("\n2. Initial status:")
    status = can_interface.get_status()
    print(f"   Connected: {status['connected']}")
    print(f"   Available interfaces: {status['available_interfaces']}")

    # Test 3: Test CLI commands
    print("\n3. Testing CLI commands:")

    # Help command
    result = can_interface.execute_cli_command("help")
    print("   Help command result:")
    if result['success']:
        print(f"   {result['message']}")
    else:
        print(f"   Error: {result['error']}")

    # Status command
    result = can_interface.execute_cli_command("status")
    print("   Status command result:")
    if result['success']:
        print(f"   Data: {json.dumps(result['data'], indent=6)}")
    else:
        print(f"   Error: {result['error']}")

    # Test 4: Try to connect (this will likely fail without hardware)
    print("\n4. Testing connection (may fail without CAN hardware):")
    config = CANBusConfig(
        interface='cantact',
        channel='can0',
        bitrate=250000
    )

    success = can_interface.connect(config)
    print(f"   Connection attempt: {'Success' if success else 'Failed (expected without hardware)'}")

    if success:
        print("   Connected! Testing message operations...")

        # Send a test message
        success = can_interface.send_message(
            arbitration_id=0x123,
            data=[0x01, 0x02, 0x03, 0x04]
        )
        print(f"   Send message: {'Success' if success else 'Failed'}")

        # Get messages
        messages = can_interface.get_messages(10)
        print(f"   Retrieved {len(messages)} messages")

        # Disconnect
        can_interface.disconnect()
        print("   Disconnected")
    else:
        print("   Note: This is expected if no CAN hardware is connected")

    # Test 5: Final status
    print("\n5. Final status:")
    final_status = can_interface.get_status()
    print(f"   Connected: {final_status['connected']}")
    print(f"   Message count: {final_status['message_count']}")

    print("\n" + "=" * 50)
    print("CAN Interface Test Complete")
    print("=" * 50)

if __name__ == "__main__":
    test_can_interface()