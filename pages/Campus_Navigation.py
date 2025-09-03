# pages/Campus_Navigation.py
import streamlit as st
import pandas as pd
import networkx as nx
import requests
import json
import math
from pathlib import Path
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation

# ==============================
# Page setup
# ==============================
st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.markdown(
    """
    <style>
      .header { display:flex; gap:16px; align-items:center; }
      .card { background: rgba(255,255,255,0.85); border-radius:12px; padding:12px; box-shadow:0 6px 18px rgba(0,0,0,0.06); }
      .small { color:#666; font-size:12px; }
      .pill { background:#eef3ff; color:#2f5cff; padding:2px 8px; border-radius:999px; font-size:12px; margin-left:6px; }
      .kpi { display:flex; gap:16px; margin: 8px 0 16px; }
      .kpi > div { background:#fff; border:1px solid #eee; border-radius:12px; padding:10px 12px; box-shadow:0 2px 10px rgba(0,0,0,.04); }
      .dir-table thead th { position: sticky; top:0; background:#fafafa; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="header"><h1>🏫 CampusMate — Indoor + Outdoor Navigation</h1></div>', unsafe_allow_html=True)
st.markdown("Allow your browser’s location when prompted. We’ll compute a combined indoor/outdoor route with a 3D MapLibre view and an animated walker.")

# ==============================
# Data
# ==============================
rooms_path = Path("data/rooms.csv")
indoor_edges_path = Path("data/indoor_edges.csv")

if not rooms_path.exists() or not indoor_edges_path.exists():
    st.error("Missing demo data in `data/`. Need `rooms.csv` and `indoor_edges.csv`.")
    st.stop()

rooms_df = pd.read_csv(rooms_path)
edges_df = pd.read_csv(indoor_edges_path)

# Normalize types
rooms_df["room"] = rooms_df["room"].astype(str)
rooms_df["building"] = rooms_df["building"].astype(str)
if rooms_df["is_entrance"].dtype != bool:
    rooms_df["is_entrance"] = (
        rooms_df["is_entrance"].astype(str).str.lower().isin(["true", "1", "yes"])
    )

# Optional columns in edges for contextual guidance
for opt_col in ["left_desc", "right_desc"]:
    if opt_col not in edges_df.columns:
        edges_df[opt_col] = None

# Build indoor graph
G_indoor = nx.Graph()
for _, r in edges_df.iterrows():
    s = str(r["start"])
    e = str(r["end"])
    dist = float(r.get("distance", 1.0))
    action = str(r.get("action", "walk"))
    # store left/right context on the edge if present
    left_desc = r.get("left_desc", None)
    right_desc = r.get("right_desc", None)
    G_indoor.add_edge(
        s, e, distance=dist, action=action, left_desc=left_desc, right_desc=right_desc
    )

# ==============================
# Helpers
# ==============================
def get_latlon(room_id: str):
    row = rooms_df[rooms_df["room"] == str(room_id)]
    if row.empty:
        return None
    r = row.iloc[0]
    return float(r["lat"]), float(r["lon"]), int(r.get("floor", 0)), r.get("building", "")

def get_room_label(room_id: str) -> str:
    row = rooms_df[rooms_df["room"] == str(room_id)]
    if row.empty:
        return str(room_id)
    r = row.iloc[0]
    if "name" in rooms_df.columns and pd.notna(r.get("name", None)) and str(r.get("name", "")).strip():
        return f"{room_id} ({r['name']})"
    return str(room_id)

def pick_entrance(building: str):
    rows = rooms_df[(rooms_df["building"] == building) & (rooms_df["is_entrance"] == True)]
    if not rows.empty:
        return rows.iloc[0]["room"]
    rows2 = rooms_df[rooms_df["building"] == building]
    if not rows2.empty:
        return rows2.iloc[0]["room"]
    return None

def compute_indoor_path(start: str, end: str):
    try:
        path = nx.shortest_path(G_indoor, source=str(start), target=str(end), weight="distance")
    except Exception:
        return None, []
    steps = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        data = G_indoor.get_edge_data(a, b) or {}
        steps.append(
            {
                "from": a,
                "to": b,
                "action": data.get("action", "walk"),
                "distance": float(data.get("distance", 0)),
                "left_desc": data.get("left_desc", None),
                "right_desc": data.get("right_desc", None),
            }
        )
    return path, steps

def osrm_route(lon1, lat1, lon2, lat2):
    url = f"http://router.project-osrm.org/route/v1/walking/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}
    try:
        resp = requests.get(url, params=params, timeout=12)
    except Exception:
        return None, []
    if resp.status_code != 200:
        return None, []
    data = resp.json()
    if not data.get("routes"):
        return None, []
    route = data["routes"][0]
    coords = route["geometry"]["coordinates"]  # [lon,lat]
    instrs = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            man = step.get("maneuver", {})
            name = step.get("name", "")
            dist = step.get("distance", 0)
            t = man.get("type", "").replace("_", " ")
            mod = man.get("modifier", "")
            instr_text = f"{t} {mod} → {name} ({int(dist)} m)".strip()
            instrs.append(instr_text)
    return coords, instrs

def turn_direction(a_row, b_row, c_row) -> str:
    """Return 'Go straight' / 'Turn left' / 'Turn right' using bearing change."""
    ax, ay = float(a_row["lon"]), float(a_row["lat"])
    bx, by = float(b_row["lon"]), float(b_row["lat"])
    cx, cy = float(c_row["lon"]), float(c_row["lat"])
    v1 = (bx - ax, by - ay)
    v2 = (cx - bx, cy - by)
    ang1 = math.atan2(v1[1], v1[0])
    ang2 = math.atan2(v2[1], v2[0])
    diff = math.degrees(ang2 - ang1)
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    if abs(diff) < 25:
        return "Go straight"
    elif diff > 0:
        return "Turn left"
    else:
        return "Turn right"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

# ==============================
# Sidebar (controls)
# ==============================
st.sidebar.header("Navigation Controls")
st.sidebar.info("Please allow location access in your browser when prompted.")
geo = get_geolocation()
user_lat = user_lon = None
if geo and "coords" in geo:
    user_lat = geo["coords"].get("latitude")
    user_lon = geo["coords"].get("longitude")
    st.sidebar.success(f"Your location: {user_lat:.6f}, {user_lon:.6f}")
else:
    st.sidebar.warning("Location not available yet or permission denied. You can select a start manually below.")

rooms = rooms_df["room"].astype(str).tolist()
start_choice = st.sidebar.radio("Start from:", ("Use my current location", "Choose a room"), index=0)
if start_choice == "Choose a room":
    start_room = st.sidebar.selectbox("From room:", rooms, index=0)
else:
    start_room = None

end_room = st.sidebar.selectbox("To (destination room):", rooms, index=min(1, len(rooms) - 1))
st.sidebar.markdown("---")
st.sidebar.markdown("**Map view** settings")

pitch = st.sidebar.slider("Map tilt (3D pitch)", 0, 70, 55)
bearing = st.sidebar.slider("Map bearing (rotation)", -180, 180, 0)
map_style = st.sidebar.selectbox(
    "Map style (tiles)",
    [
        "https://demotiles.maplibre.org/style.json",
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    ],
    index=0,
)

# ==============================
# Determine start room for GPS
# ==============================
if start_choice == "Use my current location":
    if user_lat is None or user_lon is None:
        st.warning("Location permission needed to use current location. Pick a room below.")
        start_room = st.selectbox("Fallback — pick start room:", rooms, index=0)
    else:
        nearest = None
        nearest_dist = 1e12
        for _, r in rooms_df.iterrows():
            d = haversine(user_lat, user_lon, float(r["lat"]), float(r["lon"]))
            if d < nearest_dist:
                nearest = r["room"]
                nearest_dist = d
        # Prefer nearest entrance if quite far away (>200 m)
        if nearest_dist > 200:
            entries = rooms_df[rooms_df["is_entrance"] == True]
            if not entries.empty:
                nearest_e = None
                nd = 1e12
                for _, rr in entries.iterrows():
                    d = haversine(user_lat, user_lon, float(rr["lat"]), float(rr["lon"]))
                    if d < nd:
                        nearest_e = rr["room"]
                        nd = d
                start_room = nearest_e or nearest
            else:
                start_room = nearest
        else:
            start_room = nearest
        st.sidebar.info(f"Computed start: **{get_room_label(start_room)}** (≈{int(nearest_dist)} m)")

# ==============================
# Route computation
# ==============================
combined_coords = []      # [[lon, lat], ...]
combined_instructions = []  # list of strings
indoor_debug_rows = []    # For the directions table with columns

if start_room == end_room:
    st.info("You are already at the destination.")
else:
    s_info = get_latlon(start_room)
    e_info = get_latlon(end_room)
    if s_info is None or e_info is None:
        st.error("Start or end room missing coordinates in rooms.csv")
        st.stop()
    s_lat, s_lon, s_floor, s_building = s_info
    e_lat, e_lon, e_floor, e_building = e_info

    if s_building == e_building:
        # Indoor only
        indoor_path, indoor_steps = compute_indoor_path(start_room, end_room)
        if indoor_path is None:
            st.error("No indoor path found inside building.")
        else:
            for node in indoor_path:
                r = get_latlon(node)
                if r:
                    combined_coords.append([r[1], r[0]])

            for i, stp in enumerate(indoor_steps):
                frm, to = stp["from"], stp["to"]
                frm_label, to_label = get_room_label(frm), get_room_label(to)
                act = stp["action"]
                left_desc = stp.get("left_desc") or ""
                right_desc = stp.get("right_desc") or ""

                # Turn detection if we have 3 points
                turn_txt = ""
                if act not in ["stairs_up", "stairs_down", "elevator"] and i < len(indoor_path) - 2:
                    a = rooms_df[rooms_df["room"] == indoor_path[i]].iloc[0]
                    b = rooms_df[rooms_df["room"] == indoor_path[i + 1]].iloc[0]
                    c = rooms_df[rooms_df["room"] == indoor_path[i + 2]].iloc[0]
                    turn_txt = turn_direction(a, b, c)

                if act == "stairs_up":
                    text = f"Take stairs up from {frm_label} to {to_label}."
                elif act == "stairs_down":
                    text = f"Take stairs down from {frm_label} to {to_label}."
                elif act == "elevator":
                    text = f"Use elevator from {frm_label} to {to_label}."
                else:
                    lead = f"{turn_txt} towards {to_label}" if turn_txt else f"Walk from {frm_label} to {to_label}"
                    text = f"{lead} ({int(stp['distance'])} m)."

                # Append left/right context if available
                context_bits = []
                if right_desc and str(right_desc).strip():
                    context_bits.append(f"Right: {right_desc}")
                if left_desc and str(left_desc).strip():
                    context_bits.append(f"Left: {left_desc}")
                if context_bits:
                    text += "  " + " | ".join(context_bits)

                combined_instructions.append(text)

                indoor_debug_rows.append({
                    "From": frm_label,
                    "To": to_label,
                    "Action": act.replace("_", " ").title(),
                    "Turn": turn_txt or "-",
                    "Distance (m)": int(stp["distance"]),
                    "Right": right_desc or "-",
                    "Left": left_desc or "-",
                })

    else:
        # Cross-building: indoor → outdoor (OSRM) → indoor
        start_entrance = pick_entrance(s_building)
        end_entrance = pick_entrance(e_building)
        indoor_path1, indoor_steps1 = compute_indoor_path(start_room, start_entrance)
        indoor_path2, indoor_steps2 = compute_indoor_path(end_entrance, end_room)

        if indoor_path1 is None or indoor_path2 is None:
            st.warning("Missing indoor leg. Check indoor_edges.csv and entrances.")
        else:
            # Indoor start leg
            for i, stp in enumerate(indoor_steps1):
                frm, to = stp["from"], stp["to"]
                frm_label, to_label = get_room_label(frm), get_room_label(to)
                act = stp["action"]
                left_desc = stp.get("left_desc") or ""
                right_desc = stp.get("right_desc") or ""
                turn_txt = ""
                if act not in ["stairs_up", "stairs_down", "elevator"] and i < len(indoor_path1) - 1:
                    # i < len(path)-2 for next-next turn; safe compute when possible
                    if i < len(indoor_path1) - 2:
                        a = rooms_df[rooms_df["room"] == indoor_path1[i]].iloc[0]
                        b = rooms_df[rooms_df["room"] == indoor_path1[i + 1]].iloc[0]
                        c = rooms_df[rooms_df["room"] == indoor_path1[i + 2]].iloc[0]
                        turn_txt = turn_direction(a, b, c)
                if act in ["stairs_up", "stairs_down", "elevator"]:
                    text = f"{act.replace('_', ' ').title()} from {frm_label} to {to_label}."
                else:
                    lead = f"{turn_txt} towards {to_label}" if turn_txt else f"Walk from {frm_label} to {to_label}"
                    text = f"{lead} ({int(stp['distance'])} m)."
                context_bits = []
                if right_desc and str(right_desc).strip():
                    context_bits.append(f"Right: {right_desc}")
                if left_desc and str(left_desc).strip():
                    context_bits.append(f"Left: {left_desc}")
                if context_bits:
                    text += "  " + " | ".join(context_bits)
                combined_instructions.append(text)
                indoor_debug_rows.append({
                    "From": frm_label, "To": to_label, "Action": act.replace("_"," ").title(),
                    "Turn": turn_txt or "-", "Distance (m)": int(stp["distance"]),
                    "Right": right_desc or "-", "Left": left_desc or "-"
                })

            # Outdoor OSRM
            s_ent = get_latlon(start_entrance)
            e_ent = get_latlon(end_entrance)
            if s_ent is None or e_ent is None:
                st.error("Entrance coordinates missing for one building.")
            else:
                s_ent_lat, s_ent_lon = s_ent[0], s_ent[1]
                e_ent_lat, e_ent_lon = e_ent[0], e_ent[1]
                osrm_coords, osrm_instrs = osrm_route(s_ent_lon, s_ent_lat, e_ent_lon, e_ent_lat)
                if osrm_coords is None:
                    combined_coords.append([s_ent_lon, s_ent_lat])
                    combined_coords.append([e_ent_lon, e_ent_lat])
                    combined_instructions.append(
                        f"Walk outdoors from {get_room_label(start_entrance)} to {get_room_label(end_entrance)}."
                    )
                else:
                    combined_coords.extend([[c[0], c[1]] for c in osrm_coords])
                    combined_instructions.extend(osrm_instrs)

            # Indoor end leg
            for i, stp in enumerate(indoor_steps2):
                frm, to = stp["from"], stp["to"]
                frm_label, to_label = get_room_label(frm), get_room_label(to)
                act = stp["action"]
                left_desc = stp.get("left_desc") or ""
                right_desc = stp.get("right_desc") or ""
                turn_txt = ""
                if act not in ["stairs_up", "stairs_down", "elevator"] and i < len(indoor_path2) - 1:
                    if i < len(indoor_path2) - 2:
                        a = rooms_df[rooms_df["room"] == indoor_path2[i]].iloc[0]
                        b = rooms_df[rooms_df["room"] == indoor_path2[i + 1]].iloc[0]
                        c = rooms_df[rooms_df["room"] == indoor_path2[i + 2]].iloc[0]
                        turn_txt = turn_direction(a, b, c)
                if act in ["stairs_up", "stairs_down", "elevator"]:
                    text = f"{act.replace('_',' ').title()} from {frm_label} to {to_label}."
                else:
                    lead = f"{turn_txt} towards {to_label}" if turn_txt else f"Walk from {frm_label} to {to_label}"
                    text = f"{lead} ({int(stp['distance'])} m)."
                context_bits = []
                if right_desc and str(right_desc).strip():
                    context_bits.append(f"Right: {right_desc}")
                if left_desc and str(left_desc).strip():
                    context_bits.append(f"Left: {left_desc}")
                if context_bits:
                    text += "  " + " | ".join(context_bits)
                combined_instructions.append(text)
                indoor_debug_rows.append({
                    "From": frm_label, "To": to_label, "Action": act.replace("_"," ").title(),
                    "Turn": turn_txt or "-", "Distance (m)": int(stp["distance"]),
                    "Right": right_desc or "-", "Left": left_desc or "-"
                })

# If route empty, stop
if not combined_coords:
    st.info("Could not compute route — check data in `data/`.")
    st.stop()

# ==============================
# Persist in session
# ==============================
st.session_state["campus_route_coords"] = combined_coords
st.session_state["campus_route_instr"] = combined_instructions
st.session_state["start_label"] = str(start_room)
st.session_state["end_label"] = str(end_room)

# ==============================
# Map style handling
# ==============================
def build_style(style_choice: str):
    # If a JSON style URL provided, use as-is. If a raster template, build a minimal style.
    if style_choice.endswith(".json"):
        return json.dumps(style_choice)  # we pass the URL string directly in JS
    # Raster template → construct a simple raster style
    style_obj = {
        "version": 8,
        "sources": {
            "raster-tiles": {
                "type": "raster",
                "tiles": [style_choice],
                "tileSize": 256,
                "attribution": "© OpenStreetMap contributors",
            }
        },
        "layers": [{"id": "simple-tiles", "type": "raster", "source": "raster-tiles"}],
    }
    return json.dumps(style_obj)

style_json_or_url = build_style(map_style)

# ==============================
# MapLibre frontend (3D, animated marker + segment context)
# ==============================
route_json = json.dumps(st.session_state["campus_route_coords"])
start_label_safe = get_room_label(st.session_state["start_label"]).replace("'", "\\'")
end_label_safe = get_room_label(st.session_state["end_label"]).replace("'", "\\'")

# Build mid-segment context labels (if any) from the indoor graph edges along path
# We’ll compute midpoints for segments that have left/right_desc and render small labels.
context_features = []
def add_context_point(lon_a, lat_a, lon_b, lat_b, text):
    mx = (lon_a + lon_b) / 2.0
    my = (lat_a + lat_b) / 2.0
    context_features.append({
        "type": "Feature",
        "properties": {"text": text},
        "geometry": {"type": "Point", "coordinates": [mx, my]},
    })

# Walk through polyline coords to produce midpoints every Nth step for simplicity
# (We only annotate if the source indoor edge had text; we approximated by scanning edges_df)
edge_lookup = {(str(row["start"]), str(row["end"])): row for _, row in edges_df.iterrows()}
edge_lookup.update({(str(row["end"]), str(row["start"])): row for _, row in edges_df.iterrows()})

poly = st.session_state["campus_route_coords"]
for i in range(len(poly) - 1):
    # Try to map this segment back to a known indoor edge by nearest node coordinates
    # (Best-effort; indoor coords usually match room nodes.)
    # We’ll check for any left/right_desc on this segment via lat/lon matching to rooms_df.
    # If not found, skip.
    # Fast index by rounding to ~6 decimals
    pass  # annotation handled below using indoor_debug_rows for textual panel; on-map labels will rely on steps below.

# To guarantee some context on-map when available, we add labels at every 8th vertex with step text (if exists)
# Build a small list of context strings from the indoor_debug_rows preserving order.
context_texts = []
for row in indoor_debug_rows:
    bits = []
    if row["Right"] and row["Right"] != "-":
        bits.append(f"Right: {row['Right']}")
    if row["Left"] and row["Left"] != "-":
        bits.append(f"Left: {row['Left']}")
    if bits:
        context_texts.append(" | ".join(bits))

if context_texts:
    step_interval = max(1, len(st.session_state["campus_route_coords"]) // (len(context_texts) + 1))
    idx = 0
    for txt in context_texts:
        idx = min(idx + step_interval, len(st.session_state["campus_route_coords"]) - 2)
        a = st.session_state["campus_route_coords"][idx]
        b = st.session_state["campus_route_coords"][idx + 1]
        add_context_point(a[0], a[1], b[0], b[1], txt)

context_fc = {"type": "FeatureCollection", "features": context_features}
context_geojson = json.dumps(context_fc)

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
  .ctx {{ background: rgba(0,0,0,0.7); color:#fff; padding:3px 6px; border-radius:6px; font-size:12px; white-space:nowrap; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="info"><b>Route:</b> {start_label_safe} → {end_label_safe}</div>
<script>
  const route = {route_json};
  const ctxPoints = {context_geojson};
  const styleSpec = {style_json_or_url};

  // Map: accept either a style URL string or a JSON object
  const map = new maplibregl.Map({{
    container: 'map',
    style: (typeof styleSpec === 'string' && styleSpec.endsWith('.json')) ? styleSpec : styleSpec,
    center: route[Math.floor(route.length/2)],
    zoom: 17,
    pitch: {pitch},
    bearing: {bearing}
  }});
  map.addControl(new maplibregl.NavigationControl());

  map.on('load', () => {{
    // Route source + line layer
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

    // Start/End markers with popups
    new maplibregl.Marker({{ color:'green' }}).setLngLat(route[0]).setPopup(new maplibregl.Popup().setText('Start: {start_label_safe}')).addTo(map);
    new maplibregl.Marker({{ color:'red' }}).setLngLat(route[route.length-1]).setPopup(new maplibregl.Popup().setText('End: {end_label_safe}')).addTo(map);

    // Fit bounds
    const bounds = route.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(route[0], route[0]));
    map.fitBounds(bounds, {{ padding: 60 }});

    // Animated walker
    const dot = document.createElement('div');
    dot.style.width = '18px'; dot.style.height = '18px'; dot.style.borderRadius = '50%';
    dot.style.background = 'rgba(255,140,0,1)'; dot.style.boxShadow = '0 0 12px rgba(255,140,0,0.9)';
    const marker = new maplibregl.Marker(dot).setLngLat(route[0]).addTo(map);
    let idx = 0;
    const speedMs = 80;
    function animateStep() {{
      if (idx < route.length - 1) {{
        idx++;
        marker.setLngLat(route[idx]);
        setTimeout(animateStep, speedMs);
      }}
    }}
    setTimeout(animateStep, 600);

    // Optional context labels along route (left/right descriptors)
    if (ctxPoints.features.length) {{
      map.addSource('ctx', {{ type:'geojson', data: ctxPoints }});
      map.addLayer({{
        id: 'ctx-symbols',
        type: 'symbol',
        source: 'ctx',
        layout: {{
          'text-field': ['get','text'],
          'text-size': 12,
          'text-offset': [0, 1.2],
          'text-anchor': 'top'
        }},
        paint: {{
          'text-color': '#111',
          'text-halo-color': '#fff',
          'text-halo-width': 1.2
        }}
      }});
    }}
  }});
</script>
</body>
</html>
"""
components.html(map_html, height=750, scrolling=False)

# ==============================
# Directions / Instructions panel
# ==============================
st.markdown("## 📝 Turn-by-turn Directions")
for i, ins in enumerate(st.session_state["campus_route_instr"], start=1):
    st.write(f"{i}. {ins}")

# Rich table for quick scan
if indoor_debug_rows:
    st.markdown("### 📋 Indoor Steps (detail)")
    df_debug = pd.DataFrame(indoor_debug_rows)
    st.dataframe(df_debug, use_container_width=True, hide_index=True)
