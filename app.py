from flask import Flask, render_template, request, jsonify
import subprocess
import platform
import re

app = Flask(__name__)

# Function to get WiFi SSIDs and signal strength

def get_wifi_networks():
    wifi_data = []
    os_type = platform.system()

    if os_type == "Windows":
        try:
            output = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True).decode()
            networks = re.split(r"\n\n", output)  # Splitting networks by blank lines
            for network in networks:
                ssid_match = re.search(r"SSID \d+ : (.+)", network)
                signal_match = re.findall(r"Signal\s*:\s*(\d+)%", network)

                if ssid_match and signal_match:
                    ssid = ssid_match.group(1)
                    signal_percent = int(signal_match[0])  # Get first BSSID's signal
                    signal_dbm = (signal_percent / 2) - 100  # Approximate dBm conversion
                    
                    wifi_data.append({"ssid": ssid, "signal": int(signal_dbm)})

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
    
    return jsonify({"latitude": latitude, "longitude": longitude, "wifi": wifi_networks})

if __name__ == '__main__':
    app.run(debug=True)
