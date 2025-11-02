"""
Arduino Serial Bridge to InfluxDB
Reads sensor data from Arduino via USB and sends to InfluxDB
"""

import time
import requests
import re
import serial
import serial.tools.list_ports

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Serial Port Configuration
SERIAL_PORT = "COM8"  # Windows: COM3, COM4, etc. | Linux: /dev/ttyUSB0, /dev/ttyACM0
BAUD_RATE = 9600

# InfluxDB Configuration
INFLUXDB_URL = "https://eu-central-1-1.aws.cloud2.influxdata.com"
INFLUXDB_BUCKET = "wazi_sensors"
INFLUXDB_ORG = "andguladzeluka12@gmail.com"
INFLUXDB_TOKEN = "k7dFdwFKCIsk6bwZjnwKmry9uiw8yAkw7nye1D4ym2Wk8SX84wL41XxhSNWqtTspNnkfjbce3RXL7rT45m5CIQ=="

DEVICE_NAME = "arduino-sensor-node"

# ═══════════════════════════════════════════════════════════════
# PARSE ARDUINO OUTPUT
# ═══════════════════════════════════════════════════════════════

def parse_arduino_line(line):
    """
    Parse Arduino serial output line
    Expected format: T=22.5C H=60.2% Rain=300 Sound=500 Water=200
    """
    try:
        # Extract values using regex
        temp_match = re.search(r'T=([\d.]+)', line)
        humid_match = re.search(r'H=([\d.]+)', line)
        rain_match = re.search(r'Rain=(\d+)', line)
        sound_match = re.search(r'Sound=(\d+)', line)
        water_match = re.search(r'Water=(\d+)', line)
        
        if temp_match and humid_match and rain_match and sound_match and water_match:
            return {
                'temperature': float(temp_match.group(1)),
                'humidity': float(humid_match.group(1)),
                'rain': int(rain_match.group(1)),
                'sound': int(sound_match.group(1)),
                'water': int(water_match.group(1))
            }
    except Exception as e:
        print(f"Parse error: {e}")
    
    return None

# ═══════════════════════════════════════════════════════════════
# INFLUXDB FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def calculate_percentages(rain_ao, sound_ao, water_ao):
    """Calculate percentage values from analog readings"""
    rain_pct = round(max(0, min(100, (1023 - rain_ao) * 100 / 1023)), 1)
    sound_pct = round(max(0, min(100, sound_ao * 100 / 1023)), 1)
    water_pct = round(max(0, min(100, water_ao * 100 / 1023)), 1)
    return rain_pct, sound_pct, water_pct

def send_to_influxdb(data):
    """Send sensor data to InfluxDB"""
    rain_pct, sound_pct, water_pct = calculate_percentages(
        data['rain'], data['sound'], data['water']
    )
    
    ts_ns = int(time.time() * 1e9)
    
    # Build line protocol
    lines = [
        f"temperature,device={DEVICE_NAME} value={data['temperature']} {ts_ns}",
        f"relativehumidity,device={DEVICE_NAME} value={data['humidity']} {ts_ns}",
        f"rainAO,device={DEVICE_NAME} value={data['rain']} {ts_ns}",
        f"rainPct,device={DEVICE_NAME} value={rain_pct} {ts_ns}",
        f"soundAO,device={DEVICE_NAME} value={data['sound']} {ts_ns}",
        f"soundPct,device={DEVICE_NAME} value={sound_pct} {ts_ns}",
        f"waterAO,device={DEVICE_NAME} value={data['water']} {ts_ns}",
        f"waterPct,device={DEVICE_NAME} value={water_pct} {ts_ns}"
    ]
    
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
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("Arduino Serial Bridge → InfluxDB")
    print("=" * 70)
    print(f"Serial Port: {SERIAL_PORT} @ {BAUD_RATE} baud")
    print(f"InfluxDB: {INFLUXDB_BUCKET}")
    print("=" * 70)
    
    # Open serial connection
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {SERIAL_PORT}")
        time.sleep(2)  # Wait for Arduino to reset
    except serial.SerialException as e:
        print(f"❌ Cannot open {SERIAL_PORT}: {e}")
        print("\nAvailable ports:")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"  - {port.device}: {port.description}")
        return 1
    
    print("🎧 Listening for Arduino data...\n")
    
    packet_count = 0
    
    try:
        while True:
            if ser.in_waiting > 0:
                # Read line from Arduino
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if line:
                    print(f"Arduino: {line}")
                    
                    # Parse sensor data
                    data = parse_arduino_line(line)
                    
                    if data:
                        print(f"📊 T={data['temperature']:.1f}°C H={data['humidity']:.1f}% "
                              f"Rain={data['rain']} Sound={data['sound']} Water={data['water']}")
                        
                        # Send to InfluxDB
                        if send_to_influxdb(data):
                            packet_count += 1
                            print(f"✓ Packet #{packet_count}\n")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        print(f"Total packets sent: {packet_count}")
        ser.close()
        print("✅ Done!")
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        ser.close()
        return 1

if __name__ == "__main__":
    exit(main())