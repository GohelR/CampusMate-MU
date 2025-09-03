import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Campus Navigation 3D", page_icon="🏢", layout="wide")

st.title("🏢 Campus Navigation in 3D (WOW Factor 🚀)")

# Dummy coordinates (replace with real lat/lon later)
campus_coords = {
    "MB107": [70.781, 22.301],
    "MA407": [70.786, 22.306],
}

start = st.selectbox("📍 From (Your Room):", list(campus_coords.keys()), index=0)
end = st.selectbox("🎯 To (Destination Room):", list(campus_coords.keys()), index=1)

maplibre_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Campus 3D Navigation</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<style>
  body {{ margin:0; padding:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; height:100%; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
    var map = new maplibregl.Map({{
        container: 'map',
        style: 'https://demotiles.maplibre.org/style.json',
        center: [{campus_coords[start][0]}, {campus_coords[start][1]}],
        zoom: 17,
        pitch: 60,   // tilt for 3D effect
        bearing: -20 // camera angle
    }});

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl());

    // 3D buildings layer
    map.on('load', function() {{
        map.addLayer({{
            'id': '3d-buildings',
            'source': 'openmaptiles',
            'source-layer': 'building',
            'type': 'fill-extrusion',
            'paint': {{
                'fill-extrusion-color': '#aaa',
                'fill-extrusion-height': ['get', 'render_height'],
                'fill-extrusion-base': ['get', 'render_min_height'],
                'fill-extrusion-opacity': 0.8
            }}
        }});
    }});

    // Markers for Start and End
    new maplibregl.Marker({{color:"green"}})
        .setLngLat([{campus_coords[start][0]}, {campus_coords[start][1]}])
        .setPopup(new maplibregl.Popup().setText("Start: {start}"))
        .addTo(map);

    new maplibregl.Marker({{color:"red"}})
        .setLngLat([{campus_coords[end][0]}, {campus_coords[end][1]}])
        .setPopup(new maplibregl.Popup().setText("End: {end}"))
        .addTo(map);

    // 🚀 Draw straight path line (later replace with routing engine)
    map.on('load', function() {{
        map.addSource('route', {{
            'type': 'geojson',
            'data': {{
                'type': 'Feature',
                'geometry': {{
                    'type': 'LineString',
                    'coordinates': [
                        [{campus_coords[start][0]}, {campus_coords[start][1]}],
                        [{campus_coords[end][0]}, {campus_coords[end][1]}]
                    ]
                }}
            }}
        }});

        map.addLayer({{
            'id': 'route-line',
            'type': 'line',
            'source': 'route',
            'paint': {{
                'line-color': '#007bff',
                'line-width': 5
            }}
        }});
    }});
</script>
</body>
</html>
"""

components.html(maplibre_html, height=600)
