import streamlit as st
import networkx as nx
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.title("🗺️ Campus Navigation Guide")
st.write("Select your current room and destination to get step-by-step directions inside campus.")

# -------------------------
# Campus Graph (Demo)
# -------------------------
edges = [
    ("MB107", "MB108", 5),
    ("MB108", "MB201", 7),
    ("MB201", "MA101", 12),
    ("MA101", "MA202", 8),
    ("MA202", "MA407", 15),
]

# Build graph
G = nx.Graph()
for start, end, dist in edges:
    G.add_edge(start, end, weight=dist)

rooms = list(G.nodes)
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

# -------------------------
# Dummy coordinates (replace with real)
# -------------------------
coords = {
    "MB107": [22.301, 70.781],
    "MB108": [22.302, 70.782],
    "MB201": [22.303, 70.783],
    "MA101": [22.304, 70.784],
    "MA202": [22.305, 70.785],
    "MA407": [22.306, 70.786],
}

# -------------------------
# Show map only when user clicks
# -------------------------
if st.button("🚀 Get Directions"):
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")
        st.success(" ➝ ".join(path))

        # 🌍 Create OSM Map with 3D Buildings
        m = folium.Map(location=[22.303, 70.783], zoom_start=18, tiles="cartodbpositron")

        # Add 3D building layer (using OSM Buildings)
        folium.TileLayer(
            tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            attr="OpenStreetMap"
        ).add_to(m)

        # Path
        route_coords = [coords[node] for node in path]
        folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

        # Markers
        folium.Marker(coords[start], popup="Start", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(coords[end], popup="End", icon=folium.Icon(color="red")).add_to(m)

        # Display stable map (no blinking ✨)
        st_folium(m, width=900, height=600)

        # Directions
        st.subheader("📝 Step-by-Step Directions")
        for i in range(len(path) - 1):
            st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")
