import streamlit as st
import pandas as pd
import networkx as nx
import pydeck as pdk

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")

st.title("🗺️ CampusMate Navigation")
st.write("Enter your current room and destination to get 3D navigation inside campus.")

# -------------------------
# Load campus graph
# -------------------------
CSV_FILE = "data/campus_graph.csv"
edges = pd.read_csv(CSV_FILE)

# Build graph
G = nx.Graph()
for _, row in edges.iterrows():
    G.add_edge(row["start"], row["end"], weight=row["distance"])

rooms = list(G.nodes)
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

# Dummy coordinates (replace with real later)
coords = {
    "MB107": [70.781, 22.301],
    "MB201": [70.782, 22.303],
    "MA101": [70.783, 22.304],
    "MA202": [70.784, 22.305],
    "MA407": [70.785, 22.306],
}

if st.button("🚀 Get Directions"):
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")

        # Show path text
        st.success(" ➝ ".join(path))

        # Build route coordinates for pydeck
        route_coords = [[coords[node][0], coords[node][1]] for node in path]

        # Mapbox layer: path
        route_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": route_coords}],
            get_path="path",
            get_color=[0, 0, 255],
            width_scale=2,
            width_min_pixels=4,
        )

        # Mapbox layer: points
        point_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"pos": coords[node]} for node in path],
            get_position="pos",
            get_color=[255, 0, 0],
            get_radius=10,
        )

        # DeckGL view
        view_state = pdk.ViewState(
            latitude=22.303,
            longitude=70.783,
            zoom=17,
            pitch=60,   # tilt = 3D
        )

        r = pdk.Deck(
            layers=[route_layer, point_layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/streets-v12",
            api_keys={"mapbox": st.secrets["MAPBOX_TOKEN"]},  # 🔑
        )

        st.pydeck_chart(r)

        # Step directions
        st.subheader("📝 Directions")
        for i in range(len(path)-1):
            st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")
