import streamlit as st
import pandas as pd
import networkx as nx
import folium
from streamlit_folium import st_folium

# -------------------------
# Page Setup
# -------------------------
st.set_page_config(page_title="Campus Navigation", page_icon="🗺️")
st.title("🗺️ Campus Navigation Guide")
st.write("Select your current room and destination to get directions inside campus.")

# -------------------------
# Load campus graph
# -------------------------
CSV_FILE = "data/campus_graph.csv"

try:
    edges = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    st.error(f"❌ Could not find {CSV_FILE}. Please upload it in `data/` folder.")
    st.stop()

# Build graph
G = nx.Graph()
for _, row in edges.iterrows():
    G.add_edge(row["start"], row["end"], weight=row["distance"])

rooms = list(G.nodes)

# -------------------------
# Dummy coordinates (replace with real later)
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
# Sidebar Inputs
# -------------------------
st.sidebar.header("🧭 Navigation Controls")
start = st.sidebar.selectbox("📍 From (Your Room):", rooms, index=0)
end = st.sidebar.selectbox("🎯 To (Destination Room):", rooms, index=1)

# -------------------------
# Map + Directions (Always Visible)
# -------------------------
map_container = st.container()
directions_container = st.container()

try:
    if start and end:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")

        # Create map
        m = folium.Map(location=[22.303, 70.783], zoom_start=18)

        # Draw path
        route_coords = [coords[node] for node in path if node in coords]
        if route_coords:
            folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)
            folium.Marker(coords[start], popup="Start", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(coords[end], popup="End", icon=folium.Icon(color="red")).add_to(m)

        # Show map (permanent)
        with map_container:
            st_folium(m, width=750, height=500)

        # Step-by-step directions
        with directions_container:
            st.subheader("📝 Step-by-Step Directions")
            for i in range(len(path) - 1):
                st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

except nx.NetworkXNoPath:
    st.error("⚠️ No path found between selected rooms.")
