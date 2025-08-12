# pages/3_Student_Section.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Student Section", page_icon="👤")
st.title("👤 Student Section")

# Dummy profile
profile = {
    "Name": "Ravi Gohel",
    "Enrollment": "92510118030",
    "Branch": "CSE - AI & ML",
    "Email": "ravi.n.gohel811@gmail.com"
}

st.write("### Profile")
for k, v in profile.items():
    st.write(f"**{k}:** {v}")

# Attendance dummy
st.write("### Attendance")
subjects = ["Maths","DSA","AI/ML","DBMS"]
attendance = [90, 85, 92, 88]
att_df = pd.DataFrame({"Subject": subjects, "Attendance": attendance})
fig = px.pie(att_df, values='Attendance', names='Subject', title="Attendance %")
st.plotly_chart(fig, use_container_width=True)
