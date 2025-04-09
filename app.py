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
DATA_FILE = 'wifi_data.json'

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
                            # Format may be slightly different, adapt as needed
                            coords = f"{location_data.get('latitude'):.6f},{location_data.get('longitude'):.6f}"
                            wifi_locations[coords] = location_data["networks"]
                
                # Update signal history if available
                if "signal_history" in data:
                    signal_history.update(data["signal_history"])
                
                print(f"Loaded {len(wifi_locations)} locations from {DATA_FILE}")
    except Exception as e:
        print(f"Error loading existing data: {str(e)}")

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

# Improved function to get WiFi SSIDs and signal strength with shorter scan times
def get_wifi_networks(samples=1, delay=0.2):
    all_samples = []
    
    for _ in range(samples):
        # Get a single scan
        networks = get_single_wifi_scan()
        if networks:
            all_samples.append(networks)
        # Wait between scans - reduced delay
        time.sleep(delay)
    
    # Aggregate results from all samples
    return aggregate_wifi_samples(all_samples)

def get_single_wifi_scan():
    wifi_data = []
    os_type = platform.system()
    
    # Try to get noise floor (varies by system)
    noise_floor = -95  # Default noise floor estimation in dBm

    if os_type == "Windows":
        try:
            # Quick adapter refresh
            subprocess.run("netsh wlan show networks mode=bssid", shell=True, stderr=subprocess.DEVNULL)
            
            # Get detailed info about all networks
            output = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True).decode()
            
            # Try to get adapter info for noise floor (might not be available)
            try:
                adapter_info = subprocess.check_output("netsh wlan show interfaces", shell=True).decode()
                # If available, we might find noise floor or use RSSI to estimate it
                # Windows doesn't directly expose noise floor
            except:
                pass
            
            # Parse the output to extract SSIDs and signal strength
            ssid_blocks = re.split(r"SSID \d+ : ", output)[1:]  
            
            for block in ssid_blocks:
                lines = block.strip().split('\n')
                if not lines:
                    continue
                    
                ssid = lines[0].strip()
                if not ssid:
                    continue
                    
                # Find signal strength
                signal_match = re.search(r"Signal\s*:\s*(\d+)%", block)
                # Extract authentication type
                auth_match = re.search(r"Authentication\s*:\s*(\S+)", block)
                # Extract channel
                channel_match = re.search(r"Channel\s*:\s*(\d+)", block)
                
                if signal_match:
                    signal_percent = int(signal_match.group(1))
                    # Simple conversion formula: 100% = -50dBm, 0% = -100dBm
                    signal_dbm = int((signal_percent / 2) - 100)
                    
                    # Calculate SNR (Signal-to-Noise Ratio)
                    snr = signal_dbm - noise_floor
                    
                    # Get authentication type
                    auth_type = auth_match.group(1) if auth_match else "Unknown"
                    
                    # Get channel
                    channel = int(channel_match.group(1)) if channel_match else 0
                    
                    # Add this network to our list
                    wifi_data.append({
                        "ssid": ssid, 
                        "signal": signal_dbm,
                        "signal_percent": signal_percent,
                        "auth": auth_type,
                        "channel": channel,
                        "noise_floor": noise_floor,
                        "snr": snr
                    })
            
            print(f"Found {len(wifi_data)} networks in scan")

        except Exception as e:
            print(f"Error fetching WiFi data: {str(e)}")

    elif os_type == "Linux":
        try:
            # Try to use iwlist for Linux
            interfaces = subprocess.check_output(["ls", "/sys/class/net"]).decode().split()
            wifi_interface = None
            
            # Find the first wireless interface
            for interface in interfaces:
                try:
                    output = subprocess.check_output(["iwconfig", interface], stderr=subprocess.DEVNULL).decode()
                    if "ESSID" in output:
                        wifi_interface = interface
                        break
                except:
                    continue
            
            if wifi_interface:
                # Try to get noise floor from iw survey
                try:
                    survey_output = subprocess.check_output(["iw", "dev", wifi_interface, "survey", "dump"], stderr=subprocess.DEVNULL).decode()
                    noise_match = re.search(r"noise:\s*(-\d+)", survey_output)
                    if noise_match:
                        noise_floor = int(noise_match.group(1))
                except:
                    pass
                
                output = subprocess.check_output(["sudo", "iwlist", wifi_interface, "scan"]).decode()
                network_sections = re.split(r"Cell \d+ - ", output)[1:]
                
                for section in network_sections:
                    ssid_match = re.search(r'ESSID:"(.*?)"', section)
                    signal_match = re.search(r"Signal level=(-?\d+) dBm", section)
                    # Extract channel
                    channel_match = re.search(r"Channel:(\d+)", section)
                    # Extract encryption
                    encryption_match = re.search(r"Encryption key:(on|off)", section)
                    auth_match = re.search(r"IE: (?:WPA|IEEE 802.11i/WPA2|WPA2) Version \d+", section)
                    
                    if ssid_match and signal_match:
                        ssid = ssid_match.group(1)
                        signal_dbm = int(signal_match.group(1))
                        
                        # Calculate SNR
                        snr = signal_dbm - noise_floor
                        
                        # Get channel
                        channel = int(channel_match.group(1)) if channel_match else 0
                        
                        # Determine authentication type
                        auth_type = "Open"
                        if encryption_match and encryption_match.group(1) == "on":
                            if auth_match:
                                if "WPA2" in auth_match.group(0):
                                    auth_type = "WPA2"
                                else:
                                    auth_type = "WPA"
                            else:
                                auth_type = "WEP"
                        
                        # Calculate approximate percentage
                        signal_percent = max(0, min(100, 2 * (signal_dbm + 100)))
                        
                        wifi_data.append({
                            "ssid": ssid, 
                            "signal": signal_dbm,
                            "signal_percent": signal_percent,
                            "auth": auth_type,
                            "channel": channel,
                            "noise_floor": noise_floor,
                            "snr": snr
                        })
        except Exception as e:
            print(f"Error fetching WiFi data on Linux: {str(e)}")
    
    return wifi_data

