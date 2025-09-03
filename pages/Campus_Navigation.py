import streamlit as st
import pandas as pd
import networkx as nx

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")
st.title("🗺️ Campus Navigation Guide (3D WOW)")

# -------------------------
# Load campus graph
# -------------------------
CSV_FILE = "data/campus_graph.csv"
try:
    edges = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    st.error(f"❌ Could not find {CSV_FILE}. Please upload it.")
    st.stop()

# Build graph
G = nx.Graph()
for _, row in edges.iterrows():
    G.add_edge(row["start"], row["end"], weight=row["distance"])

# Room coordinates (replace with your real data)
coords = {
    "MB101": [70.781, 22.301],
    "MB201": [70.783, 22.303],
    "MA202": [70.785, 22.305],
    "MA407": [70.786, 22.306],
}

rooms = list(coords.keys())

# -------------------------
# User input
# -------------------------
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]

# -------------------------
# Compute route
# -------------------------
route_coords = []
if st.button("🚀 Get 3D Directions"):
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")
        st.success(" ➝ ".join(path))

        # convert to list of lon/lat
        route_coords = [coords[node] for node in path]

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")

# -------------------------
# Mapbox GL JS Embed
# -------------------------
if route_coords:
    route_js = str(route_coords).replace("'", "")

    html_code = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>Campus 3D Navigation</title>
      <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
      <script src="https://api.mapbox.com/mapbox-gl-js/v2.18.0/mapbox-gl.js"></script>
      <link href="https://api.mapbox.com/mapbox-gl-js/v2.18.0/mapbox-gl.css" rel="stylesheet" />
      <style>
        body {{ margin:0; padding:0; }}
        #map {{ position:absolute; top:0; bottom:0; width:100%; height:100%; }}
        .controls {{ position:absolute; z-index:2; left:12px; top:12px;
          background:white; padding:8px; border-radius:8px; }}
      </style>
    </head>
    <body>
    <div id="map"></div>
    <div class="controls">
      <button onclick="startAnim()">▶ Start Navigation</button>
    </div>
    <script>
      mapboxgl.accessToken = "{MAPBOX_TOKEN}";
      const route = {route_js};

      const map = new mapboxgl.Map({{
        container: 'map',
        style: 'mapbox://styles/mapbox/streets-v12',
        center: route[0],
        zoom: 18,
        pitch: 60,
        bearing: -20,
        antialias: true
      }});

      map.on('load', () => {{
        // 3D buildings
        const layers = map.getStyle().layers;
        const labelLayerId = layers.find(
          layer => layer.type === 'symbol' && layer.layout['text-field']
        ).id;

        map.addLayer({{
          'id': '3d-buildings',
          'source': 'composite',
          'source-layer': 'building',
          'filter': ['==', 'extrude', 'true'],
          'type': 'fill-extrusion',
          'minzoom': 15,
          'paint': {{
            'fill-extrusion-color': '#aaa',
            'fill-extrusion-height': ['get', 'height'],
            'fill-extrusion-base': ['get', 'min_height'],
            'fill-extrusion-opacity': 0.85
          }}
        }}, labelLayerId);

        // Route line
        map.addSource('route', {{
          'type': 'geojson',
          'data': {{
            'type': 'Feature',
            'geometry': {{
              'type': 'LineString',
              'coordinates': route
            }}
          }}
        }});

        map.addLayer({{
          'id': 'route-line',
          'type': 'line',
          'source': 'route',
          'paint': {{ 'line-color': '#0074ff', 'line-width': 6 }}
        }});

        // Marker
        const el = document.createElement('div');
        el.style.width = '36px';
        el.style.height = '36px';
        el.style.backgroundImage = 'url(https://i.imgur.com/MK4NUzI.png)';
        el.style.backgroundSize = 'contain';
        const marker = new mapboxgl.Marker(el).setLngLat(route[0]).addTo(map);

        let animId;
        function animate(i) {{
          if (i >= route.length) return;
          marker.setLngLat(route[i]);
          map.easeTo({{ center: route[i], zoom: 18, pitch: 60, bearing: -20 }});
          animId = setTimeout(() => animate(i+1), 1000);
        }}

        window.startAnim = () => {{
          animate(0);
        }}
      }});
    </script>
    </body>
    </html>
    """

    st.components.v1.html(html_code, height=700, scrolling=False)
