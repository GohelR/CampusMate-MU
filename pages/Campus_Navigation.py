import streamlit as st
import pandas as pd
import networkx as nx
import requests
import json
from pathlib import Path
import streamlit.components.v1 as components

st.set_page_config(page_title="Campus Navigation 3D (Indoor+Outdoor)", page_icon="🗺️", layout="wide")
st.title("🏫 CampusMate — 3D Indoor + Outdoor Navigation")
st.markdown("Select a start room and destination. The app will compute indoor legs (floors/stairs) and outdoor walking route, then show a combined route on a **3D MapLibre** map with step-by-step directions and animated marker.")

# ---------- LOAD DATA ----------
rooms_path = Path("data/rooms.csv")
indoor_edges_path = Path("data/indoor_edges.csv")

if not rooms_path.exists() or not indoor_edges_path.exists():
    st.warning("Please add `data/rooms.csv` and `data/indoor_edges.csv` to your repo. See example in the project README.")
    st.stop()

rooms_df = pd.read_csv(rooms_path)
edges_df = pd.read_csv(indoor_edges_path)

# Normalize
rooms_df['room'] = rooms_df['room'].astype(str)
rooms_df.set_index('room', inplace=False)

# ---------- BUILD INDOOR GRAPH ----------
G_indoor = nx.Graph()
for _, r in edges_df.iterrows():
    s = str(r['start'])
    e = str(r['end'])
    dist = float(r.get('distance', 1.0))
    action = str(r.get('action', 'walk'))
    G_indoor.add_edge(s, e, distance=dist, action=action)

# Helper: get coordinates (lat, lon)
def get_latlon(node):
    row = rooms_df[rooms_df['room'] == node]
    if row.empty:
        return None
    r = row.iloc[0]
    return float(r['lat']), float(r['lon']), int(r.get('floor', 0)), r.get('building', '')

# Helper: pick an entrance node for a building
def pick_entrance(building):
    rows = rooms_df[(rooms_df['building'] == building) & (rooms_df['is_entrance'] == True)]
    if not rows.empty:
        return rows.iloc[0]['room']
    # fallback: pick any node in building (first)
    rows2 = rooms_df[rooms_df['building'] == building]
    if not rows2.empty:
        return rows2.iloc[0]['room']
    return None

# ---------- UI: pick start & end ----------
rooms = rooms_df['room'].astype(str).tolist()
start_room = st.selectbox("📍 From (room):", rooms, index=0)
end_room = st.selectbox("🎯 To (room):", rooms, index=min(1, len(rooms)-1))

# ---------- Compute combined route ----------
def compute_indoor_path(start, end):
    """Return list of nodes and step texts for indoor graph path."""
    try:
        path = nx.shortest_path(G_indoor, source=start, target=end, weight='distance')
    except Exception:
        return None, []
    steps = []
    for i in range(len(path)-1):
        a, b = path[i], path[i+1]
        data = G_indoor.get_edge_data(a, b)
        action = data.get('action', 'walk')
        steps.append({'from': a, 'to': b, 'action': action, 'distance': data.get('distance', 0)})
    return path, steps

def osrm_route(lon1, lat1, lon2, lat2):
    """Call public OSRM demo server to get a walking route and steps. Returns list of [lon,lat] coords and step instructions."""
    url = f"http://router.project-osrm.org/route/v1/walking/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        return None, []
    data = resp.json()
    if not data.get('routes'):
        return None, []
    route = data['routes'][0]
    coords = route['geometry']['coordinates']  # list of [lon,lat]
    # collect human-friendly instructions from steps
    instructions = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            m = step.get('maneuver', {})
            # Simple readable instruction
            name = step.get('name', '')
            dist = step.get('distance', 0)
            instr = f"{m.get('type', '')} {m.get('modifier','')} -> {name} ({dist:.0f} m)".strip()
            instructions.append(instr)
    return coords, instructions

# Compose route:
combined_coords = []   # list of [lon, lat]
combined_instructions = []  # list of human instructions

