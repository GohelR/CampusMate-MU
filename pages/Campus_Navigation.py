# pages/Campus_Navigation.py
import streamlit as st
import pandas as pd
import networkx as nx
import pydeck as pdk
import json
from pathlib import Path

# -------------------------
# Page setup + style
# -------------------------
st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
/* Glassmorphic header card */
.glass {
  background: rgba(255, 255, 255, 0.55);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.35);
  padding: 18px 22px;
}
.badge {
  display:inline-block; padding:4px 10px; border-radius:999px; 
  background:#eef2ff; color:#4338ca; font-weight:600; font-size:12px; margin-right:10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="glass"><span class="badge">LIVE</span>'
    '<span style="font-size:26px;font-weight:800">📍 Campus Navigation Guide</span>'
    '<div style="opacity:.7">Turn-by-turn inside your campus with 3D map.</div>'
    '</div>',
    unsafe_allow_html=True
)

# -------------------------
# Mapbox token (required)
# -------------------------
MAPBOX_TOKEN = st.secrets.get("MAPBOX_API_KEY", None)
if not MAPBOX_TOKEN:
    st.error("⚠️ Missing Mapbox token. Add `MAPBOX_API_KEY` in Streamlit Secrets / Render Environment.")
    st.stop()

pdk.settings.mapbox_api_key = MAPBOX_TOKEN

# -------------------------
# Load data
# -------------------------
GRAPH_CSV = Path("data/campus_graph.csv")
ROOMS_CSV = Path("data/rooms.csv")
BUILDINGS_GEOJSON = Path("data/buildings.geojson")  # optional

if not GRAPH_CSV.exists():
    st.error(f"❌ `{GRAPH_CSV}` not found.")
    st.stop()
if not ROOMS_CSV.exists():
    st.error(f"❌ `{ROOMS_CSV}` not found.")
    st.stop()

edges = pd.read_csv(GRAPH_CSV)
rooms_df = pd.read_csv(ROOMS_CSV)

# Build Graph
G = nx.Graph()
for _, r in edges.iterrows():
    G.add_edge(r["start"], r["end"], weight=float(r["distance"]))

rooms = sorted(rooms_df["room"].unique().tolist())

# -------------------------
# Sidebar controls
# -------------------------
with st.sidebar:
    st.header("🧭 Navigation")
    start = st.selectbox("From (Your Room):", rooms, index=0, key="start_room")
    end = st.selectbox("To (Destination):", rooms, index=min(1, len(rooms)-1), key="end_room")
    pitch = st.slider("Map tilt", 0, 85, 60)
    bearing = st.slider("Map bearing", -180, 180, 30)
    style = st.selectbox(
        "Map style",
        [
            "mapbox://styles/mapbox/streets-v12",
            "mapbox://styles/mapbox/outdoors-v12",
            "mapbox://styles/mapbox/light-v11",
            "mapbox://styles/mapbox/dark-v11",
            "mapbox://styles/mapbox/satellite-streets-v12",
        ],
        index=2
    )
    show_buildings = st.checkbox("Show 3D buildings (if geojson available)", value=True)

# Helper: fetch lat/lon by room
def room_xy(room):
    row = rooms_df.loc[rooms_df["room"] == room]
    if row.empty:
        return None, None
    return float(row.iloc[0]["lat"]), float(row.iloc[0]["lon"])

# Compute route (NetworkX inside-campus routing)
route_nodes = []
route_coords_latlon = []
if start and end:
    try:
        route_nodes = nx.shortest_path(G, source=start, target=end, weight="distance")
        for n in route_nodes:
            lat, lon = room_xy(n)
            if lat is not None:
                route_coords_latlon.append([lat, lon])
    except nx.NetworkXNoPath:
        st.warning("No path found between selected rooms.")

# Center map on route or fallback
if route_coords_latlon:
    avg_lat = sum(c[0] for c in route_coords_latlon)/len(route_coords_latlon)
    avg_lon = sum(c[1] for c in route_coords_latlon)/len(route_coords_latlon)
else:
    # fallback center = median of all rooms
    avg_lat = rooms_df["lat"].median()
    avg_lon = rooms_df["lon"].median()

# Deck.gl expects [lon, lat]
route_coords_lonlat = [[c[1], c[0]] for c in route_coords_latlon]

# -------------------------
# Layers
# -------------------------
layers = []

# 3D Buildings (optional, from GeoJSON)
if show_buildings and BUILDINGS_GEOJSON.exists():
    with open(BUILDINGS_GEOJSON, "r", encoding="utf-8") as f:
        buildings_geo = json.load(f)

    buildings_layer = pdk.Layer(
        "PolygonLayer",
        data=buildings_geo,
        get_polygon="geometry.coordinates",
        get_fill_color=[200, 200, 200, 90],
        pickable=True,
        extruded=True,
        wireframe=False,
        get_elevation="properties.height",
        elevation_scale=1.2,
    )
    layers.append(buildings_layer)

# Start/End markers
points = []
s_lat, s_lon = room_xy(start)
e_lat, e_lon = room_xy(end)
if s_lat is not None:
    points.append({"name": f"Start • {start}", "lon": s_lon, "lat": s_lat, "color": [0, 190, 0]})
if e_lat is not None:
    points.append({"name": f"End • {end}", "lon": e_lon, "lat": e_lat, "color": [220, 30, 30]})

if points:
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame(points),
            get_position="[lon, lat]",
            get_color="color",
            get_radius=7,
            radius_min_pixels=7,
            pickable=True,
        )
    )

# Route line (pretty + thick)
if route_coords_lonlat:
    layers.append(
        pdk.Layer(
            "PathLayer",
            data=[{"path": route_coords_lonlat, "name": "Route"}],
            get_path="path",
            get_width=6,
            width_min_pixels=5,
            get_color=[24, 119, 242],
            rounded=True,
            pickable=True,
        )
    )

# Optional: animated trip (wow factor)
# Creates a simple animated visual along the same path
if len(route_coords_lonlat) >= 2:
    trip_data = [{
        "name": "Walking",
        "path": [[pt[0], pt[1], t*200] for t, pt in enumerate(route_coords_lonlat)]
    }]
    layers.append(
        pdk.Layer(
            "TripsLayer",
            data=trip_data,
            get_path="path",
            get_timestamps="path[*][2]",
            get_color=[255, 140, 0],
            opacity=0.8,
            width_min_pixels=3,
            trail_length=1200,  # milliseconds
            current_time=1200,  # show full path
        )
    )

# -------------------------
# View & render
# -------------------------
view_state = pdk.ViewState(
    latitude=avg_lat,
    longitude=avg_lon,
    zoom=18,
    pitch=pitch,
    bearing=bearing,
)

tooltip = {"text": "{name}"}

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style=style,
    tooltip=tooltip,
)

st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# Directions panel
# -------------------------
st.markdown("### 📝 Directions")
if route_nodes:
    for i in range(len(route_nodes) - 1):
        st.write(f"➡️ Walk from **{route_nodes[i]}** to **{route_nodes[i+1]}**")
    total_dist = 0
    for i in range(len(route_nodes) - 1):
        edge = edges[(edges["start"] == route_nodes[i]) & (edges["end"] == route_nodes[i+1])]
        if edge.empty:
            edge = edges[(edges["start"] == route_nodes[i+1]) & (edges["end"] == route_nodes[i])]
        if not edge.empty:
            total_dist += float(edge.iloc[0]["distance"])
    st.success(f"Total distance: **{total_dist:.1f} m** (demo)")
else:
    st.info("Pick a start and destination to see the route.")
