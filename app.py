from flask import Flask, render_template, request, jsonify
import subprocess
import platform
import re
import time
import statistics
import json
import os
from datetime import datetime

app = Flask(__name__)

# File to store WiFi data persistently
DATA_FILE = 'dynamic_data.json'

# Store WiFi data by location
wifi_locations = {}
signal_history = {}

# Function to load existing data from file
def load_existing_data():
    """Load existing data from the JSON file if it exists."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as file:
                data = json.load(file)
                # Extract locations data
                if "locations" in data:
                    for location_key, location_data in data["locations"].items():
                        if "networks" in location_data:
                            # Create key from latitude/longitude
                            coords = f"{location_data.get('latitude'):.6f},{location_data.get('longitude'):.6f}"
                            wifi_locations[coords] = location_data["networks"]
                
                print(f"Loaded {len(wifi_locations)} locations from {DATA_FILE}")
                return True
    except Exception as e:
        print(f"Error loading existing data: {str(e)}")
        return False

# Function to save current data to file
def save_data_to_file():
    """Save the current WiFi data to the JSON file."""
    try:
        # Structure the data - combines existing data
        data = {
            "locations": {},
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "version": "1.1"
            }
        }
        
        # Load existing data if file exists
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as file:
                    existing_data = json.load(file)
                    data["locations"] = existing_data.get("locations", {})
                    # Keep the original creation date if available
                    if "metadata" in existing_data and "created" in existing_data["metadata"]:
                        data["metadata"]["created"] = existing_data["metadata"]["created"]
                    else:
                        data["metadata"]["created"] = datetime.now().isoformat()
        except:
            data["metadata"]["created"] = datetime.now().isoformat()
        
        # Update with new data from memory
        for location_key, networks in wifi_locations.items():
            # Parse lat/lon from the key
            try:
                lat, lon = location_key.split(',')
                timestamp = datetime.now().isoformat()
                location_name = f"Location_{timestamp}"
                
                # Create a unique location entry
                data["locations"][f"{location_name}_{timestamp}"] = {
                    "name": location_name,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "timestamp": timestamp,
                    "networks": networks,
                    "note": ""
                }
            except:
                # Skip locations with invalid keys
                continue
        
        # Add signal history
        data["signal_history"] = signal_history
        
        with open(DATA_FILE, 'w') as file:
            json.dump(data, file, indent=2)
        
        print(f"Data saved to {DATA_FILE}")
        return True
    except Exception as e:
        print(f"Error saving data: {str(e)}")
        return False



@app.route('/')
def index():
    return render_template('map.html')

# Add this new function at the top level
def find_nearest_location(target_lat, target_lon, max_distance=0.001):  # max_distance in degrees (~100m)
    """Find the nearest stored location within max_distance."""
    nearest = None
    min_dist = float('inf')
    
    for location_key in wifi_locations:
        lat, lon = map(float, location_key.split(','))
        # Simple distance calculation (Euclidean)
        dist = ((lat - target_lat) ** 2 + (lon - target_lon) ** 2) ** 0.5
        
        if dist < min_dist and dist < max_distance:
            min_dist = dist
            nearest = location_key
            
    return nearest

# Replace the existing /get_wifi route with this:
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
        wifi_networks = wifi_locations[nearest_location]
        stored_lat, stored_lon = map(float, nearest_location.split(','))
        
        return jsonify({
            "latitude": stored_lat, 
            "longitude": stored_lon,
            "wifi": wifi_networks,
            "timestamp": datetime.now().isoformat(),
            "is_stored_data": True
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
    # Return all unique SSIDs
    all_ssids = set()
    for location_data in wifi_locations.values():
        for network in location_data:
            all_ssids.add(network['ssid'])
    
    return jsonify({
        "all_ssids": list(all_ssids)
    })

@app.route('/get_data_for_download', methods=['GET'])
def get_data_for_download():
    """Return all collected WiFi data for download as JSON"""
    # Make sure to save the latest data
    save_data_to_file()
    
    # Load the complete data from file to ensure we have everything
    try:
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
    except:
        # If loading fails, use the in-memory data
        data = {
            "locations": wifi_locations,
            "history": signal_history,
            "timestamp": datetime.now().isoformat()
        }
    
    return jsonify(data)

@app.route('/get_all_locations', methods=['GET'])
def get_all_locations():
    """Return all stored location coordinates"""
    locations = []
    try:
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
            for loc_key, loc_data in data["locations"].items():
                if "latitude" in loc_data and "longitude" in loc_data:
                    locations.append({
                        "latitude": loc_data["latitude"],
                        "longitude": loc_data["longitude"],
                        "name": loc_data["name"]
                    })
    except Exception as e:
        print(f"Error loading locations: {e}")
    
    return jsonify({"locations": locations})

# Load existing data when the app starts
load_existing_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
