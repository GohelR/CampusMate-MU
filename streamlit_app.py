# streamlit_app.py
import streamlit as st

st.set_page_config(page_title="CampusMate - Home", page_icon="🎓", layout="wide")
st.title("CampusMate — AI Student Dashboard (MU)")
st.markdown("""
Welcome to **CampusMate** — your AI-powered student dashboard for Marwadi University.
Use the left sidebar to open:
- Chatbot
- Academic Record
- Student Section
- CR/CC/Mentor Board
- Events & Startups
- Admin Panel
- Campus Navigation
""")

st.markdown("Made by **Ravi Gohel** (CSE - AI & ML).")
st.info("Tip: open the Chatbot page first and try 'Where is the CR room?'")
