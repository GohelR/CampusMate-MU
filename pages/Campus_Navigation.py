# pages/Campus_Navigation.py
import streamlit as st
import pandas as pd
import networkx as nx
import requests
import json
import streamlit.components.v1 as components
from pathlib import Path
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.markdown(
    """
    <style>
    .header { display:flex; gap:16px; align-items:center; }
    .card { background: rgba(255,255,255,0.85); border-radius:12px; padding:12px; box-shadow:0 6px 18px rgba(0,0,0,0.06); }
    </style>
    """, unsafe_allow_html=True
)
st.markdown('<div class="header"><h1>🏫 CampusMate — Indoor+Outdoor Navigation</h1></div>', unsafe_allow_html=True)
st.markdown("This page uses your browser location (allow permission) and computes an indoor + outdoor route (demo) with a 3D MapLibre view and animated walker.")

# ------------------------------
# Data files
# ------------------------------
rooms_path = Path("data/rooms.csv")
indoor_edges_path = Path("data/indoor_edges.csv")

if not rooms_path.exists() or not indoor_edges_path.exists():
    st.error("Missing demo data files in `data/` folder. Add `rooms.csv` and `indoor_edges.csv` (see instructions in repo).")
    st.stop()

rooms_df = pd.read_csv(rooms_path)
edges_df = pd.read_csv(indoor_edges_path)

# Normalize types
rooms_df['room'] = rooms_df['room'].astype(str)
rooms_df['building'] = rooms_df['building'].astype(str)
# ensure is_entrance boolean
if rooms_df['is_entrance'].dtype != bool:
    rooms_df['is_entrance'] = rooms_df['is_entrance'].astype(str).str.lower().isin(['true', '1', 'yes'])

# Build indoor graph
G_indoor = nx.Graph()
for _, r in edges_df.iterrows():
    s = str(r['start'])
    e = str(r['end'])
    dist = float(r.get('distance', 1.0))
    action = str(r.get('action', 'walk'))
    G_indoor.add_edge(s, e, distance=dist, action=action)

def get_latlon(room):
    row = rooms_df[rooms_df['room'] == room]
    if row.empty:
        return None
    r = row.iloc[0]
    return float(r['lat']), float(r['lon']), int(r.get('floor', 0)), r.get('building', '')

def pick_entrance(building):
    rows = rooms_df[(rooms_df['building'] == building) & (rooms_df['is_entrance'] == True)]
    if not rows.empty:
        return rows.iloc[0]['room']
    rows2 = rooms_df[rooms_df['building'] == building]
    if not rows2.empty:
        return rows2.iloc[0]['room']
    return None

def compute_indoor_path(start, end):
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
    url = f"http://router.project-osrm.org/route/v1/walking/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview":"full","geometries":"geojson","steps":"true"}
    try:
        resp = requests.get(url, params=params, timeout=12)
    except Exception:
        return None, []
    if resp.status_code != 200:
        return None, []
    data = resp.json()
    if not data.get('routes'):
        return None, []
    route = data['routes'][0]
    coords = route['geometry']['coordinates']  # [lon,lat] pairs
    instrs = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            man = step.get('maneuver', {})
            name = step.get('name', '')
            dist = step.get('distance', 0)
            # create readable instruction
            t = man.get('type','').replace('_',' ')
            mod = man.get('modifier','')
            instr_text = f"{t} {mod} → {name} ({int(dist)} m)".strip()
            instrs.append(instr_text)
    return coords, instrs

# ------------------------------
# UI controls
# ------------------------------
st.sidebar.header("Navigation Controls")
# Attempt to get browser geolocation
st.sidebar.info("Please allow location access in your browser when prompted.")
geo = get_geolocation()  # uses streamlit-js-eval to call navigator.geolocation
user_lat = user_lon = None
if geo and 'coords' in geo:
    user_lat = geo['coords'].get('latitude')
    user_lon = geo['coords'].get('longitude')
    st.sidebar.success(f"Your location detected: {user_lat:.6f}, {user_lon:.6f}")
else:
    st.sidebar.warning("Location not available yet or permission denied. You can select a start manually below.")

rooms = rooms_df['room'].astype(str).tolist()
# Allow user to choose start: either detected location (use nearest room) or pick a room
start_choice = st.sidebar.radio("Start from:", ("Use my current location", "Choose a room"), index=0)
if start_choice == "Choose a room":
    start_room = st.sidebar.selectbox("From room:", rooms, index=0)
else:
    # we will compute nearest room/entrance once location available
    start_room = None

