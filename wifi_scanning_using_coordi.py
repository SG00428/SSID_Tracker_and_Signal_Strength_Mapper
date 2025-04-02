import folium
import pywifi
from pywifi import const
import time
from folium.plugins import HeatMap

# Define the area boundaries (Hostel area)
hostel_boundary = [
    (23.21144, 72.683386),
    (23.211205, 72.685907),
    (23.208763, 72.685926),
    (23.209519, 72.683377)
]

# Initialize WiFi scanner
def scan_wifi():
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]  # First WiFi interface
    iface.scan()
    time.sleep(3)  # Wait for scan results
    results = iface.scan_results()
    
    ssid_data = []
    for result in results:
        ssid_data.append({
            "ssid": result.ssid,
            "signal": result.signal,  # dBm (closer to 0 is stronger)
            "lat": 23.210,  # Replace with actual GPS logging logic
            "lon": 72.684  # Replace with actual GPS logging logic
        })
    
    return ssid_data

# Simulated or actual SSID data (replace lat/lon with real data)
wifi_data = scan_wifi()

# Create OpenStreetMap
map_center = (23.210, 72.684)
wifi_map = folium.Map(location=map_center, zoom_start=17, tiles="OpenStreetMap")

# Add hostel boundary
folium.PolyLine(hostel_boundary, color="blue", weight=3).add_to(wifi_map)

# Add WiFi markers
for wifi in wifi_data:
    folium.Marker(
        location=[wifi["lat"], wifi["lon"]],
        popup=f"SSID: {wifi['ssid']}<br>Signal: {wifi['signal']} dBm",
        icon=folium.Icon(color="blue", icon="wifi", prefix="fa")
    ).add_to(wifi_map)

# Create heatmap layer (signal strength visualization)
heatmap_data = [[wifi["lat"], wifi["lon"], wifi["signal"]] for wifi in wifi_data]
HeatMap(heatmap_data).add_to(wifi_map)

# Save to HTML
wifi_map.save("wifi_coordi_map.html")
print("WiFi Signal Map saved as wifi_signal_map.html")
