
#  Tanya UU Naker - Backend API

Hei bro ! Ini adalah repositori **Backend** (Otak) dari project **Tanya UU Naker**. Isinya API yang dibangun pake **FastAPI**, plus integrasi ke **Pinecone** (Vector DB) dan **Google Gemini 2.0** (LLM) buat mikir hukumnya.

Kalo frontend itu wajahnya, nah ini mesinnya

## Cara Jalanin di Localhost (Versi Indo)

Mau oprek logikanya? Gas ikutin langkah ini:

### 1. Syarat Wajib
Pastiin laptop lo udah ada **Python 3.10** ke atas.

### 2. Install Library
Buka terminal di folder ini, terus ketik:

```bash
pip install -r requirements.txt
````

### 3\. Atur Kunci Rahasia (.env)

Backend ini butuh kunci biar bisa jalan.

1.  Buat file baru namanya `.env` (tanpa nama depan, cuma ekstensi .env).
2.  Isi kayak gini (ganti sama key asli lo):

<!-- end list -->

```env
PINECONE_API_KEY=masukkan_key_pinecone_lo_disini
GEMINI_API_KEY=masukkan_key_gemini_lo_disini
```

### 4\. Nyalain Server 

Ketik perintah sakti ini:

```bash
uvicorn api:app --reload
```

Kalo sukses, server bakal jalan di `http://127.0.0.1:8000`.
Lo bisa cek dokumentasi API-nya (Swagger UI) di `http://127.0.0.1:8000/docs`.

Live demo website : https://tanya-uu-naker.vercel.app/

## How to Run Locally (English Version)

Wanna tweak the brain of "Tanya UU Naker"? Here we go:

### 1\. Prerequisites

Make sure **Python 3.10+** is installed on your machine.

### 2\. Install Dependencies

Open terminal in this folder and run:

```bash
pip install -r requirements.txt
```

### 3\. Setup Secrets (.env)

Create a `.env` file in the root folder and add your API keys:

```env
PINECONE_API_KEY=your_pinecone_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### 4\. Start the Server 

Run this command:

```bash
uvicorn api:app --reload
```

Boom\! Server runs at `http://127.0.0.1:8000`.
Check the API documentation at `http://127.0.0.1:8000/docs`.