# edge cases
if start_room == end_room:
    st.info("You're already at the destination.")
else:
    # get room info
    s_latlon = get_latlon(start_room)
    e_latlon = get_latlon(end_room)
    if s_latlon is None or e_latlon is None:
        st.error("Start or end room not found in rooms.csv")
        st.stop()

    s_lat, s_lon, s_floor, s_building = s_latlon
    e_lat, e_lon, e_floor, e_building = e_latlon

    # if same building -> indoor-only route
    if s_building == e_building:
        indoor_path, indoor_steps = compute_indoor_path(start_room, end_room)
        if indoor_path is None:
            st.error("No indoor path found inside the building.")
        else:
            # map coords: use rooms_df lat/lon for each node; convert to [lon,lat]
            for node in indoor_path:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])
            # build instructions
            for stp in indoor_steps:
                if stp['action'] == 'stairs_up':
                    combined_instructions.append(f"Take stairs from {stp['from']} to {stp['to']} (go up).")
                elif stp['action'] == 'stairs_down':
                    combined_instructions.append(f"Take stairs from {stp['from']} to {stp['to']} (go down).")
                elif stp['action'] == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({stp['distance']} m).")
    else:
        # different buildings -> indoor start -> OSRM outdoor -> indoor end
        start_entrance = pick_entrance(s_building)
        end_entrance = pick_entrance(e_building)
        # indoor: start_room -> start_entrance
        indoor_path1, indoor_steps1 = compute_indoor_path(start_room, start_entrance)
        # indoor: end_entrance -> end_room
        indoor_path2, indoor_steps2 = compute_indoor_path(end_entrance, end_room)
        if indoor_path1 is None or indoor_path2 is None:
            st.warning("Indoor leg path not found for one of the buildings. Check indoor_edges.csv entrances.")
        else:
            # add indoor start leg coords
            for node in indoor_path1:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])  # lon, lat
            # instructions for indoor start
            for stp in indoor_steps1:
                if stp['action'] == 'stairs_up':
                    combined_instructions.append(f"Take stairs from {stp['from']} to {stp['to']} (go up).")
                elif stp['action'] == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({stp['distance']} m).")

            # OSRM outdoor: from start_entrance coords to end_entrance coords
            s_ent_latlon = get_latlon(start_entrance)
            e_ent_latlon = get_latlon(end_entrance)
            if s_ent_latlon is None or e_ent_latlon is None:
                st.error("Entrance coordinates missing.")
            else:
                s_ent_lat, s_ent_lon = s_ent_latlon[0], s_ent_latlon[1]
                e_ent_lat, e_ent_lon = e_ent_latlon[0], e_ent_latlon[1]
                osrm_coords, osrm_instr = osrm_route(s_ent_lon, s_ent_lat, e_ent_lon, e_ent_lat)
                if osrm_coords is None:
                    st.warning("OSRM routing failed — will fallback to straight line between entrances.")
                    # fallback line between entrances
                    combined_coords.append([s_ent_lon, s_ent_lat])
                    combined_coords.append([e_ent_lon, e_ent_lat])
                    combined_instructions.append(f"Walk outdoors from {start_entrance} to {end_entrance} (straight).")
                else:
                    # append osrm coords to combined_coords (avoid duplicate point)
                    # ensure last indoor coord equals first osrm coord? not necessarily.
                    for c in osrm_coords:
                        combined_coords.append([c[0], c[1]])  # lon, lat
                    # add instructions from OSRM
                    combined_instructions.extend(osrm_instr)

            # add indoor end leg coords (from entrance to room)
            for node in indoor_path2:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])
            # add indoor end instructions
            for stp in indoor_steps2:
                if stp['action'] == 'stairs_up':
                    combined_instructions.append(f"Take stairs from {stp['from']} to {stp['to']} (go up).")
                elif stp['action'] == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({stp['distance']} m).")