end_room = st.sidebar.selectbox("To (destination room):", rooms, index=min(1, len(rooms)-1))
st.sidebar.markdown("---")
st.sidebar.markdown("**Map view** settings")
pitch = st.sidebar.slider("Map tilt (3D pitch)", 0, 70, 55)
bearing = st.sidebar.slider("Map bearing (rotation)", -180, 180, 0)
map_style = st.sidebar.selectbox("Map style (tiles)", ["https://demotiles.maplibre.org/style.json",
                                                       "https://tile.openstreetmap.org/{z}/{x}/{y}.png"], index=0)

# ------------------------------
# Determine start room if using GPS: pick nearest entrance or room
# ------------------------------
if start_choice == "Use my current location":
    if user_lat is None or user_lon is None:
        st.warning("Location permission needed to use 'Use my current location'. Please allow location access or choose a room manually.")
        # fallback to allow selecting a room
        start_room = st.selectbox("Fallback - pick start room:", rooms, index=0)
    else:
        # compute nearest room by haversine approx
        def haversine(lat1, lon1, lat2, lon2):
            import math
            R = 6371000.0
            phi1 = math.radians(lat1); phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return 2*R*math.asin(math.sqrt(a))
        nearest = None; nearest_dist = 1e12
        for _, r in rooms_df.iterrows():
            d = haversine(user_lat, user_lon, float(r['lat']), float(r['lon']))
            if d < nearest_dist:
                nearest = r['room']; nearest_dist = d
        # if nearest is far (>200m), prefer nearest entrance
        if nearest_dist > 200:
            # find nearest entrance node
            entries = rooms_df[rooms_df['is_entrance'] == True]
            if not entries.empty:
                nearest_e = None; nd = 1e12
                for _, rr in entries.iterrows():
                    d = haversine(user_lat, user_lon, float(rr['lat']), float(rr['lon']))
                    if d < nd:
                        nearest_e = rr['room']; nd = d
                start_room = nearest_e or nearest
            else:
                start_room = nearest
        else:
            start_room = nearest
        st.sidebar.info(f"Computed start location as: **{start_room}** (≈{int(nearest_dist)} m)")

# ------------------------------
# Compute combined route
# ------------------------------
combined_coords = []  # [ [lon, lat], ... ]
combined_instructions = []

if start_room == end_room:
    st.info("You are already at the destination.")
else:
    # gather lat/lon/floor/building
    s_info = get_latlon(start_room)
    e_info = get_latlon(end_room)
    if s_info is None or e_info is None:
        st.error("Start or end room missing coordinates in rooms.csv")
        st.stop()
    s_lat, s_lon, s_floor, s_building = s_info
    e_lat, e_lon, e_floor, e_building = e_info

    # if same building -> indoor only
    if s_building == e_building:
        indoor_path, indoor_steps = compute_indoor_path(start_room, end_room)
        if indoor_path is None:
            st.error("No indoor path found inside building.")
        else:
            for node in indoor_path:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])
            for stp in indoor_steps:
                act = stp['action']
                if act == 'stairs_up':
                    combined_instructions.append(f"Take stairs up from {stp['from']} to {stp['to']}.")
                elif act == 'stairs_down':
                    combined_instructions.append(f"Take stairs down from {stp['from']} to {stp['to']}.")
                elif act == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({int(stp['distance'])} m).")
    else:
        # cross-building: indoor start -> outdoor (OSRM) -> indoor end
        start_entrance = pick_entrance(s_building)
        end_entrance = pick_entrance(e_building)
        indoor_path1, indoor_steps1 = compute_indoor_path(start_room, start_entrance)
        indoor_path2, indoor_steps2 = compute_indoor_path(end_entrance, end_room)

        if indoor_path1 is None or indoor_path2 is None:
            st.warning("Missing indoor leg. Check indoor_edges.csv and entrances.")
        else:
            # indoor start leg
            for node in indoor_path1:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])
            for stp in indoor_steps1:
                act = stp['action']
                if act == 'stairs_up':
                    combined_instructions.append(f"Take stairs up from {stp['from']} to {stp['to']}.")
                elif act == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({int(stp['distance'])} m).")

            # OSRM outdoor
            s_ent = get_latlon(start_entrance)
            e_ent = get_latlon(end_entrance)
            if s_ent is None or e_ent is None:
                st.error("Entrance coordinates missing for one building.")
            else:
                s_ent_lat, s_ent_lon = s_ent[0], s_ent[1]
                e_ent_lat, e_ent_lon = e_ent[0], e_ent[1]
                osrm_coords, osrm_instrs = osrm_route(s_ent_lon, s_ent_lat, e_ent_lon, e_ent_lat)
                if osrm_coords is None:
                    # fallback line
                    combined_coords.append([s_ent_lon, s_ent_lat])
                    combined_coords.append([e_ent_lon, e_ent_lat])
                    combined_instructions.append(f"Walk outdoors from {start_entrance} to {end_entrance}.")
                else:
                    for c in osrm_coords:
                        combined_coords.append([c[0], c[1]])
                    combined_instructions.extend(osrm_instrs)

            # indoor end leg
            for node in indoor_path2:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])
            for stp in indoor_steps2:
                act = stp['action']
                if act == 'stairs_up':
                    combined_instructions.append(f"Take stairs up from {stp['from']} to {stp['to']}.")
                elif act == 'elevator':
                    combined_instructions.append(f"Use elevator from {stp['from']} to {stp['to']}.")
                else:
                    combined_instructions.append(f"Walk from {stp['from']} to {stp['to']} ({int(stp['distance'])} m).")