def aggregate_wifi_samples(samples):
    if not samples:
        return []
    
    # If only one sample, return it directly
    if len(samples) == 1:
        return sorted(samples[0], key=lambda n: n["signal"], reverse=True)
    
    # Combine samples for better accuracy
    networks_by_ssid = {}
    
    for sample in samples:
        for network in sample:
            ssid = network["ssid"]
            if ssid not in networks_by_ssid:
                networks_by_ssid[ssid] = []
            networks_by_ssid[ssid].append(network)
    
    # Create the final list with averaged values
    result = []
    for ssid, networks in networks_by_ssid.items():
        # Average signal strength
        signal_values = [n["signal"] for n in networks]
        snr_values = [n["snr"] for n in networks]
        avg_signal = int(statistics.mean(signal_values))
        avg_snr = int(statistics.mean(snr_values))
        
        # Get other fields from the strongest sample
        strongest = max(networks, key=lambda n: n["signal"])
        
        # Add to result with combined data
        result.append({
            "ssid": ssid,
            "signal": avg_signal,
            "signal_percent": strongest.get("signal_percent", 0),
            "auth": strongest.get("auth", "Unknown"),
            "channel": strongest.get("channel", 0),
            "noise_floor": strongest.get("noise_floor", -95),
            "snr": avg_snr
        })
    
    # Sort by signal strength
    return sorted(result, key=lambda n: n["signal"], reverse=True)

@app.route('/')
def index():
    return render_template('map.html')

@app.route('/get_wifi', methods=['POST'])
def get_wifi():
    data = request.json
    latitude = data.get('lat')
    longitude = data.get('lon')
    samples = data.get('samples', 1)  # Default to 1 sample for speed
    
    # Get WiFi data with short scan time
    wifi_networks = get_wifi_networks(samples=samples)
    
    # Store WiFi data for this location
    location_key = f"{latitude:.6f},{longitude:.6f}"
    wifi_locations[location_key] = wifi_networks
    
    # Update signal history
    for network in wifi_networks:
        ssid = network['ssid']
        if ssid not in signal_history:
            signal_history[ssid] = []
        
        signal_history[ssid].append({
            "timestamp": datetime.now().isoformat(),
            "signal": network['signal'],
            "location": location_key
        })
        if len(signal_history[ssid]) > 5:  # Reduced history length
            signal_history[ssid].pop(0)
    
    # Save data to file after each scan
    save_data_to_file()
    
    return jsonify({
        "latitude": latitude, 
        "longitude": longitude, 
        "wifi": wifi_networks,
        "timestamp": datetime.now().isoformat()
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

# Load existing data when the app starts
load_existing_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
