# pages/5_Events_Startups.py
import streamlit as st

st.set_page_config(page_title="Events & Startups", page_icon="🎉")
st.title("🗓️ Events & Startup Showcase")

events = [
    {"title":"TechFest 2025","date":"Aug 15","desc":"Robotics, Coding, Gaming"},
    {"title":"Startup Expo","date":"Aug 20","desc":"Student startup showcase"},
    {"title":"AI Workshop","date":"Aug 18","desc":"AI/ML hands-on bootcamp"}
]

cols = st.columns(3)
for i, ev in enumerate(events):
    with cols[i]:
        st.image("https://via.placeholder.com/300x150?text="+ev["title"].replace(" ","+"))
        st.subheader(ev["title"])
        st.write(ev["date"])
        st.write(ev["desc"])
        st.button("Register", key=f"reg_{i}")
