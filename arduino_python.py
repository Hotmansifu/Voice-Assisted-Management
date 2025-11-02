"""
LoRa Sensor Node - Python Version
Simulates Arduino sensor readings and sends to InfluxDB
Works on Windows/Mac/Linux
"""

import time
import random
import requests
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Device Info (same as Arduino)
DEVICE_ADDR = [0xAC, 0x5B, 0xAD, 0xE2]
DEVICE_NAME = "python-sensor-node"

# InfluxDB Configuration
INFLUXDB_URL = "https://eu-central-1-1.aws.cloud2.influxdata.com"
INFLUXDB_BUCKET = "wazi_sensors"
INFLUXDB_ORG = "andguladzeluka12@gmail.com"
INFLUXDB_TOKEN = "k7dFdwFKCIsk6bwZjnwKmry9uiw8yAkw7nye1D4ym2Wk8SX84wL41XxhSNWqtTspNnkfjbce3RXL7rT45m5CIQ=="

# Timing
TX_INTERVAL = 30  # Send every 30 seconds
packet_counter = 0

# ═══════════════════════════════════════════════════════════════
# SENSOR SIMULATION
# ═══════════════════════════════════════════════════════════════

class SensorSimulator:
    """Simulates realistic sensor behavior"""
    
    def __init__(self):
        # Base values
        self.temp_base = 22.0
        self.humid_base = 60.0
        self.rain_base = 300
        self.sound_base = 500
        self.water_base = 200
        
        # Trends
        self.temp_trend = 0
        self.humid_trend = 0
    
    def read_dht11(self):
        """Simulate DHT11 temperature and humidity"""
        # Add realistic drift and noise
        self.temp_trend += random.uniform(-0.1, 0.1)
        self.temp_trend = max(-2, min(2, self.temp_trend))
        
        self.humid_trend += random.uniform(-0.2, 0.2)
        self.humid_trend = max(-5, min(5, self.humid_trend))
        
        temp = self.temp_base + self.temp_trend + random.uniform(-0.5, 0.5)
        humid = self.humid_base + self.humid_trend + random.uniform(-2, 2)
        
        temp = max(15, min(30, temp))
        humid = max(30, min(90, humid))
        
        return temp, humid
    
    def read_analog(self, base, variation):
        """Simulate analog sensor reading (0-1023)"""
        value = base + random.randint(-variation, variation)
        return max(0, min(1023, value))
    
    def read_sensors(self):
        """Read all sensors"""
        temp, humid = self.read_dht11()
        rain = self.read_analog(self.rain_base, 50)
        sound = self.read_analog(self.sound_base, 100)
        water = self.read_analog(self.water_base, 30)
        
        return temp, humid, rain, sound, water

# ═══════════════════════════════════════════════════════════════
# XLPP PAYLOAD BUILDER
# ═══════════════════════════════════════════════════════════════

def build_xlpp_payload(temp, humid, rain, sound, water):
    """Build XLPP payload exactly like Arduino"""
    payload = []
    
    # Temperature (channel 1)
    temp_val = int(temp * 10)
    payload.extend([0x02, 0x01, (temp_val >> 8) & 0xFF, temp_val & 0xFF])
    
    # Humidity (channel 2)
    payload.extend([0x03, 0x02, int(humid)])
    
    # Rain (channel 3)
    payload.extend([0x06, 0x03, (rain >> 8) & 0xFF, rain & 0xFF])
    
    # Sound (channel 4)
    payload.extend([0x06, 0x04, (sound >> 8) & 0xFF, sound & 0xFF])
    
    # Water (channel 5)
    payload.extend([0x06, 0x05, (water >> 8) & 0xFF, water & 0xFF])
    
    return bytes(payload)

# ═══════════════════════════════════════════════════════════════
# INFLUXDB FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def calculate_percentages(rain_ao, sound_ao, water_ao):
    """Calculate percentage values from analog readings"""
    rain_pct = round(max(0, min(100, (1023 - rain_ao) * 100 / 1023)), 1)
    sound_pct = round(max(0, min(100, sound_ao * 100 / 1023)), 1)
    water_pct = round(max(0, min(100, water_ao * 100 / 1023)), 1)
    return rain_pct, sound_pct, water_pct

def send_to_influxdb(temp, humid, rain, sound, water):
    """Send sensor data to InfluxDB"""
    global packet_counter
    
    rain_pct, sound_pct, water_pct = calculate_percentages(rain, sound, water)
    
    ts_ns = int(time.time() * 1e9)
    
    # Build line protocol
    lines = [
        f"temperature,device={DEVICE_NAME} value={temp} {ts_ns}",
        f"relativehumidity,device={DEVICE_NAME} value={humid} {ts_ns}",
        f"rainAO,device={DEVICE_NAME} value={rain} {ts_ns}",
        f"rainPct,device={DEVICE_NAME} value={rain_pct} {ts_ns}",
        f"soundAO,device={DEVICE_NAME} value={sound} {ts_ns}",
        f"soundPct,device={DEVICE_NAME} value={sound_pct} {ts_ns}",
        f"waterAO,device={DEVICE_NAME} value={water} {ts_ns}",
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
            packet_counter += 1
            print(f"✓ Packet #{packet_counter} sent!")
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
    print("=" * 70)
    print("LoRa Sensor Node - Python Version")
    print("=" * 70)
    print(f"Device: {':'.join(f'{b:02X}' for b in DEVICE_ADDR)}")
    print(f"InfluxDB: {INFLUXDB_BUCKET}")
    print(f"Interval: {TX_INTERVAL} seconds")
    print("=" * 70)
    print("Simulating sensor readings...\n")
    
    sensors = SensorSimulator()
    last_tx_time = 0
    
    try:
        while True:
            now = time.time()
            
            # Read sensors
            temp, humid, rain, sound, water = sensors.read_sensors()
            
            # Display every 5 seconds
            if int(now) % 5 == 0:
                remaining = int(TX_INTERVAL - (now - last_tx_time))
                print(f"T={temp:.1f}°C H={humid:.1f}% Rain={rain} Sound={sound} Water={water} [TX in {remaining}s]")
                time.sleep(1)  # Prevent multiple prints in same second
            
            # Send packet
            if now - last_tx_time >= TX_INTERVAL:
                last_tx_time = now
                
                print("\n>>> SENDING PACKET <<<")
                print(f"Data: T={temp:.1f}°C H={humid:.1f}% Rain={rain} Sound={sound} Water={water}")
                
                # Build XLPP payload (like Arduino)
                payload = build_xlpp_payload(temp, humid, rain, sound, water)
                print(f"Payload ({len(payload)} bytes): {payload.hex()}")
                
                # Send to InfluxDB
                send_to_influxdb(temp, humid, rain, sound, water)
                print(">>> DONE <<<\n")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        print(f"Total packets sent: {packet_counter}")
        print("✅ Done!")

if __name__ == "__main__":
    main()