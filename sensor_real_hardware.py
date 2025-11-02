"""
Direct Sensor Reading to InfluxDB (Python)
Reads sensors directly from Raspberry Pi and sends to InfluxDB
REAL HARDWARE VERSION - No simulated data
"""

import time
import requests
from datetime import datetime

# For Raspberry Pi GPIO sensors
try:
    import Adafruit_DHT
    import RPi.GPIO as GPIO
    USE_RPI = True
except ImportError:
    USE_RPI = False
    print("⚠️  RPi.GPIO not found - install on Raspberry Pi")

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Sensor Configuration
DHT_SENSOR = Adafruit_DHT.DHT11 if USE_RPI else None
DHT_PIN = 4

# MCP3008 ADC Channels (SPI)
RAIN_CHANNEL = 0    # Rain sensor on MCP3008 CH0
SOUND_CHANNEL = 1   # Sound sensor on MCP3008 CH1
WATER_CHANNEL = 2   # Water sensor on MCP3008 CH2

# InfluxDB Configuration
INFLUXDB_URL = "https://eu-central-1-1.aws.cloud2.influxdata.com"
INFLUXDB_BUCKET = "wazi_sensors"
INFLUXDB_ORG = "andguladzeluka12@gmail.com"
INFLUXDB_TOKEN = "k7dFdwFKCIsk6bwZjnwKmry9uiw8yAkw7nye1D4ym2Wk8SX84wL41XxhSNWqtTspNnkfjbce3RXL7rT45m5CIQ=="

DEVICE_NAME = "python-sensor-node"
SEND_INTERVAL = 30  # Send every 30 seconds

# ═══════════════════════════════════════════════════════════════
# SENSOR READING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def read_dht_sensor():
    """Read temperature and humidity from DHT11"""
    if USE_RPI:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN, retries=5, delay_seconds=2)
            if humidity is not None and temperature is not None:
                return temperature, humidity
            else:
                print("⚠️  DHT11 read failed - check wiring")
                return None, None
        except Exception as e:
            print(f"❌ DHT read error: {e}")
            return None, None
    
    print("⚠️  Not running on Raspberry Pi")
    return None, None

def read_analog_sensors():
    """Read analog sensor values using MCP3008 ADC"""
    if USE_RPI:
        try:
            # Import MCP3008 libraries
            import busio
            import digitalio
            import board
            import adafruit_mcp3xxx.mcp3008 as MCP
            from adafruit_mcp3xxx.analog_in import AnalogIn
            
            # Create SPI bus
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            cs = digitalio.DigitalInOut(board.D5)  # CS pin
            mcp = MCP.MCP3008(spi, cs)
            
            # Create analog input channels
            rain_channel = AnalogIn(mcp, MCP.P0)
            sound_channel = AnalogIn(mcp, MCP.P1)
            water_channel = AnalogIn(mcp, MCP.P2)
            
            # Read raw values (0-65535) and convert to 0-1023 range
            rain = int(rain_channel.value / 64)
            sound = int(sound_channel.value / 64)
            water = int(water_channel.value / 64)
            
            return rain, sound, water
            
        except ImportError:
            print("❌ MCP3008 library missing!")
            print("Install: pip3 install adafruit-circuitpython-mcp3xxx")
            return None, None, None
            
        except Exception as e:
            print(f"❌ MCP3008 read error: {e}")
            print("Check SPI wiring and enable SPI: sudo raspi-config")
            return None, None, None
    
    print("⚠️  Not running on Raspberry Pi")
    return None, None, None

def calculate_percentages(rain_ao, sound_ao, water_ao):
    """Calculate percentage values from analog readings"""
    if rain_ao is None or sound_ao is None or water_ao is None:
        return None, None, None
        
    rain_pct = round(max(0, min(100, (1023 - rain_ao) * 100 / 1023)), 1)
    sound_pct = round(max(0, min(100, sound_ao * 100 / 1023)), 1)
    water_pct = round(max(0, min(100, water_ao * 100 / 1023)), 1)
    return rain_pct, sound_pct, water_pct

