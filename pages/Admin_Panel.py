# pages/6_Admin_Panel.py
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Admin Panel", page_icon="🛠️")
st.title("🛠️ Admin Panel (demo)")

st.write("Add a quick announcement (this will be in-session only).")

who = st.selectbox("Post as", ["CR - AI/ML","CC - CSE","Mentor"])
text = st.text_area("Message")
if st.button("Post Announcement"):
    st.success("Posted!")
    st.write(f"**{who}** — {text}  \n _{datetime.now().strftime('%b %d %H:%M')}_")
