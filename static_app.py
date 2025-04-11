import json
import os
import webbrowser
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# File containing stored WiFi data
WIFI_DATA_FILE = 'wifi_data.json'

app = Flask(__name__)

def load_data():
    """Load WiFi data from the static JSON file"""
    try:
        if os.path.exists(WIFI_DATA_FILE):
            with open(WIFI_DATA_FILE, 'r') as file:
                return json.load(file)
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"locations": {}, "metadata": {"error": str(e)}}
    
    return {"locations": {}, "metadata": {"message": "No data file found"}}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters"""
    import math
    R = 6371000  # Earth's radius in meters
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = math.sin(Δφ/2) * math.sin(Δφ/2) + \
        math.cos(φ1) * math.cos(φ2) * \
        math.sin(Δλ/2) * math.sin(Δλ/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_nearest_location(target_lat, target_lon, max_distance=100):
    """Find the nearest stored location within max_distance (meters)."""
    data = load_data()
    nearest = None
    min_dist = float('inf')
    
    for location_key, location_data in data["locations"].items():
        lat = location_data.get("latitude")
        lon = location_data.get("longitude")
        
        if lat is None or lon is None:
            continue
            
        # Calculate distance
        dist = calculate_distance(lat, lon, target_lat, target_lon)
        
        if dist < min_dist and dist < max_distance:
            min_dist = dist
            nearest = {
                "key": location_key,
                "distance": dist,
                "location_data": location_data
            }
    
    return nearest

@app.route('/')
def index():
    """Serve the main map page"""
    return render_template('map.html', static_mode=True)

@app.route('/get_wifi', methods=['POST'])
def get_wifi():
    """Return WiFi data for nearest stored location"""
    data = request.json
    latitude = float(data.get('lat'))
    longitude = float(data.get('lon'))
    
    # Find nearest stored location
    nearest_location = find_nearest_location(latitude, longitude)
    
    if nearest_location:
        # Use stored data
        location_data = nearest_location["location_data"]
        wifi_networks = location_data["networks"]
        
        return jsonify({
            "latitude": location_data["latitude"], 
            "longitude": location_data["longitude"],
            "wifi": wifi_networks,
            "timestamp": location_data["timestamp"],
            "is_stored_data": True,
            "distance": nearest_location["distance"],
            "name": location_data.get("name", "Unknown")
        })
    
    return jsonify({
        "latitude": latitude,
        "longitude": longitude,
        "wifi": [],
        "timestamp": datetime.now().isoformat(),
        "is_stored_data": False,
        "message": "No stored data found nearby"
    })

@app.route('/get_all_wifi', methods=['GET'])
def get_all_wifi():
    """Return all unique SSIDs and their signal strength ranges"""
    data = load_data()
    ssid_data = {}
    
    for location_key, location_data in data["locations"].items():
        for network in location_data.get("networks", []):
            ssid = network.get("ssid")
            if not ssid:
                continue
            
            signal = network.get("signal", 0)
            
            if ssid not in ssid_data:
                ssid_data[ssid] = {
                    "ssid": ssid,
                    "min_signal": signal,
                    "max_signal": signal,
                    "locations": 1
                }
            else:
                ssid_data[ssid]["min_signal"] = min(ssid_data[ssid]["min_signal"], signal)
                ssid_data[ssid]["max_signal"] = max(ssid_data[ssid]["max_signal"], signal)
                ssid_data[ssid]["locations"] += 1
    
    networks = list(ssid_data.values())
    return jsonify({
        "networks": networks,
        "count": len(networks)
    })

@app.route('/get_data_for_download', methods=['GET'])
def get_data_for_download():
    """Return all collected WiFi data for download as JSON"""
    data = load_data()
    return jsonify(data)

@app.route('/get_all_locations', methods=['GET'])
def get_all_locations():
    """Return all stored location coordinates"""
    locations = []
    try:
        data = load_data()
        for loc_key, loc_data in data["locations"].items():
            if "latitude" in loc_data and "longitude" in loc_data:
                locations.append({
                    "latitude": loc_data["latitude"],
                    "longitude": loc_data["longitude"],
                    "name": loc_data.get("name", "Unknown Location"),
                    "timestamp": loc_data.get("timestamp", "")
                })
    except Exception as e:
        print(f"Error loading locations: {e}")
    
    return jsonify({"locations": locations})

@app.route('/stats', methods=['GET'])
def get_stats():
    """Return statistics about the collected data"""
    data = load_data()
    
    # Count networks
    total_locations = len(data["locations"])
    unique_ssids = set()
    network_counts = {}
    signal_ranges = {}
    
    for location_key, location_data in data["locations"].items():
        networks = location_data.get("networks", [])
        
        for network in networks:
            ssid = network.get("ssid")
            if not ssid:
                continue
                
            unique_ssids.add(ssid)
            
            # Count occurrence by auth type
            auth_type = network.get("auth", "Unknown")
            if auth_type not in network_counts:
                network_counts[auth_type] = 0
            network_counts[auth_type] += 1
            
            # Track signal strength ranges
            signal = network.get("signal", 0)
            if ssid not in signal_ranges:
                signal_ranges[ssid] = {"min": signal, "max": signal}
            else:
                signal_ranges[ssid]["min"] = min(signal_ranges[ssid]["min"], signal)
                signal_ranges[ssid]["max"] = max(signal_ranges[ssid]["max"], signal)
    
    # Get metadata
    created = data.get("metadata", {}).get("created", "Unknown")
    last_updated = data.get("metadata", {}).get("last_updated", "Unknown")
    
    return jsonify({
        "total_locations": total_locations,
        "unique_networks": len(unique_ssids),
        "networks_by_auth": network_counts,
        "created": created,
        "last_updated": last_updated,
        "strongest_network": max(signal_ranges.items(), key=lambda x: x[1]["max"])[0] if signal_ranges else None
    })

@app.route('/network/<ssid>', methods=['GET'])
def get_network_details(ssid):
    """Get details for a specific network"""
    data = load_data()
    network_data = []
    
    for location_key, location_data in data["locations"].items():
        for network in location_data.get("networks", []):
            if network.get("ssid") == ssid:
                network_data.append({
                    "location": {
                        "name": location_data.get("name", "Unknown"),
                        "latitude": location_data.get("latitude"),
                        "longitude": location_data.get("longitude"),
                        "timestamp": location_data.get("timestamp")
                    },
                    "signal": network.get("signal"),
                    "auth": network.get("auth"),
                    "channel": network.get("channel"),
                    "snr": network.get("snr")
                })
    
    if not network_data:
        return jsonify({"error": "Network not found"}), 404
    
    return jsonify({
        "ssid": ssid,
        "locations": len(network_data),
        "data": network_data
    })

def main(port=5000):
    """Run the Flask application"""
    print(f"Starting static WiFi data viewer on port {port}")
    print(f"Data source: {WIFI_DATA_FILE}")
    
    # Check if data file exists
    if not os.path.exists(WIFI_DATA_FILE):
        print(f"Warning: Data file {WIFI_DATA_FILE} not found.")
        print("The application will run but may not display any data.")
    else:
        try:
            data = load_data()
            location_count = len(data["locations"])
            print(f"Found {location_count} locations in data file")
        except Exception as e:
            print(f"Error loading data: {e}")
    
    # Open browser
    webbrowser.open(f"http://127.0.0.1:{port}")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='View stored WiFi data on a map')
    parser.add_argument('--port', '-p', type=int, default=5000, 
                        help='Port for web interface (default: 5000)')
    parser.add_argument('--data-file', '-f', default='wifi_data.json',
                        help='JSON file containing WiFi data (default: wifi_data.json)')
    args = parser.parse_args()
    
    # Update global variable
    WIFI_DATA_FILE = args.data_file
    
    main(port=args.port)