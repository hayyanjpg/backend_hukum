import os
import sys
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from groq import Groq


PINECONE_API_KEY = "sudah di pindah ke env"
GROQ_API_KEY = "sudah dipindah ke env"

INDEX_NAME = "uu-naker"

def init_systems():
    print("  Memuat model dan koneksi...")
    
    embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # 2. Koneksi Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    
    # 3. Koneksi Groq
    client = Groq(api_key=GROQ_API_KEY)
    
    return embedder, index, client

def get_answer(query_text, embedder, index, groq_client):
    print(f"\n Mencari referensi hukum untuk: '{query_text}'...")
    
    # melakukan retrieval(pencarian)
    query_vector = embedder.encode(query_text).tolist()
    
    try:
        results = index.query(
            vector=query_vector,
            top_k=5, #5 pasal bersangkutan tertinggi
            include_metadata=True
        )
    except Exception as e:
        return f"Error koneksi Pinecone: {e}"

    # Filter hasil (Thresholding)
    contexts = []
    sources = []
    
    for match in results['matches']:
        # menurut saya diatas 0.30 sudah cukup relaban
        if match['score'] > 0.30: 
            text = match['metadata']['text']
            pasal = match['metadata']['pasal']
            contexts.append(text)
            sources.append(pasal)

    if not contexts:
        return " Maaf, tidak ditemukan pasal yang relevan di database UU Ketenagakerjaan."

    context_block = "\n\n".join(contexts)
    source_list = ", ".join(list(set(sources))) # Hilangkan duplikat

    # --- STEP 2: GENERATION (LLM) ---
    print(f" Menemukan konteks: {source_list}")
    print(" Mengonstruksi jawaban...")

    system_prompt = """
    Anda adalah Asisten Hukum Ketenagakerjaan Indonesia yang Kritis dan Akurat.
    Tugas Anda: Menjawab pertanyaan user HANYA berdasarkan 'KONTEKS HUKUM' yang diberikan di bawah.
    
    Aturan Keras:
    1. JANGAN menggunakan pengetahuan luar selain dari konteks yang diberikan.
    2. Jika jawaban tidak ada di konteks, katakan "Informasi tidak ditemukan dalam pasal yang tersedia".
    3. WAJIB menyebutkan Nomor Pasal dan Ayat yang menjadi dasar hukum jawaban Anda.
    4. Jawab dengan gaya bahasa formal, lugas, dan terstruktur (gunakan poin-poin jika perlu).
    5. Jangan bertele-tele.
    """

    user_prompt = f"""
    KONTEKS HUKUM (UU No 13 Tahun 2003):
    {context_block}

    PERTANYAAN USER:
    {query_text}
    """

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile", # Model tercerdas di Groq
            temperature=0.0, # 0.0 agar jawaban konsisten dan tidak halusinasi
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error Groq API: {e}"

# --- MAIN LOOP ---
if __name__ == "__main__":
    try:
        embedder, index, client = init_systems()
        print("\n Sistem Siap. Silakan tanya soal UU Ketenagakerjaan.")
        print("(Ketik 'exit' untuk keluar)\n")
        
        while True:
            print("-" * 50)
            user_input = input(">> Pertanyaan: ")
            if user_input.lower() in ['exit', 'keluar', 'quit']:
                break
            
            if not user_input.strip():
                continue
                
            response = get_answer(user_input, embedder, index, client)
            
            print("\nJAWABAN AI:")
            print("=" * 20)
            print(response)
            print("="*20 + "\n")
            
    except Exception as e:
        print(f"\n Terjadi Error Fatal: {e}")
        print("Pastikan API Key benar dan internet stabil.")