import streamlit as st
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np

# --------------------------
# Page config
# --------------------------
st.set_page_config(page_title="CampusMate", page_icon="🎓")
st.title("🎓 CampusMate - AI Chatbot for Students")
st.write("Ask me anything from the FAQ!")

# --------------------------
# Load FAQ CSV
# --------------------------
CSV_FILE = "data/faq.csv"
try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    st.error(f"❌ Could not find `{CSV_FILE}`. Please upload it to your repo.")
    st.stop()

# --------------------------
# Load model and FAISS index
# --------------------------
@st.cache_resource
def load_model_and_index():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(df["question"].tolist(), convert_to_numpy=True)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return model, index

model, index = load_model_and_index()

# --------------------------
# User input
# --------------------------
query = st.text_input("💬 Your question:")

if query:
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, 1)
    best_idx = indices[0][0]
    answer = df.iloc[best_idx]["answer"]

    st.markdown(f"**Answer:** {answer}")
