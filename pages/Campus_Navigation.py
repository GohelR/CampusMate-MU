import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="Campus Navigation Guide", page_icon="🗺️")

st.title("🌍 Campus Navigation Guide")
st.write("Select your current room and destination to get directions inside campus.")

# Dummy room coordinates (replace with real campus map data later)
rooms = {
    "MB201": [22.3039, 70.8022],  # Example: Rajkot Lat/Lon
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

    st.success(f"Showing path from **{from_room}** ➝ **{to_room}**")

    # Path line
    path = [start, end]

    # Pydeck map
    layer = pdk.Layer(
        "PathLayer",
        data=[{"path": path}],
        get_path="path",
        get_color=[0, 128, 255],
        width_scale=2,
        width_min_pixels=5,
    )

    view_state = pdk.ViewState(
        latitude=start[0],
        longitude=start[1],
        zoom=16,
        pitch=45,
    )

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