# ═══════════════════════════════════════════════════════════════
# INFLUXDB FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def send_to_influxdb(sensor_data):
    """Send sensor data to InfluxDB Cloud"""
    ts_ns = int(time.time() * 1e9)
    lines = []
    
    for key, value in sensor_data.items():
        if value is None:
            continue
        try:
            fv = float(value)
            lines.append(f"{key},device={DEVICE_NAME} value={fv} {ts_ns}")
        except (ValueError, TypeError):
            continue
    
    if not lines:
        print("⚠️  No valid sensor data to send")
        return False
    
    payload = "\n".join(lines)
    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain",
        "Accept": "application/json"
    }
    
    url = f"{INFLUXDB_URL}/api/v2/write"
    params = {
        "org": INFLUXDB_ORG,
        "bucket": INFLUXDB_BUCKET,
        "precision": "ns"
    }
    
    try:
        r = requests.post(url, params=params, data=payload, headers=headers, timeout=10)
        
        if r.status_code == 204:
            print(f"✅ Sent to InfluxDB")
            return True
        else:
            print(f"❌ InfluxDB error [{r.status_code}]: {r.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

# ═══════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    """Main application loop"""
    print("=" * 70)
    print("🌡️  REAL Hardware Sensor Node → InfluxDB")
    print("=" * 70)
    print(f"📍 Device: {DEVICE_NAME}")
    print(f"📍 InfluxDB: {INFLUXDB_BUCKET}")
    print(f"📍 Interval: {SEND_INTERVAL} seconds")
    print("=" * 70)
    
    if not USE_RPI:
        print("\n❌ ERROR: Must run on Raspberry Pi!")
        print("Install: sudo apt-get install python3-dev python3-pip")
        print("         pip3 install Adafruit_DHT RPi.GPIO")
        return 1
    
    print("✅ Running on Raspberry Pi")
    print("\n🔌 Hardware Requirements:")
    print("  - DHT11 on GPIO 4")
    print("  - MCP3008 ADC on SPI (CS=GPIO5)")
    print("  - Rain sensor on MCP3008 CH0")
    print("  - Sound sensor on MCP3008 CH1")
    print("  - Water sensor on MCP3008 CH2")
    print("\n🎧 Starting sensor readings...\n")
    
    packet_count = 0
    
    try:
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Read sensors
            temperature, humidity = read_dht_sensor()
            rain_ao, sound_ao, water_ao = read_analog_sensors()
            rain_pct, sound_pct, water_pct = calculate_percentages(rain_ao, sound_ao, water_ao)
            
            # Display readings
            print(f"\n📊 [{timestamp}] Sensor Reading #{packet_count + 1}")
            
            if temperature is not None:
                print(f"   🌡️  Temperature: {temperature:.1f}°C")
            else:
                print(f"   🌡️  Temperature: ERROR")
                
            if humidity is not None:
                print(f"   💧 Humidity: {humidity:.1f}%")
            else:
                print(f"   💧 Humidity: ERROR")
                
            if rain_ao is not None:
                print(f"   🌧️  Rain: {rain_ao} ({rain_pct}%)")
            else:
                print(f"   🌧️  Rain: ERROR")
                
            if sound_ao is not None:
                print(f"   🔊 Sound: {sound_ao} ({sound_pct}%)")
            else:
                print(f"   🔊 Sound: ERROR")
                
            if water_ao is not None:
                print(f"   💦 Water: {water_ao} ({water_pct}%)")
            else:
                print(f"   💦 Water: ERROR")
            
            # Prepare data for InfluxDB (only include valid readings)
            sensor_data = {}
            if temperature is not None:
                sensor_data["temperature"] = temperature
            if humidity is not None:
                sensor_data["relativehumidity"] = humidity
            if rain_ao is not None:
                sensor_data["rainAO"] = rain_ao
                sensor_data["rainPct"] = rain_pct
            if sound_ao is not None:
                sensor_data["soundAO"] = sound_ao
                sensor_data["soundPct"] = sound_pct
            if water_ao is not None:
                sensor_data["waterAO"] = water_ao
                sensor_data["waterPct"] = water_pct
            
            # Send to InfluxDB
            if send_to_influxdb(sensor_data):
                packet_count += 1
            
            # Wait for next interval
            print(f"\n⏳ Waiting {SEND_INTERVAL} seconds until next reading...")
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        GPIO.cleanup()
        print("✅ Done!")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        GPIO.cleanup()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())