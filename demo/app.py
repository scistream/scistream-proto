#!/usr/bin/env python3
"""
USGS Earthquake Data Streaming Dashboard
Fetches and displays real-time earthquake data from USGS with streaming updates.
"""
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, Response
import time

app = Flask(__name__)

# Add custom filter for timestamp conversion
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to readable date/time format"""
    dt = datetime.fromtimestamp(int(timestamp))
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def get_earthquake_data():
    """Fetch the latest earthquake data from USGS API"""
    try:
        # Get earthquakes from the last hour
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # Format times for USGS API
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # USGS Earthquake API
        url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_str}&endtime={end_str}&minmagnitude=1"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                'earthquakes': data['features'],
                'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                'count': len(data['features'])
            }
        else:
            print(f"Error fetching USGS data: {response.status_code}")
            return {'earthquakes': [], 'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), 'count': 0}
                
    except Exception as e:
        print(f"Error getting earthquake data: {e}")
        return {'earthquakes': [], 'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), 'count': 0}

@app.route('/')
def index():
    """Renders the main dashboard page with streaming data."""
    data = get_earthquake_data()
    return render_template('index.html', 
                          earthquakes=data['earthquakes'], 
                          timestamp=data['timestamp'],
                          count=data['count'])

@app.route('/api/earthquakes')
def api_earthquakes():
    """Returns the current earthquake data as JSON."""
    data = get_earthquake_data()
    return jsonify({
        'earthquakes': data['earthquakes'],
        'timestamp': data['timestamp'],
        'count': data['count']
    })

@app.route('/stream')
def stream():
    """Provides server-sent events stream for real-time updates."""
    def event_stream():
        last_count = -1
        while True:
            # Get fresh data
            data = get_earthquake_data()
            count = data['count']
            
            # Only send if there's new data or every 10 seconds as a keepalive
            if count != last_count:
                last_count = count
                yield f"data: {json.dumps({'count': count, 'timestamp': data['timestamp']})}\n\n"
            
            # Sleep for a bit before checking again
            time.sleep(10)
    
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    print("Starting earthquake data streaming dashboard...")
    app.run(debug=True, host='0.0.0.0', port=5000)