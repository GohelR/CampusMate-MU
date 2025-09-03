# streamlit_app.py (add or merge into your existing app)
import streamlit as st
import json
import os
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="CampusMate Map", layout="wide")

# 1) Get Mapbox token & style
mapbox_token = None
style_url = "mapbox://styles/mapbox/standard"  # default if not provided

# Try secrets first (recommended)
try:
    mapbox_token = st.secrets["mapbox"]["token"]
    style_url = st.secrets["mapbox"].get("style_url", style_url)
except Exception:
    mapbox_token = os.environ.get("MAPBOX_TOKEN")  # fallback

if not mapbox_token:
    st.warning("Mapbox token not found. Add it to .streamlit/secrets.toml or set MAPBOX_TOKEN as an environment variable.")
    st.stop()

# 2) Load campus GeoJSON
data_path = Path("data") / "campus.geojson"
if not data_path.exists():
    st.error(f"{data_path} not found. Add your campus.geojson and commit it.")
    st.stop()

campus_geojson = json.loads(data_path.read_text())

# 3) Sidebar: simple search/filter
st.sidebar.title("Campus Search")
query = st.sidebar.text_input("Find building (type name, e.g. 'Library')")

matches = []
for f in campus_geojson.get("features", []):
    name = f.get("properties", {}).get("name","").lower()
    if query.strip() == "" or query.strip().lower() in name:
        matches.append(f)

st.sidebar.write(f"Found {len(matches)} result(s)")
if len(matches) > 0:
    for f in matches:
        st.sidebar.write(f"- {f['properties'].get('name')}")

# Determine initial center: if matches non-empty, center on first match
if matches:
    center_lng, center_lat = matches[0]["geometry"]["coordinates"]
else:
    # fallback to first feature or default coords
    if campus_geojson.get("features"):
        center_lng, center_lat = campus_geojson["features"][0]["geometry"]["coordinates"]
    else:
        center_lng, center_lat = 72.525, 23.033

# 4) Read the HTML template and inject variables
html_path = Path("frontend") / "map.html"
if not html_path.exists():
    st.error(f"{html_path} not found. Add the frontend template.")
    st.stop()

html = html_path.read_text()
# replace placeholders (safe-ish): mapbox token, style, and geojson
injected_html = html.replace("{{MAPBOX_TOKEN}}", mapbox_token)\
                    .replace("{{STYLE_URL}}", style_url)\
                    .replace("{{GEOJSON}}", json.dumps(campus_geojson))

# 5) Display
st.title("🏫 Campus Map (Mapbox)")
components.html(injected_html, height=720, scrolling=True)
