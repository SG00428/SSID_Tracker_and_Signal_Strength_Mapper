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

# Store WiFi data by location
wifi_locations = {}
signal_history = {}

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

    if os_type == "Windows":
        try:
            # Quick adapter refresh
            subprocess.run("netsh wlan show networks mode=bssid", shell=True, stderr=subprocess.DEVNULL)
            
            # Get detailed info about all networks
            output = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True).decode()
            
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
                        "channel": channel
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
                            "channel": channel
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
        avg_signal = int(statistics.mean(signal_values))
        
        # Get other fields from the strongest sample
        strongest = max(networks, key=lambda n: n["signal"])
        
        # Add to result with combined data
        result.append({
            "ssid": ssid,
            "signal": avg_signal,
            "signal_percent": strongest.get("signal_percent", 0),
            "auth": strongest.get("auth", "Unknown"),
            "channel": strongest.get("channel", 0)
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
    data = {
        "locations": wifi_locations,
        "history": signal_history,
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
