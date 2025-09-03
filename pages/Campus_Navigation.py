# pages/Campus_Navigation_All_Options.py
import json
from pathlib import Path

import networkx as nx
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation

# ---------- Page setup ----------
st.set_page_config(page_title="Campus Navigation — All Options", page_icon="🧭", layout="wide")
st.markdown("""
<style>
:root { --glass: rgba(255,255,255,0.85); }
.block { background: var(--glass); backdrop-filter: blur(8px); border-radius: 16px; padding: 14px 16px; box-shadow: 0 12px 28px rgba(0,0,0,0.08); }
h1,h2,h3 { margin-top: 0.4rem; }
.small { font-size: 0.9rem; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

st.title("🧭 CampusMate — All-Options Navigation (3D, GPS, Indoor+Outdoor)")

# ---------- Data loading helpers ----------
def read_nodes_edges(nodes_file: Path, edges_file: Path):
    nodes = pd.read_csv(nodes_file)
    edges = pd.read_csv(edges_file)
    # normalize
    nodes["id"] = nodes["id"].astype(str)
    if "is_entrance" in nodes:
        nodes["is_entrance"] = nodes["is_entrance"].astype(str).str.lower().isin(["true","1","yes"])
    else:
        nodes["is_entrance"] = False
    # types
    nodes["lat"] = nodes["lat"].astype(float)
    nodes["lon"] = nodes["lon"].astype(float)
    if "floor" in nodes:
        nodes["floor"] = nodes["floor"].fillna(0).astype(int)
    else:
        nodes["floor"] = 0
    nodes["building"] = nodes.get("building", pd.Series(["?"]*len(nodes))).astype(str)

    edges["u"] = edges["u"].astype(str)
    edges["v"] = edges["v"].astype(str)
    if "distance" not in edges:
        edges["distance"] = 1.0
    edges["distance"] = edges["distance"].astype(float)
    edges["action"] = edges.get("action", pd.Series(["walk"]*len(edges))).astype(str)
    return nodes, edges

def build_graph(nodes_df: pd.DataFrame, edges_df: pd.DataFrame):
    G = nx.Graph()
    for _, r in nodes_df.iterrows():
        G.add_node(
            r["id"],
            name=str(r.get("name", r["id"])),
            lat=float(r["lat"]),
            lon=float(r["lon"]),
            building=str(r.get("building","?")),
            floor=int(r.get("floor", 0)),
            is_entrance=bool(r.get("is_entrance", False)),
        )
    for _, r in edges_df.iterrows():
        G.add_edge(r["u"], r["v"], distance=float(r["distance"]), action=str(r["action"]))
    return G

def haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(math.sqrt(a))

def nearest_node_by_gps(nodes_df: pd.DataFrame, lat, lon, prefer_entrance_if_far=True):
    nearest = None; dmin = 10**12
    for _, r in nodes_df.iterrows():
        d = haversine(lat, lon, r["lat"], r["lon"])
        if d < dmin:
            nearest = r["id"]; dmin = d
    if prefer_entrance_if_far and dmin > 200:
        ents = nodes_df[nodes_df["is_entrance"] == True]
        if not ents.empty:
            n2 = None; d2min = 10**12
            for _, r in ents.iterrows():
                d2 = haversine(lat, lon, r["lat"], r["lon"])
                if d2 < d2min:
                    n2 = r["id"]; d2min = d2
            return n2, d2min
    return nearest, dmin

def osrm_route(lon1, lat1, lon2, lat2):
    url = f"http://router.project-osrm.org/route/v1/walking/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview":"full","geometries":"geojson","steps":"true"}
    try:
        resp = requests.get(url, params=params, timeout=12)
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
                t = man.get("type","").replace("_"," ")
                mod = man.get("modifier","")
                text = f"{t} {mod} → {name} ({int(dist)} m)".strip()
                instrs.append(text)
        return coords, instrs
    except Exception:
        return None, []

# ---------- Sidebar: Data ----------
with st.sidebar:
    st.header("📦 Data")
    nodes_upl = st.file_uploader("Upload nodes.csv", type=["csv"], key="nodes_upl")
    edges_upl = st.file_uploader("Upload edges.csv", type=["csv"], key="edges_upl")
    st.caption("Or keep empty to use `data/nodes.csv` and `data/edges.csv` from the repo.")

# Load nodes/edges (uploaded or from data/)
data_dir = Path("data")
try:
    if nodes_upl and edges_upl:
        nodes_df = pd.read_csv(nodes_upl)
        edges_df = pd.read_csv(edges_upl)
        # normalize
        nodes_df, edges_df = read_nodes_edges(nodes_df.to_csv(index=False), edges_df.to_csv(index=False))  # not used; we re-validate below
        # Reparse properly (above line is awkward for UploadedFile). Do again neatly:
        nodes_upl.seek(0); edges_upl.seek(0)
        nodes_df = pd.read_csv(nodes_upl)
        edges_df = pd.read_csv(edges_upl)
    else:
        nodes_df, edges_df = read_nodes_edges(data_dir/"nodes.csv", data_dir/"edges.csv")
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# Final normalize (ensure schema)
nodes_df, edges_df = read_nodes_edges(nodes_df if isinstance(nodes_df, Path) else nodes_df, edges_df if isinstance(edges_df, Path) else edges_df)

# Build graph
G = build_graph(nodes_df, edges_df)

# ---------- Sidebar: Layers & Map ----------
with st.sidebar:
    st.header("🗺️ Map & Layers")
    pitch = st.slider("3D tilt (pitch)", 0, 70, 55)
    bearing = st.slider("Rotation (bearing)", -180, 180, 0)
    show_nodes = st.checkbox("Show nodes", True)
    show_edges = st.checkbox("Show edges", True)
    show_entrances = st.checkbox("Highlight entrances", True)
    animate_route = st.checkbox("Animate route", True)
    st.markdown("---")
    st.info("Allow browser **location** for GPS start.")
    geo = get_geolocation()
    gps_lat = geo["coords"]["latitude"] if geo and "coords" in geo else None
    gps_lon = geo["coords"]["longitude"] if geo and "coords" in geo else None
    if gps_lat and gps_lon:
        st.success(f"GPS: {gps_lat:.6f}, {gps_lon:.6f}")
    else:
        st.warning("GPS not available yet, or permission denied.")

# ---------- Routing controls ----------
st.markdown("### 🎯 Routing", help="Pick start & destination. You can start from GPS.")
col1, col2, col3 = st.columns([1.2,1.2,0.8])

all_nodes = nodes_df["id"].tolist()
with col1:
    start_mode = st.radio("Start point", ["Use my GPS", "Choose node"], horizontal=True)
    if start_mode == "Choose node":
        start_node = st.selectbox("From node (room/poi):", all_nodes, index=0, key="start_node_select")
    else:
        start_node = None

with col2:
    end_node = st.selectbox("To node (room/poi):", all_nodes, index=min(1, len(all_nodes)-1), key="end_node_select")

with col3:
    route_btn = st.button("Compute Route 🚀", use_container_width=True)

# Keep results in session to avoid re-render blinking
if "route_coords" not in st.session_state:
    st.session_state["route_coords"] = []
    st.session_state["route_steps"] = []
    st.session_state["route_nodes"] = []

def node_info(nid):
    a = G.nodes[nid]
    return a["lat"], a["lon"], a["building"], a["floor"], a["name"]

def path_to_coords(path_nodes):
    coords = []
    for nid in path_nodes:
        lat, lon, *_ = node_info(nid)
        coords.append([lon, lat])  # lng,lat for MapLibre
    return coords

# ---------- Compute route ----------
if route_btn:
    try:
        # Determine start node
        if start_mode == "Use my GPS":
            if gps_lat is None or gps_lon is None:
                st.warning("GPS not available; choose a start node.")
                st.stop()
            start_node, d0 = nearest_node_by_gps(nodes_df, gps_lat, gps_lon, prefer_entrance_if_far=True)
            st.info(f"Start snapped to nearest node: **{start_node}** (≈{int(d0)} m)")
        # sanity
        if start_node == end_node:
            st.info("Already at destination.")
            st.stop()

        s_bld = G.nodes[start_node]["building"]
        e_bld = G.nodes[end_node]["building"]

        full_coords = []
        all_steps = []
        full_path_nodes = []

        # If buildings differ and you have an outdoor edge between entrances, we can simply run shortest_path on the joint graph.
        # This will naturally traverse indoor nodes → entrance → outdoor → entrance → indoor nodes.
        # If no explicit outdoor edges exist, we can OSRM between entrances as a fallback.
        try:
            path = nx.shortest_path(G, source=start_node, target=end_node, weight="distance")
            full_path_nodes = path
            # Build textual steps from edge actions
            for i in range(len(path)-1):
                u, v = path[i], path[i+1]
                data = G.get_edge_data(u, v)
                action = data.get("action", "walk")
                dist = int(data.get("distance", 0))
                if action == "stairs_up":
                    all_steps.append(f"Take stairs up from {u} to {v} ({dist} m).")
                elif action == "stairs_down":
                    all_steps.append(f"Take stairs down from {u} to {v} ({dist} m).")
                elif action == "elevator":
                    all_steps.append(f"Use elevator from {u} to {v} ({dist} m).")
                elif action == "outdoor":
                    all_steps.append(f"Walk outdoors from {u} to {v} ({dist} m).")
                else:
                    all_steps.append(f"Walk from {u} to {v} ({dist} m).")
            full_coords = path_to_coords(path)
        except nx.NetworkXNoPath:
            # Fallback: OSRM between nearest entrances of buildings, then indoor on each side.
            def pick_entrance(building):
                cand = [n for n, d in G.nodes(data=True) if d.get("building")==building and d.get("is_entrance", False)]
                return cand[0] if cand else None
            s_ent = pick_entrance(s_bld)
            e_ent = pick_entrance(e_bld)
            if s_ent is None or e_ent is None:
                st.error("No path & missing entrances for OSRM fallback. Add entrance nodes or outdoor edges.")
                st.stop()
            # indoor start to entrance
            in1 = nx.shortest_path(G, start_node, s_ent, weight="distance")
            # OSRM outdoors
            s_lat, s_lon, *_ = node_info(s_ent)
            e_lat, e_lon, *_ = node_info(e_ent)
            osrm_coords, osrm_instr = osrm_route(s_lon, s_lat, e_lon, e_lat)
            # indoor entrance to end
            in2 = nx.shortest_path(G, e_ent, end_node, weight="distance")

            # Combine coords
            full_path_nodes = in1 + [e_ent] + in2  # nodes list (approx)
            full_coords = path_to_coords(in1)
            if osrm_coords:
                full_coords.extend(osrm_coords)
            full_coords.extend(path_to_coords(in2))

            # text steps
            def add_edge_steps(p):
                for i in range(len(p)-1):
                    u, v = p[i], p[i+1]
                    ed = G.get_edge_data(u, v)
                    dist = int(ed.get("distance", 0)) if ed else 0
                    act = (ed or {}).get("action", "walk")
                    all_steps.append(f"{act.replace('_',' ').title()} from {u} to {v} ({dist} m).")
            add_edge_steps(in1)
            if osrm_coords:
                all_steps.extend(osrm_instr)
            add_edge_steps(in2)

        st.session_state["route_coords"] = full_coords
        st.session_state["route_steps"] = all_steps
        st.session_state["route_nodes"] = full_path_nodes

    except Exception as e:
        st.error(f"Routing failed: {e}")

# ---------- Map render ----------
route_coords = st.session_state.get("route_coords", [])
route_steps = st.session_state.get("route_steps", [])
route_nodes = st.session_state.get("route_nodes", [])

# Prepare GeoJSON for nodes & edges layers
def nodes_geojson(df):
    feats = []
    for _, r in df.iterrows():
        feats.append({
            "type":"Feature",
            "properties":{
                "id": r["id"],
                "name": str(r.get("name", r["id"])),
                "building": str(r.get("building","?")),
                "floor": int(r.get("floor",0)),
                "is_entrance": bool(r.get("is_entrance", False)),
            },
            "geometry":{"type":"Point","coordinates":[float(r["lon"]), float(r["lat"])]}
        })
    return {"type":"FeatureCollection","features":feats}

def edges_geojson(G):
    feats=[]
    for u,v,data in G.edges(data=True):
        a=G.nodes[u]; b=G.nodes[v]
        feats.append({
            "type":"Feature",
            "properties":{
                "u":u,"v":v,
                "action":data.get("action","walk"),
                "distance":float(data.get("distance",0))
            },
            "geometry":{"type":"LineString","coordinates":[[a["lon"],a["lat"]],[b["lon"],b["lat"]]]}
        })
    return {"type":"FeatureCollection","features":feats}

nodes_fc = nodes_geojson(nodes_df)
edges_fc = edges_geojson(G)
route_fc = {
    "type":"FeatureCollection",
    "features":[{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":route_coords}}]
} if route_coords else {"type":"FeatureCollection","features":[]}

# Map center
if route_coords:
    center = route_coords[len(route_coords)//2]
else:
    # mean center of nodes
    if len(nodes_df):
        center = [nodes_df["lon"].mean(), nodes_df["lat"].mean()]
    else:
        center = [70.783, 22.303]

map_html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Campus 3D Map</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<style>
  html,body,#map{{height:70vh;margin:0;padding:0}}
  .legend {{ position:absolute; right:10px; top:10px; background:rgba(255,255,255,0.9); padding:8px 12px; border-radius:8px; box-shadow:0 8px 18px rgba(0,0,0,.15); font: 13px/1.4 Arial; }}
  .dot {{ display:inline-block; width:10px;height:10px;border-radius:50%;margin-right:6px; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="legend">
  <div><span class="dot" style="background:#1f78b4"></span>Route</div>
  <div><span class="dot" style="background:#34a853"></span>Entrances</div>
  <div><span class="dot" style="background:#666"></span>Nodes</div>
</div>
<script>
const pitch = {pitch};
const bearing = {bearing};
const nodes = {json.dumps(nodes_fc)};
const edges = {json.dumps(edges_fc)};
const route = {json.dumps(route_fc)};
const showNodes = {str(show_nodes).lower()};
const showEdges = {str(show_edges).lower()};
const showEntrances = {str(show_entrances).lower()};
const animate = {str(animate_route).lower()};

const map = new maplibregl.Map({{
    container: 'map',
    style: 'https://demotiles.maplibre.org/style.json',
    center: [{center[0]}, {center[1]}],
    zoom: 17, pitch: pitch, bearing: bearing
}});
map.addControl(new maplibregl.NavigationControl());

map.on('load', () => {{
  // Nodes
  map.addSource('nodes', {{ type:'geojson', data: nodes }});
  map.addLayer({{
    id:'nodes-circles',
    type:'circle',
    source:'nodes',
    paint:{{
      'circle-radius': 5,
      'circle-color': ['case',['get','is_entrance'],'#34a853','#666'],
      'circle-stroke-color':'#fff',
      'circle-stroke-width': 1
    }},
    layout: {{ 'visibility': showNodes ? 'visible' : 'none' }}
  }});

  // Labels
  map.addLayer({{
    id:'nodes-labels',
    type:'symbol',
    source:'nodes',
    layout:{{
      'text-field': ['get','id'],
      'text-size': 11,
      'text-offset': [0, 1.1],
      'visibility': showNodes ? 'visible' : 'none'
    }},
    paint: {{ 'text-color': '#111', 'text-halo-color':'#fff','text-halo-width':1 }}
  }});

  // Entrances highlight (extra glow)
  if (showEntrances) {{
    map.addLayer({{
      id:'nodes-entrances',
      type:'circle',
      source:'nodes',
      filter:['==',['get','is_entrance'], true],
      paint:{{ 'circle-radius': 10, 'circle-color':'rgba(52,168,83,0.15)' }}
    }});
  }}

  // Edges
  map.addSource('edges', {{ type:'geojson', data: edges }});
  map.addLayer({{
    id:'edges-line',
    type:'line',
    source:'edges',
    paint:{{ 'line-color':'#999','line-width':2,'line-opacity':0.7 }},
    layout: {{ 'visibility': showEdges ? 'visible' : 'none' }}
  }});

  // Route
  map.addSource('route', {{ type:'geojson', data: route }});
  map.addLayer({{
    id:'route-line',
    type:'line',
    source:'route',
    paint:{{ 'line-color':'#1f78b4','line-width':6,'line-opacity':0.9 }}
  }});

  // Fit to route if exists else to all nodes
  const fc = route.features;
  if (fc && fc.length && fc[0].geometry.coordinates.length) {{
    const coords = fc[0].geometry.coordinates;
    const b = coords.reduce((b,c)=>b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]));
    map.fitBounds(b, {{ padding: 60 }});
  }} else if (nodes.features.length) {{
    const coords = nodes.features.map(f=>f.geometry.coordinates);
    const b = coords.reduce((b,c)=>b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]));
    map.fitBounds(b, {{ padding: 60 }});
  }}

  // Animated marker along the route
  if (animate && route.features.length && route.features[0].geometry.coordinates.length > 1) {{
    const coords = route.features[0].geometry.coordinates;
    const dot = document.createElement('div');
    dot.style.width='18px'; dot.style.height='18px'; dot.style.borderRadius='50%';
    dot.style.background='rgba(255,140,0,1)'; dot.style.boxShadow='0 0 12px rgba(255,140,0,0.9)';
    const walker = new maplibregl.Marker(dot).setLngLat(coords[0]).addTo(map);
    let i=0;
    const speed=70;
    const step=()=>{{ if(i<coords.length-1){{ i++; walker.setLngLat(coords[i]); setTimeout(step, speed); }} }};
    setTimeout(step, 500);
  }}
}});
</script>
</body>
</html>
"""

st.markdown("<div class='block'>", unsafe_allow_html=True)
components.html(map_html, height=540, scrolling=False)
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Directions ----------
st.markdown("### 📝 Turn-by-Turn")
if route_steps:
    for i, line in enumerate(route_steps, start=1):
        st.write(f"{i}. {line}")
else:
    st.write("_No route yet. Choose start/destination and click **Compute Route**._")

# ---------- Export ----------
st.markdown("### 📤 Export")
if route_coords:
    gj = {
        "type":"FeatureCollection",
        "features":[{"type":"Feature","properties":{"name":"CampusMate Route"},"geometry":{"type":"LineString","coordinates":route_coords}}]
    }
    st.download_button("Download Route GeoJSON", data=json.dumps(gj).encode("utf-8"),
                       file_name="campusmate_route.geojson", mime="application/geo+json")
else:
    st.caption("Route export available after you compute a route.")
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
