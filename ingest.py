import json
import time
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec # Import ServerlessSpec buat index serverless


PINECONE_API_KEY = "sudah di pindah ke .env" 
INDEX_NAME = "uu-naker"

def run_ingestion():
    print("  Menginisialisasi...")
    
    # 1. Koneksi Pinecone
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
    except Exception as e:
        print(f" API Key salah: {e}")
        return

    # 2. CEK & BUAT INDEX OTOMATIS (Logika Baru)
    existing_indexes = [i.name for i in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        print(f" Index '{INDEX_NAME}' tidak ditemukan. Sedang membuat baru...")
        try:
            pc.create_index(
                name=INDEX_NAME,
                dimension=384, # Sesuai model MiniLM
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1' # Region default free tier
                )
            )
            print(" Menunggu index siap (sekitar 10-20 detik)...")
            time.sleep(15) # Wajib tunggu agar ready
        except Exception as e:
            print(f" Gagal membuat index. Pastikan region benar atau kuota cukup: {e}")
            return
    else:
        print(f" Index '{INDEX_NAME}' ditemukan.")

    index = pc.Index(INDEX_NAME)

    # 3. Load Model
    print(" Loading model embedding...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    # 4. Baca Data
    try:
        filename = 'parsed_uu_fixed.json'
        with open(filename, 'r', encoding='utf-8') as f:
            data_uu = json.load(f)
        print(f"Membaca {len(data_uu)} pasal.")
    except FileNotFoundError:
        print(f" File {filename} tidak ditemukan.")
        return

    # 5. Upload Loop
    batch_size = 30
    vectors_to_upload = []
    count_skipped = 0
    
    print("\n Memulai upload ke Pinecone...")
    
    for i, item in enumerate(data_uu):
        text_content = item['text']
        
        # Filter Sampah
        if len(text_content) < 50:
            count_skipped += 1
            continue

        vector_values = model.encode(text_content).tolist()
        
        vector_payload = {
            "id": item['id'],
            "values": vector_values,
            "metadata": {
                "text": text_content,
                "pasal": item['metadata']['pasal'],
                "source": item['metadata']['source']
            }
        }
        vectors_to_upload.append(vector_payload)
        
        # Upload Batch
        if len(vectors_to_upload) >= batch_size or i == len(data_uu) - 1:
            try:
                index.upsert(vectors=vectors_to_upload)
                print(f" Batch terupload (Index {i})")
                vectors_to_upload = [] 
                time.sleep(0.2) 
            except Exception as e:
                print(f" Gagal upload: {e}")

    print("\n" + "="*30)
    print(f" SELESAI!")
    print(f" Data sampah dibuang: {count_skipped}")
    print("="*30)

if __name__ == "__main__":
    run_ingestion()