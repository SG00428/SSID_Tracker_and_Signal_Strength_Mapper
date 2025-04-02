import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data from CSV
df = pd.read_csv("wifi_data_1.csv")

# Convert Timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# 1. Time vs Signal Strength (Line Graph)
plt.figure(figsize=(10, 5))
sns.lineplot(x=df['Timestamp'], y=df['Signal Strength (%)'], hue=df['SSID'], marker='o')
plt.xticks(rotation=45)
plt.title("Time vs Signal Strength")
plt.xlabel("Time")
plt.ylabel("Signal Strength (%)")
plt.legend(title="SSID")
plt.grid()
plt.show()

# 2. SSID-wise Signal Strength (Multiple Line Graphs)
plt.figure(figsize=(10, 5))
sns.lineplot(data=df, x="Timestamp", y="Signal Strength (%)", hue="SSID", style="SSID", markers=True)
plt.xticks(rotation=45)
plt.title("SSID-wise Signal Strength")
plt.xlabel("Time")
plt.ylabel("Signal Strength (%)")
plt.legend(title="SSID")
plt.grid()
plt.show()

# 3. Heatmap of Signal Strength (If moving)
plt.figure(figsize=(8, 6))

# Create scatter plot using Matplotlib's scatter instead of seaborn's scatterplot
sc = plt.scatter(df['Longitude'], df['Latitude'], c=df['Signal Strength (%)'], cmap='coolwarm', s=100, alpha=0.75)

# Add colorbar
plt.colorbar(sc, label='Signal Strength (%)')

plt.title("Heatmap of Wi-Fi Signal Strength")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()


# 4. Bar Chart of Average Signal Strength per SSID
plt.figure(figsize=(8, 5))
avg_signal = df.groupby('SSID')['Signal Strength (%)'].mean().reset_index()
sns.barplot(data=avg_signal, x='SSID', y='Signal Strength (%)', palette='viridis')
plt.title("Average Signal Strength per SSID")
plt.xlabel("SSID")
plt.ylabel("Average Signal Strength (%)")
plt.xticks(rotation=45)
plt.grid(axis='y')
plt.show()
