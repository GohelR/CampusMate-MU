# pages/1_Chatbot.py
# Sidebar Navigation
st.sidebar.image("assets/logo.png", width=60)
st.sidebar.markdown("## 📌 Navigation")

pages = {
    "🏠 Home": "Home.py",
    "💬 Chatbot": "Chatbot.py",
    "📚 Student Section": "Student_Section.py",
    "📢 Announcements": "Announcements.py",
    "🎉 Events": "Events.py",
    "🗺 Campus Map": "Campus_Map.py",
    "🛠 Admin Panel": "Admin.py"
}

for name, link in pages.items():
    st.sidebar.markdown(f"[{name}]({link})")

import streamlit as st
from utils import load_faq, load_model_and_faiss, similarity_search

st.set_page_config(page_title="Chatbot", page_icon="🤖")
st.title("🤖 CampusMate Chatbot")
st.write("Ask student-related questions (FAQ-based).")

df = load_faq()

# load model
with st.spinner("Loading AI model and index... (cached)"):
    model, index, _ = load_model_and_faiss(df)

query = st.text_input("💬 Type your question here")
if st.button("Ask") or (query and st.session_state.get("auto_ask", False)):
    if not query:
        st.warning("Please enter a question.")
    else:
        results = similarity_search(model, index, df, query, top_k=3)
        # compute score from distance; lower distance => better
        best_idx, best_dist, best_answer = results[0]
        # Convert L2 distance to rough confidence
        conf = max(0, 1 - (best_dist / (best_dist + 1)))
        if conf < 0.35:
            st.warning("I am not confident about this answer. Try rephrasing or check announcements.")
        st.success(f"**Answer:** {best_answer}")
        st.write("---")
        st.write("Other close matches:")
        for idx, dist, ans in results[1:]:
            st.write(f"- {ans}  _(distance {dist:.3f})_")
