##### without heatmap and with value ###########

# import folium
# import pandas as pd

# def create_heatmap(csv_file):
#     df = pd.read_csv(csv_file)

#     map_center = [df["Latitude"].mean(), df["Longitude"].mean()]
#     wifi_map = folium.Map(location=map_center, zoom_start=15)

#     for _, row in df.iterrows():
#         folium.CircleMarker(
#             location=[row["Latitude"], row["Longitude"]],
#             radius=10,
#             popup=f"SSID: {row['SSID']}\nSignal: {row['Signal Strength (dBm)']} dBm",
#             color="blue" if row['Signal Strength (dBm)'] > -60 else "red",
#             fill=True
#         ).add_to(wifi_map)

#     wifi_map.save("wifi_map.html")
#     print("Heatmap generated.")

# if __name__ == "__main__":
#     create_heatmap("wifi_data.csv")



import pandas as pd
import folium
from folium.plugins import HeatMap
import random

def create_wifi_heatmap(csv_file):
    # Load CSV
    df = pd.read_csv(csv_file)
    print(df.head())  # Check the first few rows
    print(df["SSID"].unique())
    # Check if Latitude & Longitude columns exist
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        print("Error: CSV file must contain Latitude and Longitude.")
        return

    # Convert signal strength to positive values for heatmap
    df["Strength"] = df["Signal Strength (dBm)"].apply(lambda x: -x)

    # Create map centered at IITGN
    iitgn_location = [23.2185, 72.6847]
    wifi_map = folium.Map(location=iitgn_location, zoom_start=16)

    # HeatMap data: [Latitude, Longitude, Strength]
    heat_data = df[["Latitude", "Longitude", "Strength"]].values.tolist()
    HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(wifi_map)

    # Add Circle Markers with Signal Strength Labels
    for _, row in df.iterrows():
        ssid = str(row["SSID"])  # Convert to string to avoid float errors
        lat, lon = row["Latitude"], row["Longitude"]
        lat += random.uniform(-0.0001, 0.0001)  # Small jitter
        lon += random.uniform(-0.0001, 0.0001)
        print(f"Plotting: SSID={ssid}, Lat={lat}, Lon={lon}")  # Debugging line
    
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):  # Ensure valid coordinates
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=8,
                color="red" if "IITGN-SSO" in ssid else "blue",  # Check SSID safely
                fill=True,
                fill_color="red" if "IITGN-SSO" in ssid else "blue",
                fill_opacity=0.7,
                popup=f"SSID: {ssid}<br>Signal: {row['Signal Strength (dBm)']} dBm"
            ).add_to(wifi_map)


    # Save the map
    wifi_map.save("wifi_heatmap_with_values.html")
    print("Heatmap saved as wifi_heatmap_with_values.html")

if __name__ == "__main__":
    create_wifi_heatmap("wifi_data.csv")
