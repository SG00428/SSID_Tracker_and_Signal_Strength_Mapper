import subprocess
import re
import time
import csv
import matplotlib.pyplot as plt
from datetime import datetime
from geopy.geocoders import Nominatim

CSV_FILE = "wifi_data_1.csv"

def get_wifi_networks():
    """Fetch Wi-Fi SSIDs, BSSIDs, and Signal Strength using Windows netsh command."""
    result = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"], capture_output=True, text=True)
    networks = result.stdout.split("\n")

    wifi_data = []
    ssid, bssid, signal = None, None, None

    for line in networks:
        line = line.strip()
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":")[1].strip() if ":" in line else None
        elif "BSSID" in line:
            bssid = line.split(":")[1].strip() if ":" in line else None
        elif "Signal" in line:
            signal = re.findall(r'\d+', line.split(":")[1])  # Extract numeric value
            signal = int(signal[0]) if signal else None

        if ssid and bssid and signal is not None:
            wifi_data.append((ssid, bssid, signal))
            bssid, signal = None, None  # Reset for next entry

    return wifi_data

def get_gps_location():
    """Get approximate GPS location based on IP."""
    geolocator = Nominatim(user_agent="wifi-tracker")
    location = geolocator.geocode("IIT Gandhinagar, Gujarat")
    if location:
        return location.latitude, location.longitude
    return None, None

def write_to_csv(data):
    """Writes Wi-Fi data to a CSV file."""
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(data)

def plot_signal_graph():
    """Plots signal strength vs time."""
    timestamps = []
    signals = []

    with open(CSV_FILE, mode="r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            timestamps.append(datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S"))
            signals.append(int(row[3]))

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, signals, marker='o', linestyle='-', color='b', label="Signal Strength")
    plt.xlabel("Time")
    plt.ylabel("Signal Strength (%)")
    plt.title("Wi-Fi Signal Strength Over Time")
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid()
    plt.show()

def main():
    duration = 90  # 1.5 minutes (90 seconds)
    interval = 10  # 10-second break
    start_time = time.time()

    # Create CSV file with header
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "SSID", "BSSID", "Signal Strength (%)", "Latitude", "Longitude"])

    while time.time() - start_time < duration:
        print("\n🔍 Scanning for Wi-Fi networks...\n")
        wifi_networks = get_wifi_networks()
        latitude, longitude = get_gps_location()

        if not wifi_networks:
            print("No Wi-Fi networks found.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_to_write = [(timestamp, ssid, bssid, signal, latitude, longitude) for ssid, bssid, signal in wifi_networks]
            write_to_csv(data_to_write)

            for ssid, bssid, signal in wifi_networks:
                print(f"📡 SSID: {ssid} | 🔢 BSSID: {bssid} | 📶 Signal: {signal}% | 📍 {latitude}, {longitude}")

        print("\n⏳ Waiting 10 seconds before next scan...\n")
        time.sleep(interval)

    print("\n✅ Data collection complete. Plotting graph...\n")
    plot_signal_graph()

if __name__ == "__main__":
    main()

