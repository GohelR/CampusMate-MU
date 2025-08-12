# pages/7_Campus_Navigation.py
import streamlit as st

st.set_page_config(page_title="Campus Navigation", page_icon="🗺️")
st.title("🗺️ Campus Navigation Guide")

st.write("Search for a building or pick from the list:")

blocks = {
    "Block A":"Academic Block A - Main lectures",
    "Block B":"Administration and labs",
    "Block C":"Hostels and CR room",
    "Cafeteria":"Main cafeteria near the gate"
}

choice = st.selectbox("Choose location", list(blocks.keys()))
st.write(f"**{choice}** — {blocks[choice]}")

st.image("https://via.placeholder.com/800x400?text=Campus+Map")
st.write("Tip: Replace placeholder image with a real campus map in the `pages/7_Campus_Navigation.py` file.")
