import streamlit as st
import pandas as pd
import networkx as nx
import pydeck as pdk

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️", layout="wide")
st.title("🗺️ Campus Navigation Guide (3D WOW)")

# Load Mapbox token
MAPBOX_TOKEN = st.secrets["mapbox"]["token"]

# -------------------------
# Load graph and coordinates
# -------------------------
graph_file = "data/campus_graph.csv"
coords_file = "data/campus_coords.csv"

edges = pd.read_csv(graph_file)
coords = pd.read_csv(coords_file).set_index("room")

# Build graph
G = nx.Graph()
for _, row in edges.iterrows():
    G.add_edge(row["start"], row["end"], weight=row["distance"])

rooms = list(coords.index)

# -------------------------
# User input
# -------------------------
start = st.selectbox("📍 From (Your Room):", rooms)
end = st.selectbox("🎯 To (Destination Room):", rooms)

if st.button("🚀 Get Directions"):
    try:
        # Shortest path
        path = nx.shortest_path(G, source=start, target=end, weight="distance")

        # Convert path to coordinates
        route_coords = [[coords.loc[node, "lon"], coords.loc[node, "lat"]] for node in path]

        # Path layer
        path_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": route_coords}],
            get_color=[0, 0, 255],
            width_scale=10,
            width_min_pixels=5,
            get_width=5,
        )

        # Markers
        start_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"lon": coords.loc[start, "lon"], "lat": coords.loc[start, "lat"]}],
            get_position='[lon, lat]',
            get_color='[0,255,0,200]',
            get_radius=30,
        )
        end_layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{"lon": coords.loc[end, "lon"], "lat": coords.loc[end, "lat"]}],
            get_position='[lon, lat]',
            get_color='[255,0,0,200]',
            get_radius=30,
        )

        # View
        view_state = pdk.ViewState(
            longitude=coords.loc[start, "lon"],
            latitude=coords.loc[start, "lat"],
            zoom=18,
            pitch=60,
        )

        # Render map
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v12",
            initial_view_state=view_state,
            layers=[path_layer, start_layer, end_layer],
            mapbox_key=MAPBOX_TOKEN,
        ))

        # Step-by-step instructions
        st.subheader("📝 Directions")
        for i in range(len(path)-1):
            st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")
