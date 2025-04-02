from flask import Flask, render_template, request, jsonify
import subprocess
import platform
import re

app = Flask(__name__)

# Store WiFi data by location
wifi_locations = {}

# Function to get WiFi SSIDs and signal strength
def get_wifi_networks():
    wifi_data = []
    os_type = platform.system()

    if os_type == "Windows":
        try:
            # Forces a rescan of available networks before fetching data
            try:
                subprocess.check_output("netsh wlan disconnect", shell=True)
                subprocess.check_output("netsh wlan connect", shell=True)
                # Brief pause to allow for reconnection
                import time
                time.sleep(1)
            except:
                # Continue even if disconnect/reconnect fails
                pass
                
            output = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True).decode()
            
            # Split by SSID sections instead of blank lines
            ssid_sections = re.split(r"SSID \d+ : ", output)[1:]  # Skip the first empty element
            
            for section in ssid_sections:
                lines = section.strip().split('\n')
                if lines:
                    ssid = lines[0].strip()  # The SSID name is the first line
                    
                    # Find all BSSIDs and their signal strengths in this section
                    bssid_signal_matches = re.findall(r"BSSID \d+.*?Signal\s*:\s*(\d+)%", section, re.DOTALL)
                    
                    if bssid_signal_matches:
                        # Use the strongest signal if there are multiple BSSIDs
                        strongest_signal = max(int(signal) for signal in bssid_signal_matches)
                        signal_dbm = (strongest_signal / 2) - 100  # Approximate dBm conversion
                        
                        # Add this network to our list
                        wifi_data.append({"ssid": ssid, "signal": int(signal_dbm)})
            
            # Debug output to see what networks we're finding
            print(f"Found {len(wifi_data)} networks: {[n['ssid'] for n in wifi_data]}")

        except Exception as e:
            print("Error fetching WiFi data:", e)

    elif os_type == "Linux":
        try:
            output = subprocess.check_output(["sudo", "iwlist", "wlan0", "scan"]).decode()
            networks = re.findall(r"ESSID:\"(.*?)\".*?Signal level=(-?\d+) dBm", output, re.DOTALL)
            for ssid, signal in networks:
                wifi_data.append({"ssid": ssid, "signal": int(signal)})
        except Exception as e:
            print("Error fetching WiFi data:", e)

    return wifi_data


@app.route('/')
def index():
    return render_template('map.html')

@app.route('/get_wifi', methods=['POST'])
def get_wifi():
    data = request.json
    latitude = data.get('lat')
    longitude = data.get('lon')
    
    wifi_networks = get_wifi_networks()
    
    # Store WiFi data for this location
    location_key = f"{latitude:.6f},{longitude:.6f}"
    wifi_locations[location_key] = wifi_networks
    
    return jsonify({
        "latitude": latitude, 
        "longitude": longitude, 
        "wifi": wifi_networks
    })

@app.route('/get_all_wifi', methods=['GET'])
def get_all_wifi():
    # Return all stored WiFi networks
    all_ssids = set()
    for location_data in wifi_locations.values():
        for network in location_data:
            all_ssids.add(network['ssid'])
            
    return jsonify({"all_ssids": list(all_ssids)})

if __name__ == '__main__':
    app.run(debug=True)
