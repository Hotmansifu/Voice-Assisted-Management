from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# InfluxDB Config
INFLUXDB_URL = "https://eu-central-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "k7dFdwFKCIsk6bwZjnwKmry9uiw8yAkw7nye1D4ym2Wk8SX84wL41XxhSNWqtTspNnkfjbce3RXL7rT45m5CIQ=="
INFLUXDB_ORG = "andguladzeluka12@gmail.com"
INFLUXDB_BUCKET = "wazi_sensors"
DEVICE_NAME = "arduino-sensor-node"

def query_influxdb(flux_query):
    """Execute Flux query using requests"""
    url = f"{INFLUXDB_URL}/api/v2/query"
    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "application/vnd.flux",
        "Accept": "application/csv"
    }
    params = {"org": INFLUXDB_ORG}
    
    try:
        response = requests.post(url, params=params, headers=headers, data=flux_query, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def parse_csv_response(csv_text):
    """Parse InfluxDB CSV response"""
    if not csv_text:
        return []
    
    lines = csv_text.strip().split('\n')
    if len(lines) < 2:
        return []
    
    data = []
    headers = None
    
    for line in lines:
        if line.startswith('#'):
            continue
        
        parts = line.split(',')
        
        if headers is None:
            headers = parts
            continue
        
        if len(parts) >= len(headers):
            row = {}
            for i, header in enumerate(headers):
                if i < len(parts):
                    row[header] = parts[i]
            
            if '_measurement' in row and '_value' in row and '_time' in row:
                try:
                    data.append({
                        'measurement': row['_measurement'],
                        'value': float(row['_value']),
                        'time': row['_time']
                    })
                except (ValueError, KeyError):
                    continue
    
    return data

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/latest')
def get_latest():
    flux_query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["device"] == "{DEVICE_NAME}")
        |> last()
    '''
    
    csv_data = query_influxdb(flux_query)
    records = parse_csv_response(csv_data)
    
    result = {}
    for record in records:
        result[record['measurement']] = {
            'value': record['value'],
            'time': record['time']
        }
    
    return jsonify(result)

@app.route('/api/history/<period>')
def get_history(period):
    period_map = {
        '1h': '-1h',
        '6h': '-6h',
        '24h': '-24h',
        '7d': '-7d'
    }
    
    start = period_map.get(period, '-1h')
    
    flux_query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: {start})
        |> filter(fn: (r) => r["device"] == "{DEVICE_NAME}")
    '''
    
    csv_data = query_influxdb(flux_query)
    records = parse_csv_response(csv_data)
    
    return jsonify(records)

@app.route('/api/stats')
def get_stats():
    flux_query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -24h)
        |> filter(fn: (r) => r["device"] == "{DEVICE_NAME}")
    '''
    
    csv_data = query_influxdb(flux_query)
    records = parse_csv_response(csv_data)
    
    stats = {}
    measurements = {}
    
    for record in records:
        measurement = record['measurement']
        if measurement not in measurements:
            measurements[measurement] = []
        measurements[measurement].append(record['value'])
    
    for measurement, values in measurements.items():
        if values:
            stats[measurement] = {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'count': len(values)
            }
    
    return jsonify(stats)

if __name__ == '__main__':
    print("=" * 50)
    print("🌡️  WAZI Sensor Dashboard Starting...")
    print("=" * 50)
    print(f"📍 URL: http://localhost:5000")
    print(f"📍 Network: http://YOUR_IP:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)