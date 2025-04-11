
# 📶 SSID Tracker & WiFi Signal Strength Mapper 

A cross-platform project that scans available WiFi networks, maps their signal strength across locations within the **IIT Gandhinagar campus**, and provides an interactive heatmap and SSID details via a web interface. It supports both static and dynamic data collection modes.

---

## Requirements

Ensure you have the required Python packages installed:

```bash
pip install -r requirements.txt
You may also need to run the script with administrator/root privileges depending on your platform, especially for WiFi scanning.

Project Overview
This project enables:

Campus-wide WiFi signal strength mapping using heatmaps

SSID tracking with security type, signal strength, and channel info

Location-specific insights via an interactive web UI

Dynamic and static data collection capabilities

⚙️ How to Run
Run Static Web App
bash
Copy
Edit
python static_app.py
Opens a local web server that uses the static dataset from wifi_data.json.

Run Dynamic Web App with Live WiFi Scanning
Step 1: Start scanning every 10 seconds:

bash
Copy
Edit
python dynamic.py --interval 10
Step 2: Run the dynamic web app:

bash
Copy
Edit
python app.py
This will launch a live dashboard that updates with new scans at runtime.

Methodology & Implementation
WiFi Scanning
Uses platform-specific commands to scan WiFi networks and extract:

SSID (network name)

Signal strength in %, converted to dBm using:

python
Copy
Edit
signal_dbm = (signal_percent / 2) - 100
SNR (Signal-to-Noise Ratio), calculated as:

python
Copy
Edit
SNR = signal_dbm - noise_floor
A noise_floor of -95 dBm is assumed as baseline ambient noise. It helps normalize signal quality and derive more meaningful SNR values.

Also captures:

Channel

Authentication type (e.g., WPA2, Open)

Geolocation & Mapping
Each scan result is tied to a manually/geotagged campus coordinate.

Uses Leaflet.js for:

Campus boundary overlay

Heatmaps of signal strength

SSID metadata on-click popups

Implements a nearest-point algorithm to:

Determine the closest WiFi data point to a user click on the map

Provide detailed info for that location

Uses spatial interpolation to estimate signal strengths in regions without direct measurements

Features Implemented
A. Interactive Map Interface
Campus boundary visualization

📍 94 Data Collection Points

Color-coded Signal Strengths:

🟢 Excellent

🟡 Good

🟠 Fair

🔴 Poor

Location-Specific WiFi Details: Clicking on a location displays nearby network info

B. Data Analysis
Downloadable WiFi Data for offline use

Signal Strength Heatmap

Network Filtering (e.g., view only IITGN-SSO or eduroam)

Signal Categories:

Excellent: -30 to -65 dBm

Good: -65 to -75 dBm

Fair: -75 to -85 dBm

Poor: -85 to -100 dBm

C. Technical Highlights
Nearest Point Algorithm

Spatial Interpolation

Progressive Enhancement (Supports continuous data addition)

Responsive Design for desktop and mobile