# If route empty, stop
if not combined_coords:
    st.info("Could not compute route — check data in `data/`.")
    st.stop()

# Save route and instructions into session so re-renders don't drop it
st.session_state['campus_route_coords'] = combined_coords
st.session_state['campus_route_instr'] = combined_instructions
st.session_state['start_label'] = str(start_room)
st.session_state['end_label'] = str(end_room)

# ------------------------------
# MapLibre frontend (3D, animated marker)
# ------------------------------
route_json = json.dumps(st.session_state['campus_route_coords'])
instr_json = json.dumps(st.session_state['campus_route_instr'])
start_label = st.session_state['start_label'].replace("'", "\\'")
end_label = st.session_state['end_label'].replace("'", "\\'")

map_html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Campus Navigation 3D</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<style>
  body {{ margin:0; padding:0; font-family: Arial, sans-serif; }}
  #map {{ position:relative; width:100%; height:70vh; }}
  .info {{ position:absolute; right:12px; top:12px; z-index:2; background:rgba(255,255,255,0.9); padding:8px 12px; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,0.12); }}
</style>
</head>
<body>
<div id="map"></div>
<div class="info"><b>Route:</b> {start_label} → {end_label}</div>
<script>
  const route = {route_json};
  const instrs = {instr_json};
  const mid = route[Math.floor(route.length/2)];
  const map = new maplibregl.Map({{
    container: 'map',
    style: 'https://demotiles.maplibre.org/style.json',
    center: mid,
    zoom: 17,
    pitch: {pitch},
    bearing: {bearing}
  }});
  map.addControl(new maplibregl.NavigationControl());

  map.on('load', () => {{
    // add route source + layer
    const routeGeo = {{
      "type":"FeatureCollection",
      "features":[ {{
        "type":"Feature",
        "properties":{{}},
        "geometry":{{ "type":"LineString", "coordinates": route }}
      }} ]
    }};
    map.addSource('route', {{ type:'geojson', data: routeGeo }});
    map.addLayer({{
      id:'route-line',
      type:'line',
      source:'route',
      layout:{{ 'line-join':'round','line-cap':'round' }},
      paint:{{ 'line-color':'#007bff','line-width':6,'line-opacity':0.9 }}
    }});

    // start/end markers
    new maplibregl.Marker({{ color:'green' }}).setLngLat(route[0]).setPopup(new maplibregl.Popup().setText('Start: {start_label}')).addTo(map);
    new maplibregl.Marker({{ color:'red' }}).setLngLat(route[route.length-1]).setPopup(new maplibregl.Popup().setText('End: {end_label}')).addTo(map);

    // fit bounds
    const bounds = route.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(route[0], route[0]));
    map.fitBounds(bounds, {{ padding: 60 }});

    // animated dot
    const dot = document.createElement('div');
    dot.style.width = '18px'; dot.style.height = '18px'; dot.style.borderRadius = '50%';
    dot.style.background = 'rgba(255,140,0,1)'; dot.style.boxShadow = '0 0 12px rgba(255,140,0,0.9)';
    const marker = new maplibregl.Marker(dot).setLngLat(route[0]).addTo(map);

    // animate along simple index steps (for demo)
    let idx = 0;
    const speedMs = 80;
    function animateStep() {{
      if (idx < route.length - 1) {{
        idx++;
        marker.setLngLat(route[idx]);
        // smooth camera follow (optional)
        // map.easeTo({{ center: route[idx], duration: speedMs }});
        setTimeout(animateStep, speedMs);
      }}
    }}
    setTimeout(animateStep, 600);
  }});
</script>
</body>
</html>
"""

components.html(map_html, height=750, scrolling=False)

# ------------------------------
# Directions / Instructions panel
# ------------------------------
st.markdown("## 📝 Turn-by-turn Directions")
for i, ins in enumerate(st.session_state['campus_route_instr'], start=1):
    st.write(f"{i}. {ins}")
