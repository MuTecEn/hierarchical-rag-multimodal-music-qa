import os
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
import PyPDF2
import librosa
import pretty_midi
import gc
from collections import Counter
import re
import musicalgestures as mg

DATA_FOLDER = r"\\path\to\dataset"  # set your dataset path here
EXCLUDE_FOLDERS = {"Timing"}
DB_FOLDER = r"path\to\chroma_db"  # update according to your chroma_db folder location
COLLECTION_NAME = "My_collection" # update
CHUNK_WORDS = 150  # chunk large texts into smaller pieces if you have memory issues

# ---------------------------
# INIT
# ---------------------------

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=DB_FOLDER)
collection = client.get_or_create_collection(COLLECTION_NAME)

# ---------------------------
# TEXT HELPERS
# ---------------------------

def chunk_text(text, max_words=CHUNK_WORDS):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def extract_keywords(text, n=5):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    counts = Counter(words)
    return ", ".join([w for w,_ in counts.most_common(n)])

# ---------------------------
# TEXT FILE
# ---------------------------

def process_text_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    keywords = extract_keywords(text)

    return f"""
Text document: {os.path.basename(path)}
Keywords: {keywords}

{text}
"""

# ---------------------------
# PDF FILE
# ---------------------------
def process_pdf_file(path):
    text = ""

    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    keywords = extract_keywords(text)

    return f"""
PDF file: {os.path.basename(path)}
Pages: {len(reader.pages)}
Keywords: {keywords}

{text}
"""

# ---------------------------
# AUDIO FILE (musical fingerprint)
# ---------------------------
def process_audio_file(path):

    try:
        y, sr = librosa.load(path, sr=None, mono=True)

        duration = len(y) / sr

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(np.squeeze(tempo))

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_density = float(np.mean(onset_env))

        chroma_summary = ", ".join([f"{float(c):.2f}" for c in chroma_mean])

        return f"""
Audio recording: {os.path.basename(path)}

Duration: {duration:.2f} seconds
Tempo: {tempo:.2f} BPM

Spectral centroid: {centroid:.0f} Hz
Spectral bandwidth: {bandwidth:.0f} Hz

Onset density: {onset_density:.2f}

Chroma profile: {chroma_summary}

Musical fingerprint:
moderate tempo rhythmic dance recording with tonal pitch structure.
"""

    except Exception as e:
        print(f"Audio error {os.path.basename(path)}:", e)
        return None

# ---------------------------
# MIDI FILE
# ---------------------------
def process_midi_file(path):

    try:
        midi_data = pretty_midi.PrettyMIDI(path)

        instruments = [instr.name for instr in midi_data.instruments if instr.name]

        duration = midi_data.get_end_time()

        notes = [note for instr in midi_data.instruments for note in instr.notes]

        pitches = [n.pitch for n in notes]

        pitch_range = max(pitches) - min(pitches) if pitches else 0

        note_density = len(notes) / duration if duration > 0 else 0

        return f"""
MIDI file: {os.path.basename(path)}

Duration: {duration:.2f} seconds
Instruments: {', '.join(instruments) if instruments else "Unknown"}

Pitch range: {pitch_range} semitones
Note density: {note_density:.2f} notes per second
Total notes: {len(notes)}
"""

    except Exception as e:
        print(f"MIDI error {os.path.basename(path)}:", e)
        return None

# ---------------------------
# VIDEO FILE
# ---------------------------
def process_video_file(path):
    """
    Process a video file and compute Quantity of Motion (QoM) using musicalgestures.
    """
    # Load the video
    video_data = mg.Video(path)

    # Compute Quantity of Motion (QoM)
    qom = mg.compute_qom(video_data)

    # Return a summary string
    return f"""
Video file: {os.path.basename(path)}
Quantity of Motion (QoM): {qom:.3f}
"""

# ---------------------------
# EMBEDDING + STORAGE
# ---------------------------
def embed_and_add(text, doc_id, file_type, folder):

    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):

        embedding = embedding_model.encode(chunk)

        embedding = np.array(embedding, dtype=np.float32).tolist()

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{doc_id}::{i}"],
            metadatas=[{
                "source": doc_id,
                "type": file_type,
                "folder": folder
            }]
        )

        del embedding
        gc.collect()

# ---------------------------
# INDEXING
# ---------------------------
print("Indexing dataset...")

for root, dirs, files in os.walk(DATA_FOLDER):

    dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]

    for file in files:

        path = os.path.join(root, file)

        text = None
        file_type = None

        if file.lower().endswith((".txt", ".csv")):
            text = process_text_file(path)
            file_type = "text"

        elif file.lower().endswith(".pdf"):
            text = process_pdf_file(path)
            file_type = "pdf"

        elif file.lower().endswith((".wav",".mp3",".flac")):
            text = process_audio_file(path)
            file_type = "audio"

        elif file.lower().endswith((".mid",".midi")):
            text = process_midi_file(path)
            file_type = "midi"

        elif file.lower().endswith((".mp4",".mov",".avi")):
            text = process_video_file(path)
            file_type = "video"

        if text:
            embed_and_add(text, os.path.relpath(path, DATA_FOLDER), file_type, root)
            print("Indexed:", file)

print("Individual Indexing complete.")

# ---------------------------
# FOLDER SUMMARY FUNCTION
# ---------------------------
def summarize_folder(folder_path):
    file_types = []
    file_count = 0
    all_text = ""

    for root, dirs, files in os.walk(folder_path):
        for f in files:
            file_types.append(os.path.splitext(f)[1].lower())
            file_count += 1

            # OPTIONAL: read small text snippets
            if f.endswith(".txt"):
                try:
                    with open(os.path.join(root, f), encoding="utf-8") as file:
                        all_text += file.read()[:500]
                except:
                    pass

    counts = Counter(file_types)
    keywords = extract_keywords(all_text, n=10)

    summary = f"""
Folder: {os.path.basename(folder_path)}
Total files: {file_count}

File types:
{counts}

Keywords: {keywords}
"""

    return summary.strip()

# ---------------------------
# INDEX FOLDER SUMMARIES
# ---------------------------
print("Indexing folder summaries...")
for root, dirs, files in os.walk(DATA_FOLDER):
    summary_text = summarize_folder(root)
    embed_and_add(summary_text, f"folder::{os.path.basename(root)}", "folder_summary", root)
    print(f"Indexed folder summary: {root}")