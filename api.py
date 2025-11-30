from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from typing import List, Optional

# ==========================================
# 1. KONFIGURASI ENV
# ==========================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ambil Key & Bersihkan
raw_pinecone = os.environ.get("PINECONE_API_KEY")
PINECONE_API_KEY = raw_pinecone.strip() if raw_pinecone else None

raw_gemini = os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY = raw_gemini.strip() if raw_gemini else None

INDEX_NAME = "uu-naker"

# ==========================================
# 2. SETUP APLIKASI
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⚙️  MEMULAI SERVER (GEMINI VERSION WITH MEMORY)...")

# Load Embedding
embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# Load Pinecone
if not PINECONE_API_KEY:
    print("❌ ERROR: PINECONE_API_KEY Kosong!")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# Load Gemini
if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY Kosong!")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    # Gunakan Gemini 2.0 Flash (Cepat & Pintar)
    model = genai.GenerativeModel('gemini-2.0-flash')

print("✅ Server Siap 100%!")

# --- DATA MODEL BARU (MENDUKUNG HISTORY) ---
class Message(BaseModel):
    role: str # 'user' atau 'ai'
    content: str

class QueryRequest(BaseModel):
    question: str
    history: List[Message] = [] # List kosong jika chat baru

# ==========================================
# 3. HELPER FUNCTION: QUERY REWRITING
# ==========================================
def rewrite_query(user_question, history_list):
    """
    Mengubah pertanyaan ambigu ("saya harus gimana?") menjadi 
    pertanyaan spesifik ("Langkah hukum pekerja PHK") berdasarkan history.
    """
    if not history_list:
        return user_question # Jika chat baru, tidak perlu rewrite
    
    # Format history menjadi teks string
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in history_list[-4:]]) # Ambil 4 chat terakhir
    
    prompt = f"""
    Tugas: Ubah pertanyaan user menjadi "Search Query" yang lengkap untuk database hukum, berdasarkan riwayat obrolan.
    
    RIWAYAT CHAT:
    {history_text}
    
    PERTANYAAN USER SAAT INI:
    "{user_question}"
    
    INSTRUKSI:
    - Jika pertanyaan user merujuk ke topik sebelumnya (contoh: "gimana hitungannya?", "apa sanksinya?"), gabungkan dengan konteks sebelumnya.
    - Output HANYA satu kalimat pertanyaan yang jelas. Jangan ada penjelasan lain.
    
    SEARCH QUERY BARU:
    """
    
    try:
        response = model.generate_content(prompt)
        new_query = response.text.strip()
        print(f"🔄 Rewritten Query: '{user_question}' -> '{new_query}'")
        return new_query
    except:
        return user_question # Fallback jika gagal

# ==========================================
# 4. ENDPOINT CHAT
# ==========================================
@app.post("/chat")
async def chat_endpoint(req: QueryRequest):
    original_question = req.question
    history = req.history
    
    print(f"\n📩 Incoming: {original_question}")

    # --- LANGKAH 1: CONTEXTUALIZE (REWRITE QUERY) ---
    # Kita cari di database menggunakan query yang sudah diperjelas AI
    search_query = rewrite_query(original_question, history)

    # --- LANGKAH 2: RETRIEVAL (PENCARIAN DATA) ---
    try:
        query_vector = embedder.encode(search_query).tolist()
        results = index.query(
            vector=query_vector,
            top_k=8, 
            include_metadata=True
        )
    except Exception as e:
        print(f"❌ Pinecone Error: {e}")
        raise HTTPException(status_code=500, detail="Database Error")

    contexts = []
    unique_sources = {} 

    for match in results['matches']:
        if match['score'] > 0.30:
            text_isi = match['metadata']['text']
            pasal_judul = match['metadata']['pasal']
            contexts.append(text_isi)
            if pasal_judul not in unique_sources:
                unique_sources[pasal_judul] = text_isi

    # Jika tidak ketemu, coba fallback ke pertanyaan asli (opsional)
    if not contexts:
        print("⚠️ Context kosong dengan rewritten query, mencoba original query...")
        # (Kode retry opsional bisa ditaruh sini, tapi kita skip biar simple)
        
        # Tetap lanjut, biarkan LLM menjawab "Tidak tahu" atau basa-basi sopan
        # Agar tidak error 500

    # --- LANGKAH 3: PROMPT PREPARATION ---
    context_block = "\n\n".join(contexts)
    
    # Format history untuk prompt akhir
    chat_history_str = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in history[-4:]])

    full_prompt = f"""
    PERAN:
    Anda adalah Asisten Virtual (AI) spesialis UU Ketenagakerjaan Indonesia (UU No 13 Tahun 2003).
    Tugas: Menjawab pertanyaan user berdasarkan KONTEKS HUKUM dan RIWAYAT PERCAKAPAN.

    DATA SUMBER (KONTEKS):
    {context_block}

    RIWAYAT PERCAKAPAN:
    {chat_history_str}

    PERTANYAAN USER SAAT INI:
    {original_question}

    INSTRUKSI:
    1. Disclaimer: Awali dengan "Berdasarkan penelusuran data UU No. 13 Tahun 2003..."
    2. Konteks: Jawab pertanyaan user dengan mempertimbangkan riwayat percakapan sebelumnya (jika user bertanya "lalu bagaimana?", sambungkan dengan topik sebelumnya).
    3. Dasar Hukum: Gunakan informasi dari DATA SUMBER untuk menjawab. Sebutkan Pasal.
    4. Jika pertanyaan bersifat saran ("Saya harus gimana"), berikan langkah normatif sesuai UU (misal: Lapor ke Disnaker, Bipartit, dll) jika ada di konteks. Jika tidak ada, sarankan konsultasi ke ahli hukum.
    
    Batasan:
    - Jangan mengarang pasal.
    """

    try:
        response = model.generate_content(full_prompt)
        ai_answer = response.text
        
        formatted_sources = [{"pasal": k, "isi": v} for k, v in unique_sources.items()]

        return {
            "answer": ai_answer,
            "sources": formatted_sources
        }

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")