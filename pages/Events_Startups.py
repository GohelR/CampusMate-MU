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
        st.image("https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.forbes.com%2Fsites%2Fbernardmarr%2F2024%2F10%2F02%2Fwhy-hybrid-ai-is-the-next-big-thing-in-tech%2F&psig=AOvVaw2XV4PYoKtLO9-wFMdto28O&ust=1755086577883000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCNiBh6udhY8DFQAAAAAdAAAAABAE"+ev["title"].replace(" ","+"))
        st.subheader(ev["title"])
        st.write(ev["date"])
        st.write(ev["desc"])
        st.button("Register", key=f"reg_{i}")
