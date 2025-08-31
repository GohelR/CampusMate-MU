import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="Campus Navigation Guide", page_icon="🗺️")

st.title("🌍 Campus Navigation Guide")
st.write("Select your current room and destination to get directions inside campus.")

# Dummy room coordinates (replace with real campus map data later)
rooms = {
    "MB201": [22.3039, 70.8022],  
    "MA202": [22.3050, 70.8005],
    "MB107": [22.3045, 70.8010],
    "MA407": [22.3060, 70.8030],
}

from_room = st.selectbox("📍 From (Your Room):", list(rooms.keys()))
to_room = st.selectbox("🎯 To (Destination Room):", list(rooms.keys()))

if "show_map" not in st.session_state:
    st.session_state.show_map = False

if st.button("🚀 Get Directions"):
    st.session_state.show_map = True

if st.session_state.show_map:
    start = rooms[from_room]
    end = rooms[to_room]

    st.success(f"📌 Path from **{from_room}** ➝ **{to_room}**")

    # Path line
    path = [start, end]

    # --- Path Layer (blue line) ---
    path_layer = pdk.Layer(
        "PathLayer",
        data=[{"path": path}],
        get_path="path",
        get_color=[0, 128, 255],
        width_scale=2,
        width_min_pixels=5,
    )

    # --- Marker Layer (pins) ---
    markers = [
        {"name": from_room, "lat": start[0], "lon": start[1], "color": [0, 200, 0]},
        {"name": to_room, "lat": end[0], "lon": end[1], "color": [200, 0, 0]},
    ]
    marker_layer = pdk.Layer(
        "ScatterplotLayer",
        data=markers,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius=15,
    )

    # --- Text Labels for Rooms ---
    text_layer = pdk.Layer(
        "TextLayer",
        data=markers,
        get_position=["lon", "lat"],
        get_text="name",
        get_size=20,
        get_color=[255, 255, 255],
        get_angle=0,
        get_alignment_baseline="'bottom'",
    )

    # --- Map View ---
    view_state = pdk.ViewState(
        latitude=(start[0] + end[0]) / 2,
        longitude=(start[1] + end[1]) / 2,
        zoom=17,
        pitch=50,  # tilt for 3D effect
    )

    # --- Show Map ---
    st.pydeck_chart(
        pdk.Deck(
            layers=[path_layer, marker_layer, text_layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/satellite-streets-v12",  # satellite 3D look
        )
    )
