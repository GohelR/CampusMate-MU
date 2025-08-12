import streamlit as st
from PIL import Image

# Page Config
st.set_page_config(page_title="CampusMate Dashboard", page_icon="🎓", layout="wide")

# Custom CSS
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Logo + Title
col1, col2 = st.columns([1,5])
with col1:
    st.image("assets/logo.png", width=80)
with col2:
    st.markdown("<h1>CampusMate - Student Portal</h1>", unsafe_allow_html=True)

st.markdown("### Welcome to your University Dashboard")

# Card Layout
cards = [
    ("💬 Chatbot", "Ask CampusMate anything from the FAQ", "pages/Chatbot.py"),
    ("📚 Student Section", "Access academic records, results & more", "pages/Student_Section.py"),
    ("📢 Announcements", "CR/CC/Mentor updates", "pages/Announcements.py"),
    ("🎉 Events", "Upcoming events & startup ideas", "pages/Events.py"),
    ("🗺 Campus Map", "Navigate through the campus", "pages/Campus_Map.py"),
    ("🛠 Admin Panel", "Manage users & updates", "pages/Admin.py"),
]

# Display Cards
cols = st.columns(3)
for idx, (title, desc, link) in enumerate(cards):
    with cols[idx % 3]:
        st.markdown(f"""
        <div class="card">
            <h3>{title}</h3>
            <p>{desc}</p>
            <a href="{link}">Go ➜</a>
        </div>
        """, unsafe_allow_html=True)
