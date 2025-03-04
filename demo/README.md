# Simple USGS Earthquake Dashboard

A minimalist web application that displays real-time earthquake data from the USGS API.

## Features

- Fetches earthquake data from the USGS API
- Displays earthquake information in a clean, simple format
- Color-coded magnitude indicators
- Manual refresh with a button click

## Setup and Installation

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## How It Works

1. When a user visits the page, the application fetches the latest earthquake data from the USGS API
2. The data is rendered directly into an HTML template
3. Users can refresh the data by clicking the refresh button
4. Earthquakes are displayed with color-coded magnitude indicators for easy reading

## Files

- `app.py` - The Flask application that fetches and renders data
- `templates/index.html` - The HTML template for displaying earthquake data
- `requirements.txt` - Python dependencies
- `README.md` - This documentation file

## Data Source

The application uses the USGS Earthquake Catalog API:
`https://earthquake.usgs.gov/fdsnws/event/1/query`

## Extending the Demo

- Add auto-refresh functionality
- Implement a map visualization
- Add filtering options
- Include charts for data analysis
- Store historical data