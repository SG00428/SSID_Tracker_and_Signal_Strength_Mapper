// Add this before the closing </script> tag

let monitoringChart = null;
let currentMonitorId = null;
let monitoringInterval = null;

function updateMonitoringSelect() {
    const select = document.getElementById('monitor-ssid');
    const currentValue = select.value;
    
    // Clear existing options
    select.innerHTML = '<option value="">Select Network...</option>';
    
    // Add all tracked networks
    dataPoints.forEach(point => {
        point.networks.forEach(network => {
            const option = document.createElement('option');
            option.value = network.ssid;
            option.textContent = network.ssid;
            select.appendChild(option);
        });
    });
    
    // Restore previous selection if still available
    if (currentValue) {
        select.value = currentValue;
    }
}

function startMonitoring() {
    const ssid = document.getElementById('monitor-ssid').value;
    const duration = parseInt(document.getElementById('monitor-duration').value);
    const interval = parseInt(document.getElementById('monitor-interval').value);
    
    if (!ssid) {
        alert('Please select a network to monitor');
        return;
    }
    
    const status = document.getElementById('monitoring-status');
    status.innerHTML = '<div class="loading-indicator"></div>Starting monitoring...';
    
    fetch('/monitor_signal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            ssid: ssid,
            duration: duration,
            interval: interval
        }),
    })
    .then(response => response.json())
    .then(data => {
        currentMonitorId = data.monitor_id;
        status.textContent = 'Monitoring in progress...';
        
        // Initialize chart
        initializeMonitoringChart(ssid);
        
        // Start polling for data
        monitoringInterval = setInterval(() => {
            updateMonitoringData(currentMonitorId);
        }, interval * 1000);
        
        // Stop monitoring after duration
        setTimeout(() => {
            stopMonitoring();
        }, duration * 1000);
    })
    .catch(error => {
        console.error('Error:', error);
        status.textContent = 'Error starting monitoring';
    });
}

function initializeMonitoringChart(ssid) {
    const ctx = document.getElementById('monitoring-chart').getContext('2d');
    document.getElementById('monitoring-chart-container').style.display = 'block';
    
    if (monitoringChart) {
        monitoringChart.destroy();
    }
    
    monitoringChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: `${ssid} Signal Strength`,
                data: [],
                borderColor: '#007bff',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: -100,
                    max: -30,
                    title: {
                        display: true,
                        text: 'Signal Strength (dBm)'
                    }
                }
            }
        }
    });
}

function updateMonitoringData(monitorId) {
    fetch(`/get_monitoring_data/${monitorId}`)
        .then(response => response.json())
        .then(data => {
            if (data.data && data.data.length > 0) {
                data.data.forEach(point => {
                    monitoringChart.data.labels.push(
                        new Date(point.timestamp).toLocaleTimeString()
                    );
                    monitoringChart.data.datasets[0].data.push(point.signal);
                });
                
                // Keep only last 60 points
                if (monitoringChart.data.labels.length > 60) {
                    monitoringChart.data.labels.splice(0, 
                        monitoringChart.data.labels.length - 60);
                    monitoringChart.data.datasets[0].data.splice(0, 
                        monitoringChart.data.datasets[0].data.length - 60);
                }
                
                monitoringChart.update();
            }
        })
        .catch(error => console.error('Error updating monitoring data:', error));
}

function stopMonitoring() {
    if (monitoringInterval) {
        clearInterval(monitoringInterval);
        monitoringInterval = null;
    }
    currentMonitorId = null;
    document.getElementById('monitoring-status').textContent = 'Monitoring completed';
}

// Add event listener for the monitoring button
document.getElementById('start-monitoring').addEventListener('click', startMonitoring);

// Update monitoring select when new data is available
document.addEventListener('newDataAvailable', updateMonitoringSelect);