# ---------- PREPARE MAP CONTENT ----------
# combined_coords is list of [lon, lat]
if not combined_coords:
    st.info("No route could be computed yet. Please ensure rooms and indoor edges are defined.")
    st.stop()

# create a JSON payload for the frontend (MapLibre)
route_json = json.dumps(combined_coords)
instr_json = json.dumps(combined_instructions)
start_label = start_room.replace("'", "\\'")
end_label = end_room.replace("'", "\\'")

# ---------- EMBED MAPLIBRE + ROUTE + ANIMATION ----------
# MapLibre HTML/JS (we pass route coords and instructions)
map_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Campus Navigation 3D</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<style>
  body {{ margin:0; padding:0; }}
  #map {{ position:relative; width:100%; height:70vh; }}
  .legend {{ padding:8px; background:rgba(255,255,255,0.9); border-radius:8px; position:absolute; right:10px; top:10px; z-index:2; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="legend"><b>Route:</b> {start_label} ➝ {end_label}</div>
<script>
  const route = {route_json}; // array of [lon, lat]
  const instructions = {instr_json};

  // center at midpoint
  const mid = route[Math.floor(route.length/2)];
  const map = new maplibregl.Map({{
    container: 'map',
    style: 'https://demotiles.maplibre.org/style.json',
    center: mid,
    zoom: 17,
    pitch: 55,
    bearing: -20
  }});
  map.addControl(new maplibregl.NavigationControl());

  map.on('load', () => {{
    // Add route as geojson line
    const routeGeo = {{
      "type": "FeatureCollection",
      "features": [
        {{
          "type": "Feature",
          "properties": {{}},
          "geometry": {{
            "type": "LineString",
            "coordinates": route
          }}
        }}
      ]
    }};
    map.addSource('route', {{ type: 'geojson', data: routeGeo }});
    map.addLayer({{
      'id': 'route-line',
      'type': 'line',
      'source': 'route',
      'layout': {{
        'line-join': 'round',
        'line-cap': 'round'
      }},
      'paint': {{
        'line-color': '#007bff',
        'line-width': 6,
        'line-opacity': 0.85
      }}
    }});

    // start / end markers
    new maplibregl.Marker({{color:"green"}}).setLngLat(route[0]).setPopup(new maplibregl.Popup().setText('Start: {start_label}')).addTo(map);
    new maplibregl.Marker({{color:"red"}}).setLngLat(route[route.length-1]).setPopup(new maplibregl.Popup().setText('End: {end_label}')).addTo(map);

    // Fit bounds
    const bounds = route.reduce(function(b, coord) {{
      return b.extend(coord);
    }}, new maplibregl.LngLatBounds(route[0], route[0]));
    map.fitBounds(bounds, {{padding:60}});

    // Animated moving dot
    const el = document.createElement('div');
    el.style.width = '22px';
    el.style.height = '22px';
    el.style.borderRadius = '50%';
    el.style.background = 'rgba(255,80,0,0.95)';
    el.style.boxShadow = '0 0 10px rgba(255,80,0,0.7)';
    const marker = new maplibregl.Marker(el).setLngLat(route[0]).addTo(map);

    // animate along route
    let index = 0;
    const speedMs = 80; // lower => faster (ms per step)
    function step() {{
      index++;
      if (index >= route.length) {{
        index = route.length - 1; // stop at end
        return;
      }}
      marker.setLngLat(route[index]);
      // optionally rotate camera to follow
      // map.easeTo({{center: route[index], duration: speedMs}});
      setTimeout(step, speedMs);
    }}
    // start animation after small delay
    setTimeout(step, 600);

  }});
</script>
</body>
</html>
"""

# render in Streamlit
components.html(map_html, height=700, scrolling=False)

# ---------- SHOW INSTRUCTIONS BELOW MAP ----------
st.markdown("## 📝 Turn-by-turn Directions")
for i, instr in enumerate(combined_instructions, start=1):
    st.write(f"{i}. {instr}")
