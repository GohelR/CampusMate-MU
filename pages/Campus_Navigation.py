import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.title("🗺️ Campus Navigation (Mapbox-Style with Routing)")

# Dummy campus coordinates (replace with real ones later)
campus_coords = {
    "MB107": [70.781, 22.301],
    "MB201": [70.782, 22.303],
    "MA202": [70.784, 22.305],
    "MA407": [70.786, 22.306],
}

# UI selection
start = st.selectbox("📍 From (Your Room):", list(campus_coords.keys()), index=0)
end = st.selectbox("🎯 To (Destination Room):", list(campus_coords.keys()), index=3)

# HTML + JS for MapLibre + Routing
maplibre_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Campus Navigation</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://unpkg.com/leaflet/dist/leaflet.css" rel="stylesheet" />
<link href="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.css" rel="stylesheet" />
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.js"></script>
<style>
  body {{ margin:0; padding:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; height:100%; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
    // Create map
    var map = L.map('map').setView([{campus_coords[start][1]}, {campus_coords[start][0]}], 17);

    // Load MapLibre tiles (OpenStreetMap free style)
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 20,
        attribution: '© OpenStreetMap contributors'
    }}).addTo(map);

    // Add routing
    L.Routing.control({{
        waypoints: [
            L.latLng({campus_coords[start][1]}, {campus_coords[start][0]}),
            L.latLng({campus_coords[end][1]}, {campus_coords[end][0]})
        ],
        routeWhileDragging: false,
        lineOptions: {{ styles: [{{color: 'blue', weight: 5}}] }},
        createMarker: function(i, wp, nWps) {{
            return L.marker(wp.latLng, {{
                icon: L.icon({{
                    iconUrl: i === 0 ? 'https://cdn-icons-png.flaticon.com/512/684/684908.png'
                                     : 'https://cdn-icons-png.flaticon.com/512/149/149059.png',
                    iconSize: [30, 30]
                }})
            }});
        }}
    }}).addTo(map);
</script>
</body>
</html>
"""

# Show inside Streamlit
components.html(maplibre_html, height=600)
