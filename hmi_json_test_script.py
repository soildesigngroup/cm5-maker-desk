#!/usr/bin/env python3
"""
HMI JSON API Test Script
Comprehensive testing and demonstration of all API features
"""

import json
import time
import threading
import sys
import argparse
from hmi_json_api import HMIJsonAPI, create_api_server, create_websocket_server

class HMITestRunner:
    """Test runner for HMI JSON API"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.hmi = None
        self.test_results = {}
        
    def log(self, message):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def send_command(self, command, description=""):
        """Send a command and return parsed response"""
        if description:
            self.log(f"Test: {description}")
        
        if isinstance(command, dict):
            command_str = json.dumps(command)
        else:
            command_str = command
            
        self.log(f"Command: {command_str}")
        
        try:
            response_str = self.hmi.process_json_command(command_str)
            response = json.loads(response_str)
            
            if self.verbose:
                if response.get('success'):
                    self.log(f"✓ Success: {json.dumps(response.get('data', {}), indent=2)}")
                else:
                    self.log(f"✗ Error: {response.get('error', 'Unknown error')}")
            
            return response
            
        except Exception as e:
            self.log(f"✗ Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def test_system_commands(self):
        """Test system-level commands"""
        self.log("\n" + "="*60)
        self.log("TESTING SYSTEM COMMANDS")
        self.log("="*60)
        
        tests = [
            {
                "command": {"action": "get_system_status"},
                "description": "Get system status",
                "test_name": "system_status"
            },
            {
                "command": {"action": "get_device_list"},
                "description": "Get device list and capabilities",
                "test_name": "device_list"
            }
        ]
        
        for test in tests:
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_adc_commands(self):
        """Test ADC-related commands"""
        if 'adc' not in self.hmi.devices:
            self.log("ADC not available, skipping ADC tests")
            return
            
        self.log("\n" + "="*60)
        self.log("TESTING ADC COMMANDS")
        self.log("="*60)
        
        tests = [
            {
                "command": {"action": "read_channel", "device": "adc", "params": {"channel": 0}},
                "description": "Read ADC channel 0",
                "test_name": "adc_single_channel"
            },
            {
                "command": {"action": "read_all_channels", "device": "adc"},
                "description": "Read all ADC channels",
                "test_name": "adc_all_channels"
            },
            {
                "command": {"action": "set_vref", "device": "adc", "params": {"vref": 3.3}},
                "description": "Set ADC reference voltage to 3.3V",
                "test_name": "adc_set_vref"
            }
        ]
        
        for test in tests:
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_io_commands(self):
        """Test I/O expander commands"""
        if 'io' not in self.hmi.devices:
            self.log("I/O expander not available, skipping I/O tests")
            return
            
        self.log("\n" + "="*60)
        self.log("TESTING I/O EXPANDER COMMANDS")
        self.log("="*60)
        
        tests = [
            {
                "command": {"action": "configure_pin", "device": "io", "params": {"pin": 0, "direction": "output", "pullup": False}},
                "description": "Configure pin 0 as output",
                "test_name": "io_configure_output"
            },
            {
                "command": {"action": "write_pin", "device": "io", "params": {"pin": 0, "state": True}},
                "description": "Set pin 0 HIGH",
                "test_name": "io_write_high"
            },
            {
                "command": {"action": "read_pin", "device": "io", "params": {"pin": 0}},
                "description": "Read pin 0 state",
                "test_name": "io_read_pin"
            },
            {
                "command": {"action": "write_pin", "device": "io", "params": {"pin": 0, "state": False}},
                "description": "Set pin 0 LOW",
                "test_name": "io_write_low"
            },
            {
                "command": {"action": "read_all_pins", "device": "io"},
                "description": "Read all pin states",
                "test_name": "io_read_all"
            }
        ]
        
        for test in tests:
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_rtc_commands(self):
        """Test RTC commands"""
        if 'rtc' not in self.hmi.devices:
            self.log("RTC not available, skipping RTC tests")
            return
            
        self.log("\n" + "="*60)
        self.log("TESTING RTC COMMANDS")
        self.log("="*60)
        
        tests = [
            {
                "command": {"action": "read_datetime", "device": "rtc"},
                "description": "Read current date/time",
                "test_name": "rtc_read_datetime"
            },
            {
                "command": {"action": "set_clkout", "device": "rtc", "params": {"frequency": 6}},
                "description": "Set CLKOUT to 1Hz",
                "test_name": "rtc_set_clkout"
            }
        ]
        
        for test in tests:
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_fan_commands(self):
        """Test fan controller commands"""
        if 'fan' not in self.hmi.devices:
            self.log("Fan controller not available, skipping fan tests")
            return
            
        self.log("\n" + "="*60)
        self.log("TESTING FAN CONTROLLER COMMANDS")
        self.log("="*60)
        
        tests = [
            {
                "command": {"action": "set_pwm", "device": "fan", "params": {"duty_cycle": 0}},
                "description": "Set fan PWM to 0% (stop)",
                "test_name": "fan_stop"
            },
            {
                "command": {"action": "read_rpm", "device": "fan"},
                "description": "Read fan RPM and status",
                "test_name": "fan_read_stopped"
            },
            {
                "command": {"action": "set_pwm", "device": "fan", "params": {"duty_cycle": 50}},
                "description": "Set fan PWM to 50%",
                "test_name": "fan_set_50_percent"
            },
            {
                "command": {"action": "read_rpm", "device": "fan"},
                "description": "Read fan RPM at 50%",
                "test_name": "fan_read_50_percent",
                "wait": 3  # Wait for fan to stabilize
            },
            {
                "command": {"action": "configure", "device": "fan", "params": {"rpm_control": True, "poles": 2, "edges": 1}},
                "description": "Configure fan for RPM control",
                "test_name": "fan_configure_rpm"
            },
            {
                "command": {"action": "set_rpm", "device": "fan", "params": {"target_rpm": 1500}},
                "description": "Set target RPM to 1500",
                "test_name": "fan_set_rpm_1500"
            },
            {
                "command": {"action": "read_rpm", "device": "fan"},
                "description": "Read fan RPM in RPM control mode",
                "test_name": "fan_read_rpm_control",
                "wait": 3
            },
            {
                "command": {"action": "set_pwm", "device": "fan", "params": {"duty_cycle": 0}},
                "description": "Stop fan after testing",
                "test_name": "fan_final_stop"
            }
        ]
        
        for test in tests:
            if test.get("wait"):
                self.log(f"Waiting {test['wait']} seconds...")
                time.sleep(test["wait"])
                
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_eeprom_commands(self):
        """Test EEPROM commands"""
        if 'eeprom' not in self.hmi.devices:
            self.log("EEPROM not available, skipping EEPROM tests")
            return
            
        self.log("\n" + "="*60)
        self.log("TESTING EEPROM COMMANDS")
        self.log("="*60)
        
        test_address = 0x1000  # Use address 0x1000 for testing
        
        tests = [
            {
                "command": {"action": "get_info", "device": "eeprom"},
                "description": "Get EEPROM information",
                "test_name": "eeprom_info"
            },
            {
                "command": {"action": "write_string", "device": "eeprom", "params": {"address": test_address, "text": "JSON API Test"}},
                "description": f"Write test string to address 0x{test_address:04X}",
                "test_name": "eeprom_write_string"
            },
            {
                "command": {"action": "read_string", "device": "eeprom", "params": {"address": test_address, "max_length": 50}},
                "description": f"Read string from address 0x{test_address:04X}",
                "test_name": "eeprom_read_string"
            },
            {
                "command": {"action": "write", "device": "eeprom", "params": {"address": test_address + 100, "data": [0xDE, 0xAD, 0xBE, 0xEF]}},
                "description": "Write test bytes",
                "test_name": "eeprom_write_bytes"
            },
            {
                "command": {"action": "read", "device": "eeprom", "params": {"address": test_address + 100, "length": 4}},
                "description": "Read test bytes",
                "test_name": "eeprom_read_bytes"
            },
            {
                "command": {"action": "test", "device": "eeprom", "params": {"address": test_address + 200, "size": 256}},
                "description": "Test EEPROM functionality",
                "test_name": "eeprom_memory_test"
            }
        ]
        
        for test in tests:
            response = self.send_command(test["command"], test["description"])
            self.test_results[test["test_name"]] = response.get("success", False)
    
    def test_monitoring(self):
        """Test monitoring functionality"""
        self.log("\n" + "="*60)
        self.log("TESTING MONITORING FUNCTIONALITY")
        self.log("="*60)
        
        # Start monitoring
        response = self.send_command(
            {"action": "start_monitoring", "params": {"interval": 1.0}},
            "Start monitoring with 1 second interval"
        )
        self.test_results["monitoring_start"] = response.get("success", False)
        
        if response.get("success"):
            # Wait and collect monitoring data
            self.log("Collecting monitoring data for 5 seconds...")
            time.sleep(5)
            
            # Get monitoring data
            monitoring_data = self.hmi.get_monitoring_data(5)
            self.log(f"Collected {len(monitoring_data)} monitoring samples")
            
            if monitoring_data:
                latest_sample = monitoring_data[-1]
                self.log(f"Latest sample timestamp: {time.strftime('%H:%M:%S', time.localtime(latest_sample['timestamp']))}")
                
                # Display sample data
                for device_id, device_data in latest_sample['devices'].items():
                    if device_data['status'] == 'ok':
                        if device_data['type'] == 'adc':
                            channels_summary = ', '.join([f"CH{ch['channel']}={ch['voltage']:.2f}V" for ch in device_data.get('channels', [])[:4]])
                            self.log(f"  ADC: {channels_summary}")
                        elif device_data['type'] == 'fan':
                            self.log(f"  Fan: {device_data.get('rpm', 'N/A')} RPM, {device_data.get('pwm_duty_cycle', 0):.0f}% PWM")
                        elif device_data['type'] == 'rtc' and device_data.get('datetime'):
                            dt = device_data['datetime']
                            self.log(f"  RTC: {dt['hour']:02d}:{dt['minute']:02d}:{dt['second']:02d}")
            
            self.test_results["monitoring_data_collection"] = len(monitoring_data) > 0
            
            # Stop monitoring
            response = self.send_command(
                {"action": "stop_monitoring"},
                "Stop monitoring"
            )
            self.test_results["monitoring_stop"] = response.get("success", False)
    
    def test_error_conditions(self):
        """Test error handling"""
        self.log("\n" + "="*60)
        self.log("TESTING ERROR CONDITIONS")
        self.log("="*60)
        
        error_tests = [
            {
                "command": "invalid json {",
                "description": "Invalid JSON syntax",
                "test_name": "error_invalid_json",
                "expect_success": False
            },
            {
                "command": {"action": "invalid_action"},
                "description": "Invalid action",
                "test_name": "error_invalid_action", 
                "expect_success": False
            },
            {
                "command": {"action": "read_channel", "device": "invalid_device", "params": {"channel": 0}},
                "description": "Invalid device",
                "test_name": "error_invalid_device",
                "expect_success": False
            },
            {
                "command": {"action": "read_channel", "device": "adc", "params": {"channel": 99}},
                "description": "Invalid ADC channel",
                "test_name": "error_invalid_channel",
                "expect_success": False
            }
        ]
        
        for test in error_tests:
            response = self.send_command(test["command"], test["description"])
            expected_success = test.get("expect_success", True)
            actual_success = response.get("success", False)
            
            # For error tests, we expect success=False
            test_passed = (actual_success == expected_success)
            self.test_results[test["test_name"]] = test_passed
            
            if not test_passed:
                self.log(f"  Error test failed: expected success={expected_success}, got success={actual_success}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.log("Starting HMI JSON API Test Suite")
        self.log("=" * 60)
        
        # Initialize HMI API
        try:
            self.hmi = HMIJsonAPI(auto_connect=True)
            self.log("✓ HMI API initialized successfully")
        except Exception as e:
            self.log(f"✗ Failed to initialize HMI API: {e}")
            return False
        
        # Run test categories
        test_categories = [
            ("System Commands", self.test_system_commands),
            ("ADC Commands", self.test_adc_commands),
            ("I/O Commands", self.test_io_commands),
            ("RTC Commands", self.test_rtc_commands),
            ("Fan Commands", self.test_fan_commands),
            ("EEPROM Commands", self.test_eeprom_commands),
            ("Monitoring", self.test_monitoring),
            ("Error Conditions", self.test_error_conditions)
        ]
        
        for category_name, test_function in test_categories:
            try:
                test_function()
            except Exception as e:
                self.log(f"✗ Error in {category_name}: {e}")
        
        # Print test summary
        self.print_test_summary()
        
        # Cleanup
        if self.hmi:
            self.hmi.disconnect_all()
        
        return True
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {passed_tests} (✓)")
        self.log(f"Failed: {failed_tests} (✗)")
        self.log(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
        
        # Detailed results
        self.log("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            self.log(f"  {test_name:<30} {status}")
        
        # Device summary
        if self.hmi:
            self.log(f"\nConnected Devices:")
            for device_id, device in self.hmi.devices.items():
                self.log(f"  {device_id:<10} {device.__class__.__name__}")
            
            if not self.hmi.devices:
                self.log("  No devices connected")

def run_performance_test(duration_seconds=30):
    """Run performance test"""
    print(f"\nRunning performance test for {duration_seconds} seconds...")
    
    hmi = HMIJsonAPI()
    
    commands = [
        '{"action": "get_system_status"}',
        '{"action": "read_all_channels", "device": "adc"}',
        '{"action": "read_all_pins", "device": "io"}',
        '{"action": "read_rpm", "device": "fan"}'
    ]
    
    start_time = time.time()
    command_count = 0
    error_count = 0
    
    while time.time() - start_time < duration_seconds:
        for command in commands:
            try:
                response_str = hmi.process_json_command(command)
                response = json.loads(response_str)
                
                if not response.get('success'):
                    error_count += 1
                
                command_count += 1
                
                # Brief pause to avoid overwhelming the system
                time.sleep(0.01)
                
            except Exception as e:
                error_count += 1
                command_count += 1
    
    elapsed_time = time.time() - start_time
    commands_per_second = command_count / elapsed_time
    
    print(f"Performance Test Results:")
    print(f"  Duration: {elapsed_time:.1f} seconds")
    print(f"  Total Commands: {command_count}")
    print(f"  Commands/Second: {commands_per_second:.1f}")
    print(f"  Errors: {error_count}")
    print(f"  Error Rate: {(error_count/command_count*100):.1f}%")
    
    hmi.disconnect_all()

def run_interactive_demo():
    """Run interactive demonstration"""
    print("\nInteractive HMI JSON API Demo")
    print("=" * 40)
    
    hmi = HMIJsonAPI()
    
    demo_commands = [
        {
            "name": "System Status",
            "command": '{"action": "get_system_status"}',
            "description": "Get overall system status and connected devices"
        },
        {
            "name": "Read ADC Channels",
            "command": '{"action": "read_all_channels", "device": "adc"}',
            "description": "Read all ADC channel voltages"
        },
        {
            "name": "I/O Pin Control",
            "command": '{"action": "configure_pin", "device": "io", "params": {"pin": 0, "direction": "output"}}',
            "description": "Configure pin 0 as output"
        },
        {
            "name": "Fan Control",
            "command": '{"action": "set_pwm", "device": "fan", "params": {"duty_cycle": 25}}',
            "description": "Set fan to 25% speed"
        },
        {
            "name": "EEPROM Info",
            "command": '{"action": "get_info", "device": "eeprom"}',
            "description": "Get EEPROM memory information"
        }
    ]
    
    for i, demo in enumerate(demo_commands, 1):
        print(f"\nDemo {i}: {demo['name']}")
        print(f"Description: {demo['description']}")
        print(f"Command: {demo['command']}")
        
        input("Press Enter to execute command...")
        
        try:
            response_str = hmi.process_json_command(demo['command'])
            response = json.loads(response_str)
            
            print("Response:")
            print(json.dumps(response, indent=2))
            
        except Exception as e:
            print(f"Error: {e}")
    
    hmi.disconnect_all()
    print("\nDemo completed!")

def main():
    """Main function with command line options"""
    parser = argparse.ArgumentParser(description="HMI JSON API Test Runner")
    parser.add_argument("--test", action="store_true", help="Run complete test suite")
    parser.add_argument("--performance", type=int, metavar="SECONDS", help="Run performance test for N seconds")
    parser.add_argument("--demo", action="store_true", help="Run interactive demo")
    parser.add_argument("--server", action="store_true", help="Start HTTP API server")
    parser.add_argument("--websocket", action="store_true", help="Start WebSocket server")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    if args.test:
        # Run test suite
        runner = HMITestRunner(verbose=not args.quiet)
        runner.run_all_tests()
        
    elif args.performance:
        # Run performance test
        run_performance_test(args.performance)
        
    elif args.demo:
        # Run interactive demo
        run_interactive_demo()
        
    elif args.server:
        # Start HTTP server
        print(f"Starting HTTP API server on {args.host}:{args.port}")
        try:
            hmi = HMIJsonAPI()
            create_api_server(host=args.host, port=args.port, hmi_api=hmi)
        except KeyboardInterrupt:
            print("\nServer stopped")
        except Exception as e:
            print(f"Server error: {e}")
            
    elif args.websocket:
        # Start WebSocket server
        ws_port = args.port if args.port != 8080 else 8081
        print(f"Starting WebSocket server on {args.host}:{ws_port}")
        try:
            hmi = HMIJsonAPI()
            create_websocket_server(host=args.host, port=ws_port, hmi_api=hmi)
        except KeyboardInterrupt:
            print("\nWebSocket server stopped")
        except Exception as e:
            print(f"WebSocket server error: {e}")
            
    else:
        # Default: show help and run quick test
        parser.print_help()
        print("\n" + "="*50)
        print("Quick Test (use --test for complete suite)")
        print("="*50)
        
        try:
            hmi = HMIJsonAPI()
            
            # Quick system status check
            response_str = hmi.process_json_command('{"action": "get_system_status"}')
            response = json.loads(response_str)
            
            if response.get('success'):
                print("✓ HMI JSON API is working!")
                devices = response['data']['devices']
                print(f"Connected devices: {len(devices)}")
                for device_id, device_info in devices.items():
                    status = "✓" if device_info['connected'] else "✗"
                    print(f"  {status} {device_info['device_type']} ({device_id})")
            else:
                print("✗ API test failed")
                print(f"Error: {response.get('error')}")
                
            hmi.disconnect_all()
            
        except Exception as e:
            print(f"✗ Quick test failed: {e}")

if __name__ == "__main__":
    main()
