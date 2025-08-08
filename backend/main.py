from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np

app = FastAPI(title="CampusMate Backend", version="1.0")

# Allow frontend to call backend from GitHub Pages or any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load FAQ CSV
CSV_FILE = "data/faq.csv"  # <- You changed the file name here
df = pd.read_csv(CSV_FILE)

# Load model + FAISS index
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(df["question"].tolist(), convert_to_numpy=True)
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

@app.get("/")
def root():
    return {"message": "CampusMate API is running!"}

@app.get("/chatbot")
def chatbot(query: str = Query(..., description="User's question")):
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, 1)
    best_idx = indices[0][0]
    answer = df.iloc[best_idx]["answer"]
    return {"query": query, "answer": answer}

