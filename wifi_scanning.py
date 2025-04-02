import pywifi
import time
import csv
import requests

def get_location():
    """Fetch approximate latitude and longitude using an IP-based geolocation API."""
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        lat, lon = map(float, data["loc"].split(","))
        return lat, lon
    except Exception as e:
        print("Error getting location:", e)
        return None, None

def scan_wifi():
    """Scan for WiFi networks and collect SSID, BSSID, signal strength, and frequency."""
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    
    iface.scan()
    time.sleep(2)  # Allow scan to complete
    
    results = iface.scan_results()
    
    lat, lon = get_location()
    wifi_data = []
    for network in results:
        wifi_data.append({
            "SSID": network.ssid,
            "BSSID": network.bssid,
            "Signal Strength (dBm)": network.signal,
            "Frequency (MHz)": network.freq,
            "Latitude": lat,
            "Longitude": lon
        })
    
    return wifi_data

def save_to_csv(data, filename="wifi_data.csv"):
    """Save collected WiFi data to a CSV file."""
    keys = data[0].keys()
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    wifi_results = scan_wifi()
    save_to_csv(wifi_results)
    print("WiFi scan complete.")
