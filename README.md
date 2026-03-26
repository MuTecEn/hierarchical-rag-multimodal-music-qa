# Hierarchical RAG for Multimodal Music QA

This repository implements a hierarchical Retrieval-Augmented Generation (RAG) system for natural language interaction with multimodal music datasets. The system combines vector-based semantic retrieval (via ChromaDB) with a locally deployed Jan LLM to enable cross-modal question answering and dataset summarization.

---

## 🔹 Usage Instructions

These instructions guide you through setting up and running the RAG system.

### 1. Clone the Repository and Create Environment
```bash
# Clone the repository
git clone https://github.com/yourusername/hierarchical-rag-multimodal-music-qa.git
cd hierarchical-rag-multimodal-music-qa

# Create a local Python environment
python -m venv rag_env

# Activate environment (Windows)
rag_env\Scripts\activate

# Activate environment (macOS/Linux)
source rag_env/bin/activate

# Install required packages
pip install -r requirements.txt

### 2. Prepare ChromaDB
Create a folder for the vector database:

```bash
mkdir chroma_db

### 3. Set Up Jan Local Server
1. Download and install Jan locally.
2. Start the server and make note of the API endpoint.
3. Update the config.json file in this repo with your Jan API URL:
```bash
{
    "jan_api_url": "http://localhost:8080"
}

### 4. Select a Model in Jan

Open the Jan interface in your browser.
Choose a model to interact with (e.g., Jan-v3-4b-base-instruct-Q4_K_XL).
Make sure the model is running successfully.

### 5. Sanity Check
Run a quick test to ensure the Jan API connection works:
```bash
python testjan.py

### 6. Index Your Dataset
Run the indexing script to prepare your multimodal data:
```bash
python index_files.py

This will populate the chroma_db folder with embeddings for all dataset files.

### 7. Run RAG Queries
Use the query interface to interact with the system:
```bash
python rag_query.py

Enter natural language questions about your dataset.


