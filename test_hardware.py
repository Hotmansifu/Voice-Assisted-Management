#!/usr/bin/env python3
"""
Hardware Test Script
Verify all sensors are connected and working
"""

import time

print("=" * 60)
print("🔧 Hardware Sensor Test")
print("=" * 60)

# Test 1: DHT11 Sensor
print("\n[1/3] Testing DHT11 (Temperature & Humidity)...")
try:
    import Adafruit_DHT
    DHT_SENSOR = Adafruit_DHT.DHT11
    DHT_PIN = 4
    
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    
    if humidity is not None and temperature is not None:
        print(f"✅ DHT11 OK - Temp: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
    else:
        print("❌ DHT11 FAILED - Check wiring on GPIO 4")
except ImportError:
    print("❌ Adafruit_DHT library not installed")
    print("   Install: pip3 install Adafruit_DHT")
except Exception as e:
    print(f"❌ DHT11 ERROR: {e}")

# Test 2: SPI/MCP3008
print("\n[2/3] Testing SPI connection...")
try:
    import busio
    import digitalio
    import board
    
    # Check SPI pins exist
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    print("✅ SPI initialized")
    
    cs = digitalio.DigitalInOut(board.D5)
    print("✅ CS pin (GPIO 5) initialized")
    
except ImportError:
    print("❌ Circuit Python libraries not installed")
    print("   Install: pip3 install adafruit-circuitpython-mcp3xxx")
except Exception as e:
    print(f"❌ SPI ERROR: {e}")
    print("   Enable SPI: sudo raspi-config → Interface Options → SPI")

# Test 3: MCP3008 ADC
print("\n[3/3] Testing MCP3008 ADC (Analog Sensors)...")
try:
    import busio
    import digitalio
    import board
    import adafruit_mcp3xxx.mcp3008 as MCP
    from adafruit_mcp3xxx.analog_in import AnalogIn
    
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    cs = digitalio.DigitalInOut(board.D5)
    mcp = MCP.MCP3008(spi, cs)
    
    # Read all channels
    channels = [
        ("Rain (CH0)", MCP.P0),
        ("Sound (CH1)", MCP.P1),
        ("Water (CH2)", MCP.P2)
    ]
    
    print("✅ MCP3008 detected\n")
    print("   Channel readings:")
    
    for name, channel in channels:
        chan = AnalogIn(mcp, channel)
        value = int(chan.value / 64)  # Convert to 0-1023
        voltage = chan.voltage
        print(f"   {name}: {value:4d} ({voltage:.2f}V)")
    
    print("\n✅ All analog channels readable")
    
except ImportError:
    print("❌ MCP3008 library not installed")
    print("   Install: pip3 install adafruit-circuitpython-mcp3xxx")
except Exception as e:
    print(f"❌ MCP3008 ERROR: {e}")
    print("   Check wiring and SPI connections")

# Test 4: Internet Connection
print("\n[4/4] Testing Internet Connection...")
try:
    import requests
    response = requests.get("https://www.google.com", timeout=5)
    if response.status_code == 200:
        print("✅ Internet connection OK")
    else:
        print("⚠️  Internet connection slow")
except ImportError:
    print("❌ requests library not installed")
    print("   Install: pip3 install requests")
except Exception as e:
    print(f"❌ No internet connection: {e}")

# Summary
print("\n" + "=" * 60)
print("✅ Hardware test complete!")
print("=" * 60)
print("\nIf all tests passed, run:")
print("  python3 sensor_real_hardware.py")
print("\n")