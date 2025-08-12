# pages/4_Announcements.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Announcements", page_icon="📣")
st.title("📣 CR / CC / Mentor Announcement Board")

# Dummy announcements
ann = [
    {"who":"CR - AI/ML", "text":"Unit test on Aug 20 in Block C", "time": datetime.now()-timedelta(days=1)},
    {"who":"CC - CSE", "text":"Assignment due Friday 5 PM", "time": datetime.now()-timedelta(hours=10)},
    {"who":"Mentor", "text":"Mentor meeting on Wednesday 3 PM", "time": datetime.now()-timedelta(days=2)}
]

st.write("Latest announcements:")
for a in ann:
    st.info(f"**{a['who']}** — {a['text']}  \n _{a['time'].strftime('%b %d %H:%M')}_")
