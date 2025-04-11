import subprocess
import platform
import re
import time
import statistics
import json
import os
from datetime import datetime
import argparse
import sys
import urllib.request
import socket
import webbrowser
import math
from threading import Event

# File where data will be stored
DATA_FILE = 'dynamic_data.json'

# Distance threshold in degrees (~10 meters)
LOCATION_THRESHOLD = 0.0001

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters"""
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


def dynamic_wifi_collection(interval=10, duration=None, stop_event=None):
    """
    Continuously collect WiFi data with specified interval
    Overwrites data for same location, appends for new locations
    
    Args:
        interval: Time between scans in seconds
        duration: Total collection time in seconds (None for infinite)
        stop_event: Threading event to stop collection
    """
    print(f"Starting dynamic WiFi collection (interval: {interval}s)")
    print("Press Ctrl+C to stop collection")

    start_time = time.time()
    last_lat = None
    last_lon = None
    scan_count = 0
    
    # Distance threshold in meters - locations closer than this are considered the same
    location_distance_threshold = 0.5  # 10 meters threshold

    try:
        while True:
            # Check if we should stop
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - start_time) >= duration:
                print("\nCollection duration reached")
                break

            # Get current location
            lat, lon, loc_desc = get_current_location()
            if not lat or not lon:
                print("Could not determine location, skipping scan")
                time.sleep(interval)
                continue

            # Get WiFi data
            wifi_networks = get_wifi_networks(samples=3)
            scan_count += 1

            # Load existing data
            data = load_existing_data()
            timestamp = datetime.now().isoformat()

            # Check if we have an existing entry for this location (within threshold)
            location_found = False
            for key, location in data["locations"].items():
                location_lat = location["latitude"]
                location_lon = location["longitude"]
                
                # Calculate distance between current and stored location
                distance = calculate_distance(lat, lon, location_lat, location_lon)
                
                # If within threshold, consider it the same location
                if distance < location_distance_threshold:
                    # Update existing location data
                    data["locations"][key]["networks"] = wifi_networks
                    data["locations"][key]["timestamp"] = timestamp
                    data["locations"][key]["note"] = f"Updated scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    location_found = True
                    print(f"\rUpdating existing location - Scan #{scan_count} - Distance: {distance:.2f}m", end="")
                    break

            # If no existing location found, create new entry
            if not location_found:
                location_name = f"Dynamic_Scan_{timestamp}"
                location_key = f"{location_name}_{timestamp}"
                data["locations"][location_key] = {
                    "name": location_name,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": timestamp,
                    "networks": wifi_networks,
                    "note": f"New location scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
                print(f"\rNew location added - Scan #{scan_count}", end="")

            # Save updated data
            save_data(data)
            
            # Update last known location
            last_lat, last_lon = lat, lon
            
            # Wait for next interval
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nDynamic collection stopped by user")
    
    print(f"\nCollection completed: {scan_count} scans performed")
    return scan_count

# Function to get WiFi SSIDs and signal strength with configurable samples
def get_wifi_networks(samples=3, delay=0.2):
    all_samples = []
    
    for _ in range(samples):
        # Get a single scan
        networks = get_single_wifi_scan()
        if networks:
            all_samples.append(networks)
        # Wait between scans
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
        
        # Calculate signal variance if we have multiple samples
        signal_variance = None
        if len(signal_values) > 1:
            try:
                signal_variance = int(statistics.stdev(signal_values))
            except:
                pass
        
        # Get other fields from the strongest sample
        strongest = max(networks, key=lambda n: n["signal"])
        
        # Add to result with combined data
        network_data = {
            "ssid": ssid,
            "signal": avg_signal,
            "signal_percent": strongest.get("signal_percent", 0),
            "auth": strongest.get("auth", "Unknown"),
            "channel": strongest.get("channel", 0),
            "noise_floor": strongest.get("noise_floor", -95),
            "snr": avg_snr,
            "samples": len(networks)
        }
        
        # Add variance if available
        if signal_variance:
            network_data["signal_variance"] = signal_variance
        
        result.append(network_data)
    
    # Sort by signal strength
    return sorted(result, key=lambda n: n["signal"], reverse=True)

def load_existing_data():
    """Load existing data from the JSON file if it exists."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as file:
                return json.load(file)
    except Exception as e:
        print(f"Error loading existing data: {e}")
    
    # Return default structure if file doesn't exist or has issues
    return {
        "locations": {},
        "metadata": {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }

def save_data(data_obj):
    """Save the data to the JSON file."""
    # Update the last_updated timestamp
    data_obj["metadata"]["last_updated"] = datetime.now().isoformat()
    
    try:
        with open(DATA_FILE, 'w') as file:
            json.dump(data_obj, file, indent=2)
        print(f"Data saved to {DATA_FILE}")
    except Exception as e:
        print(f"Error saving data: {e}")

# Define known locations for easy reference
KNOWN_LOCATIONS = {
    "library": {"latitude": 23.2120, "longitude": 72.6868, "description": "Main Library Building"},
    "academic_block": {"latitude": 23.2106, "longitude": 72.6845, "description": "Academic Block"},
    "hostel_a": {"latitude": 23.2110, "longitude": 72.6850, "description": "Hostel A"},
    "hostel_b": {"latitude": 23.2112, "longitude": 72.6855, "description": "Hostel B"},
    "cafeteria": {"latitude": 23.2115, "longitude": 72.6860, "description": "Main Cafeteria"},
    "sports_complex": {"latitude": 23.2090, "longitude": 72.6830, "description": "Sports Complex"},
    "admin_block": {"latitude": 23.2100, "longitude": 72.6840, "description": "Administration Block"}
}

def get_known_location(location_name):
    """Check if the location is in our predefined list."""
    if not location_name:
        return None, None, None
    
    # Convert to lowercase and replace spaces with underscores for matching
    location_key = location_name.lower().replace(' ', '_')
    
    # Try direct match first
    if location_key in KNOWN_LOCATIONS:
        loc = KNOWN_LOCATIONS[location_key]
        return loc["latitude"], loc["longitude"], loc["description"]
    
    # Try partial match
    for key, loc in KNOWN_LOCATIONS.items():
        if key in location_key or location_key in key:
            print(f"Using known location: {key} ({loc['description']})")
            return loc["latitude"], loc["longitude"], loc["description"]
    
    # No match found
    return None, None, None

def list_known_locations():
    """Print a list of known locations."""
    print("\nKnown locations:")
    for key, loc in KNOWN_LOCATIONS.items():
        print(f"  {key}: {loc['description']} ({loc['latitude']}, {loc['longitude']})")
    print()

def get_current_location():
    """Try to determine the current device location without using external libraries."""
    try:
        print("Attempting to determine your current location...")
        # Try to get public IP-based location (not very accurate but a fallback)
        try:
            # Using urllib instead of requests
            with urllib.request.urlopen('https://ipinfo.io/json', timeout=5) as response:
                data = json.loads(response.read().decode())
                if 'loc' in data:
                    lat, lon = map(float, data['loc'].split(','))
                    print(f"Location detected: {lat}, {lon} (approximate based on IP)")
                    return lat, lon, f"IP-based location: {data.get('city', ''), {data.get('region', '')}}"
        except Exception as e:
            print(f"Error determining location via IP: {e}")
            
        # Rest of the browser-based approach remains the same
        import http.server
        import threading
        import time
        import urllib.parse
        
        location_data = {'lat': None, 'lon': None}
        server_port = 8000
        
        # Find an available port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                s.bind(('', server_port))
                s.close()
                break
            except:
                server_port += 1
                if server_port > 9000:  # Limit the search
                    raise Exception("No available ports found")
        
        class LocationHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith('/setlocation'):
                    query = urllib.parse.urlparse(self.path).query
                    params = dict(urllib.parse.parse_qsl(query))
                    
                    if 'lat' in params and 'lon' in params:
                        location_data['lat'] = float(params['lat'])
                        location_data['lon'] = float(params['lon'])
                        
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>Location received!</h1><p>You can close this window now.</p></body></html>")
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = """
                    <html>
                    <head>
                        <title>Location Permission</title>
                        <script>
                        function getLocation() {
                            if (navigator.geolocation) {
                                navigator.geolocation.getCurrentPosition(showPosition, showError);
                                document.getElementById('status').innerHTML = "Getting your location...";
                            } else {
                                document.getElementById('status').innerHTML = "Geolocation is not supported by this browser.";
                            }
                        }
                        
                        function showPosition(position) {
                            var lat = position.coords.latitude;
                            var lon = position.coords.longitude;
                            document.getElementById('status').innerHTML = 
                                "Location detected: " + lat + ", " + lon;
                            
                            // Send location back to server
                            window.location.href = "/setlocation?lat=" + lat + "&lon=" + lon;
                        }
                        
                        function showError(error) {
                            switch(error.code) {
                                case error.PERMISSION_DENIED:
                                    document.getElementById('status').innerHTML = "User denied the request for Geolocation."
                                    break;
                                case error.POSITION_UNAVAILABLE:
                                    document.getElementById('status').innerHTML = "Location information is unavailable."
                                    break;
                                case error.TIMEOUT:
                                    document.getElementById('status').innerHTML = "The request to get user location timed out."
                                    break;
                                case error.UNKNOWN_ERROR:
                                    document.getElementById('status').innerHTML = "An unknown error occurred."
                                    break;
                            }
                        }
                        
                        // Run when page loads
                        window.onload = getLocation;
                        </script>
                    </head>
                    <body>
                        <h1>WiFi Data Collector - Location Permission</h1>
                        <p>To collect accurate location data, please allow location access when prompted.</p>
                        <p id="status">Waiting for location permission...</p>
                        <button onclick="getLocation()">Try Again</button>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode())
                    
            def log_message(self, format, *args):
                # Suppress log messages
                return
        
        # Start HTTP server in a separate thread
        server = http.server.HTTPServer(('', server_port), LocationHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        
        # Open browser to get user permission for location
        webbrowser.open(f'http://localhost:{server_port}')
        print(f"A browser window has been opened to request your location.")
        print("Please allow location access when prompted.")
        
        # Wait for location data with timeout
        timeout = 60  # seconds
        start_time = time.time()
        while location_data['lat'] is None and time.time() - start_time < timeout:
            time.sleep(1)
        
        # Shutdown server
        server.shutdown()
        thread.join()
        
        if location_data['lat'] is not None and location_data['lon'] is not None:
            print(f"Location detected: {location_data['lat']}, {location_data['lon']}")
            return location_data['lat'], location_data['lon'], "Browser-based geolocation"
            
    except Exception as e:
        print(f"Error determining location via browser: {e}")
    
    return None, None, None

def collect_wifi_data(location_name=None, latitude=None, longitude=None, samples=3, note=None):
    """Collect wifi data at the current location and save to JSON file."""
    print(f"Collecting WiFi data with {samples} samples...")
    
    # Always try to auto-detect location first instead of relying on predefined locations
    auto_lat, auto_lon, auto_desc = get_current_location()
    
    if auto_lat and auto_lon:
        latitude = auto_lat
        longitude = auto_lon
        print(f"Using detected location: {latitude}, {longitude}")
        if note is None and auto_desc:
            note = f"Auto-detected location: {auto_desc}"
    
    # Only check known locations if auto-detection failed
    elif latitude is None or longitude is None:
        known_lat, known_lon, known_desc = get_known_location(location_name)
        if known_lat and known_lon:
            if latitude is None:
                latitude = known_lat
                print(f"Using known latitude: {latitude}")
            if longitude is None:
                longitude = known_lon
                print(f"Using known longitude: {longitude}")
            if note is None and known_desc:
                note = f"Known location: {known_desc}"
    
    # Get wifi data
    wifi_networks = get_wifi_networks(samples=samples)
    
    # Load existing data
    data = load_existing_data()
    
    # Use location name from command line or generate one based on current time
    if not location_name:
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        location_name = f"Location_Scan_{current_time}"
        print(f"Using auto-generated location name: {location_name}")
    
    # If coordinates are still not determined (both auto-detection and known locations failed)
    if latitude is None:
        try:
            latitude_input = input("Could not determine latitude automatically. Please enter latitude (e.g. 23.2100): ")
            latitude = float(latitude_input) if latitude_input.strip() else 0.0
        except:
            print("Invalid latitude, using 0.0")
            latitude = 0.0
    
    if longitude is None:
        try:
            longitude_input = input("Could not determine longitude automatically. Please enter longitude (e.g. 72.6845): ")
            longitude = float(longitude_input) if longitude_input.strip() else 0.0
        except:
            print("Invalid longitude, using 0.0")
            longitude = 0.0
    
    # If no note provided, use an auto-generated one
    if note is None:
        note = f"Automatically collected on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Create a unique location key
    timestamp = datetime.now().isoformat()
    location_key = f"{location_name}_{timestamp}"
    
    # Add the new data
    data["locations"][location_key] = {
        "name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "networks": wifi_networks,
        "note": note if note else ""
    }
    
    # Save the updated data
    save_data(data)
    
    # Print summary
    print(f"\nFound {len(wifi_networks)} WiFi networks at {location_name} ({latitude}, {longitude})")
    for network in wifi_networks:
        signal_quality = "Excellent" if network["signal"] > -65 else \
                         "Good" if network["signal"] > -75 else \
                         "Fair" if network["signal"] > -85 else "Poor"
        print(f"  {network['ssid']}: {network['signal']} dBm ({signal_quality})")
    
    print(f"\nData saved to {DATA_FILE}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Collect WiFi network data and store in a JSON file.')
    parser.add_argument('--location', '-l', help='Name of the location')
    parser.add_argument('--latitude', '-lat', type=float, help='Latitude in decimal degrees')
    parser.add_argument('--longitude', '-lon', type=float, help='Longitude in decimal degrees')
    parser.add_argument('--samples', '-s', type=int, default=3, help='Number of samples to collect (default: 3)')
    parser.add_argument('--note', '-n', help='Note about this location')
    parser.add_argument('--output', '-o', help='Output JSON file (default: wifi_data.json)')
    parser.add_argument('--list-locations', action='store_true', help='List known locations and exit')
    return parser.parse_args()

def main():
    parser = argparse.ArgumentParser(description='Dynamically collect WiFi network data over time.')
    parser.add_argument('--interval', '-i', type=int, default=10,
                      help='Scanning interval in seconds (default: 10)')
    parser.add_argument('--duration', '-d', type=int,
                      help='Total collection duration in seconds (default: infinite)')
    parser.add_argument('--output', '-o',
                      help='Output JSON file (default: dynamic_data.json)')
    args = parser.parse_args()

    global DATA_FILE
    if args.output:
        DATA_FILE = args.output

    print("=== Dynamic WiFi Data Collector ===")
    print(f"Output file: {DATA_FILE}")
    print(f"Interval: {args.interval} seconds")
    if args.duration:
        print(f"Duration: {args.duration} seconds")
    else:
        print("Duration: infinite (Ctrl+C to stop)")

    dynamic_wifi_collection(
        interval=args.interval,
        duration=args.duration
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
