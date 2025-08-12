import streamlit as st
import pandas as pd

st.set_page_config(page_title="Student Section", page_icon="🎓")

st.title("🎓 Student Section")

# Load student data
CSV_FILE = "data/student_records.csv"

try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    st.error("❌ Student records file not found. Please add `data/student_records.csv`.")
    st.stop()

# Input for GR Number
gr_number = st.text_input("Enter your GR Number:")

if gr_number:
    student_data = df[df["GRNumber"].astype(str) == gr_number]

    if not student_data.empty:
        st.subheader("📌 Student Details")
        st.write(f"**Name:** {student_data.iloc[0]['Name']}")
        st.write(f"**Branch:** {student_data.iloc[0]['Branch']}")
        st.write(f"**Year:** {student_data.iloc[0]['Year']}")
        st.write(f"**Email:** {student_data.iloc[0]['Email']}")
        st.write(f"**Phone:** {student_data.iloc[0]['Phone']}")

        # Side menu
        st.sidebar.title("📂 Student Services")
        page = st.sidebar.radio("Select Service", ["Result", "Bonafide", "Admission", "FV Debit"])

        if page == "Result":
            st.subheader("📜 Result")
            st.info("Result data will appear here (dummy).")
        elif page == "Bonafide":
            st.subheader("📜 Bonafide Certificate")
            st.info("Bonafide request and download link will appear here (dummy).")
        elif page == "Admission":
            st.subheader("🏫 Admission Details")
            st.info("Admission details will appear here (dummy).")
        elif page == "FV Debit":
            st.subheader("💰 Fee / FV Debit Info")
            st.info("Fee debit details will appear here (dummy).")

    else:
        st.warning("⚠️ No student found with that GR Number.")
