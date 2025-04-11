# WiFi Signal Strength Mapper

A modular and interactive web-based application to map, analyze, and monitor Wi-Fi signal strengths across geographic locations. Built using Python and modern web technologies, this tool is designed to assist users in visualizing wireless network coverage and analyzing network performance.

---

## Project Overview

This application collects and visualizes data about nearby Wi-Fi networks, including:
- Signal strengths
- Authentication types
- Channel information
- Network names (SSIDs)

It displays this information on an interactive web map, helping users identify coverage gaps, signal quality variations, and optimal connection zones.

---

## Files and Directory Structure

├── dynamic.py # Main server script for scanning and visualization ├── wifi_data.json # Persistent storage for collected Wi-Fi data ├── dynamic_data.json # Temporary cache for real-time scanning ├── templates/ │ └── map.html # HTML interface with interactive map

---

## ✨ Features

- **Real-time Wi-Fi network scanning**
- **Interactive Leaflet.js map visualization**
- **Signal strength heatmaps**
- **Detailed network info display**
- **Historical data tracking**
- **Support for multiple authentication types**
- **Signal quality analysis with Chart.js**
- **Exportable JSON data**

---

## Requirements

- Python 3.7+
- A modern web browser with JavaScript enabled

## Installation & Running

### Step 1: Clone the repository

```bash
- git clone https://github.com/your-username/wifi-signal-mapper.git
- cd wifi-signal-mapper
- Step 2: Install dependencies
- pip install flask geopy scapy wifi
- Step 3: Run the server
- python dynamic.py
- Step 4: Open in your browser
- Navigate to:
- http://127.0.0.1:5000

---

Usage Instructions
The map will load showing any previously recorded scan data.

Click anywhere on the map to perform a Wi-Fi scan at that location.

Use the "Show Signal Heatmap" checkbox to enable signal strength visualization.

Click on individual networks in the list to view detailed network information.

Use the download/export buttons to save scan data in JSON format for further analysis.

---

Technical Stack
Backend: Flask (Python)

Frontend: HTML, CSS, JavaScript

Visualization: Leaflet.js, Chart.js

Geolocation: Browser Geolocation API

Data Storage: JSON files

---

License
This project is open-source and available under the MIT License.

