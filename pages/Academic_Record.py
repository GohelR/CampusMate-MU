# pages/2_Academic_Record.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Academic Record", page_icon="📚")
st.title("📚 Academic Record")

# Dummy student marks
students = ["You (Ravi)", "Student A", "Student B"]
subjects = ["Maths", "DSA", "AI/ML", "DBMS"]
data = {
    "Student": [],
    "Subject": [],
    "Marks": []
}
import random
for s in students:
    for sub in subjects:
        data["Student"].append(s)
        data["Subject"].append(sub)
        data["Marks"].append(random.randint(45, 95))

df = pd.DataFrame(data)

student = st.selectbox("Choose Student", students, index=0)
df_s = df[df["Student"] == student]

st.subheader(f"{student}'s marks")
st.dataframe(df_s)

fig = px.bar(df_s, x="Subject", y="Marks", range_y=[0,100], title="Marks by subject")
st.plotly_chart(fig, use_container_width=True)
