# utils.py
import streamlit as st
import pandas as pd
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

@st.cache_data
def load_faq(path="data/faq.csv"):
    """Load the FAQ CSV, or return a small default if not found."""
    if not os.path.exists(path):
        df = pd.DataFrame({
            "Question": [
                "Where is the CR room?",
                "How to contact my mentor?",
                "What events are today?",
                "How can I find Block B?",
                "How to apply for admission?"
            ],
            "Answer": [
                "The CR room is in Block C, Room 203.",
                "Use the mentor tab in the dashboard to message them.",
                "TechFest '25 and Startup Showcase are happening today.",
                "Use the CampusMate navigation tool to get directions.",
                "Go to the Admission Help tab and follow the steps."
            ]
        })
        return df
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()  # normalize header
    return df

@st.cache_resource
def load_model_and_faiss(faq_df):
    """Load SBERT model and FAISS index from FAQ dataframe."""
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    questions = faq_df.iloc[:, 0].astype(str).tolist()  # first column
    embeddings = model.encode(questions, convert_to_numpy=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return model, index, embeddings

def similarity_search(model, index, faq_df, query, top_k=1):
    """Search FAQ for closest matches."""
    q_emb = model.encode([query], convert_to_numpy=True)
    D, I = index.search(q_emb, top_k)
    results = []
    for dist, idx in zip(D[0], I[0]):
        results.append((idx, dist, faq_df.iloc[idx, 1]))  # answer in col 2
    return results
