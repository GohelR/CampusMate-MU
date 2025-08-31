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
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

# Dummy coordinates
coords = {
    "MB107": [22.301, 70.781],
    "MB108": [22.302, 70.782],
    "MB201": [22.303, 70.783],
    "MA101": [22.304, 70.784],
    "MA202": [22.305, 70.785],
    "MA407": [22.306, 70.786],
}

# -------------------------
# Store state (fix blinking)
# -------------------------
if "map" not in st.session_state:
    st.session_state.map = None
    st.session_state.path = None

if st.button("🚀 Get Directions"):
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")
        st.session_state.path = path

        m = folium.Map(location=[22.303, 70.783], zoom_start=18)
        route_coords = [coords[node] for node in path]
        folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)
        folium.Marker(coords[start], popup="Start", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(coords[end], popup="End", icon=folium.Icon(color="red")).add_to(m)

        st.session_state.map = m

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")

# -------------------------
# Show stored map + path
# -------------------------
if st.session_state.map:
    st_folium(st.session_state.map, width=700, height=500)

    st.subheader("📝 Directions")
    for i in range(len(st.session_state.path) - 1):
        st.write(f"➡️ Walk from **{st.session_state.path[i]}** to **{st.session_state.path[i+1]}**")
