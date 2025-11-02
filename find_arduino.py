"""
Find Arduino COM Port
Quick utility to detect connected Arduino
"""

import serial.tools.list_ports

print("=" * 50)
print("Searching for Arduino...")
print("=" * 50)

ports = serial.tools.list_ports.comports()

if not ports:
    print("❌ No serial devices found")
    print("\nMake sure Arduino is connected via USB")
else:
    print(f"Found {len(ports)} serial device(s):\n")
    
    arduino_found = False
    
    for port in ports:
        is_arduino = 'arduino' in port.description.lower() or 'ch340' in port.description.lower() or 'usb' in port.description.lower()
        
        marker = "✅" if is_arduino else "  "
        print(f"{marker} {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        
        if is_arduino:
            arduino_found = True
            print(f"\n   👉 Use this in arduino_serial_bridge.py:")
            print(f"      SERIAL_PORT = \"{port.device}\"")
        
        print()
    
    if not arduino_found:
        print("⚠️  No Arduino detected automatically")
        print("   Try each port manually in arduino_serial_bridge.py")

print("=" * 50)