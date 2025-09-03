import streamlit as st
import pandas as pd
import networkx as nx
import folium
from streamlit_folium import st_folium

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
    st.error(f"❌ Could not find {CSV_FILE}. Please upload it.")
    st.stop()

# Create graph
G = nx.Graph()
for _, row in edges.iterrows():
    G.add_edge(row["start"], row["end"], weight=row["distance"])

rooms = list(G.nodes)

# -------------------------
# User input
# -------------------------
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

# Dummy coordinates (replace with real lat/lon)
coords = {
    "MB101": [22.301, 70.781],
    "MB102": [22.302, 70.782],
    "MB201": [22.303, 70.783],
    "MA101": [22.304, 70.784],
    "MA202": [22.305, 70.785],
    "MA407": [22.306, 70.786],
    "Library": [22.307, 70.787],
    "Canteen": [22.308, 70.788],
}

# -------------------------
# Pathfinding + Map
# -------------------------
if st.button("🚀 Get Directions"):
    if start not in G.nodes:
        st.error(f"⚠️ Start room {start} not found in campus graph!")
    elif end not in G.nodes:
        st.error(f"⚠️ Destination room {end} not found in campus graph!")
    else:
        try:
            path = nx.shortest_path(G, source=start, target=end, weight="distance")
            st.success(" ➝ ".join(path))

            # Map visualization
            route_coords = [coords.get(node, [22.303, 70.783]) for node in path]
            m = folium.Map(location=route_coords[0], zoom_start=18)

            folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)
            folium.Marker(route_coords[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(route_coords[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)

            st_folium(m, width=700, height=500)

            st.subheader("📝 Step-by-step Directions")
            for i in range(len(path)-1):
                st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

        except nx.NetworkXNoPath:
            st.error("⚠️ No path found between selected rooms.")
