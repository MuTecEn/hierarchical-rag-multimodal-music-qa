import json

import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import numpy as np

DB_FOLDER = r"path\to\chroma_db" # update according to your chroma_db folder location
COLLECTION_NAME = "MY_collection" # update according to your collection name

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

embedding_model.max_seq_length = 512

client_llm = OpenAI(
    base_url="http://127.0.0.1:1337/v1", # replace with actual URL if different, following step 3
    api_key="not-needed"
)

client_db = chromadb.PersistentClient(path=DB_FOLDER)
collection = client_db.get_or_create_collection(COLLECTION_NAME)

print("RAG assistant ready\n")

# ---------------------------
# LOOP
# ---------------------------
while True:

    query = input("Ask a question: ")

    if query.lower() in ["exit", "bye"]:
        break

    # ---------------------------
    # EMBED QUERY
    # ---------------------------
    query_embedding = embedding_model.encode(query)
    query_embedding = np.array(query_embedding, dtype=np.float32).tolist()

    # ---------------------------
    # RETRIEVE SUMMARIES
    # ---------------------------
    summary_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        where={"type": "folder_summary"}
    )

    # ---------------------------
    # RETRIEVE CONTENT
    # ---------------------------
    content_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"type": {"$ne": "folder_summary"}}
    )

    # ---------------------------
    # EXTRACT
    # ---------------------------
    summary_docs = summary_results["documents"][0] if summary_results["documents"] else []
    content_docs = content_results["documents"][0] if content_results["documents"] else []

    summary_meta = summary_results["metadatas"][0] if summary_results["metadatas"] else []
    content_meta = content_results["metadatas"][0] if content_results["metadatas"] else []

    # ---------------------------
    # BUILD CONTEXT
    # ---------------------------
    context = ""

    if summary_docs:
        context += "\n=== DATASET STRUCTURE ===\n"
        context += "\n\n".join(summary_docs)

    if content_docs:
        context += "\n\n=== DETAILED CONTENT ===\n"
        context += "\n\n".join(content_docs)

    # ---------------------------
    # PREPARE SOURCE JSON
    # ---------------------------
    retrieval_info = {
        "folder_summaries_used": [
            {"source": m["source"], "type": m["type"]}
            for m in summary_meta
        ],
        "content_sources_used": [
            {"source": m["source"], "type": m["type"]}
            for m in content_meta
        ]
    }

    # ---------------------------
    # PROMPT (FORCE JSON OUTPUT)
    # ---------------------------
    prompt = f"""
You are helping explore a multimodal music research dataset.

Use the provided context.

Return ONLY valid JSON in this exact structure:

{{
  "question": "...",
  "answer": {{
    "file_types": [...],
    "description": "...",
    "musical_materials": {{
      "tradition": "...",
      "forms": [...],
      "characteristics": [...],
      "evidence": [...]
    }},
    "structure_relationship": {{
      "folder_name": "description"
    }},
    "conclusion": "..."
  }}
}}

Do not include any extra text outside JSON.

Context:
{context}

Question:
{query}
"""

    # ---------------------------
    # LLM CALL
    # ---------------------------
    response = client_llm.chat.completions.create(
        model="janhq\\Jan-v3-4b-base-instruct-Q4_K_XL",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content

    # ---------------------------
    # PARSE JSON SAFELY
    # ---------------------------
    try:
        parsed = json.loads(raw_output)
    except Exception:
        print("\nModel did not return valid JSON. Raw output:\n")
        print(raw_output)
        continue

    # ---------------------------
    # MERGE WITH RETRIEVAL INFO
    # ---------------------------
    final_output = {
        "question": query,
        "retrieval": retrieval_info,
        "answer": parsed.get("answer", {})
    }

    # ---------------------------
    # PRINT CLEAN JSON
    # ---------------------------
    print("\n--- RESULT ---\n")
    print(json.dumps(final_output, indent=2, ensure_ascii=False))