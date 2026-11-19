# Evaluasi retrieval — Tanya UU Naker

Tanggal: 2026-11-20

## Yang benar-benar diukur

Ini **baseline BM25 lokal**, bukan angka retrieval embedding Pinecone yang dipakai aplikasi. BM25 dipilih karena bisa dijalankan ulang tanpa API key, tanpa model, dan tanpa jaringan. Tujuannya bukan membuktikan RAG sudah bagus, tapi memberi titik awal yang bisa dicek siapa saja.

Retrieval embedding asli (SentenceTransformer + Pinecone, `top_k=8`, threshold `score > 0.30`) **belum saya ukur**. Menaruh angka BM25 seolah-olah angka sistem produksi itu menyesatkan, jadi tidak saya lakukan.

Cara jalan:

```bash
python eval/retrieval_eval.py           # ringkas
python eval/retrieval_eval.py --detail  # + per-query miss
```

Korpus diambil dari `parsed_uu_fixed.json`. Script memakai filter `len(text) >= 50` yang **sama dengan `ingest.py`**, jadi yang dievaluasi adalah 160 chunk yang benar-benar masuk index — bukan 165 pasal mentah.

## Eval set

20 pertanyaan bahasa Indonesia, labelnya diambil dari teks pasal di korpus (`eval/queries.jsonl`). Bukan dari log user, bukan hasil generasi LLM. Labelnya satu atau beberapa nomor pasal yang dianggap relevan.

## Hasil

| Metrik | Nilai |
| --- | --- |
| hit@1 | 15/20 = 75,0% |
| hit@5 | 17/20 = 85,0% |
| hit@8 | 17/20 = 85,0% |
| MRR@10 | 0,799 |
| Gold tidak ada di index | 1 query |

Angka hit@8 sengaja ditampilkan karena `api.py` memakai `top_k=8`. `query.py` memakai `top_k=5`; dua jalur ini belum disatukan.

## Kegagalan yang paling informatif

| Query | Masalah |
| --- | --- |
| q07 — anak di bawah 13 tahun | Gold-nya `Pasal 68`, tapi chunk ini **tidak pernah masuk index**: teksnya cuma 48 karakter ("Pengusaha dilarang mempekerjakan anak.") dan dibuang filter `< 50` di `ingest.py`. Ini bukan salah retrieval; jawabannya memang tidak ada di database. |
| q01 — jam kerja sehari | `Pasal 77` baru muncul di rank 12. Kueri memakai "sehari dan seminggu", teks pasal memakai "7 (tujuh) jam 1 (satu) hari". |
| q20 — upah tidak dibayar berbulan-bulan | `Pasal 169` di rank 17. Teks pasal menyebut "3 (tiga) bulan berturut-turut", bukan "berbulan-bulan". |
| q13, q14 | Gold masuk top-3 (rank 2 dan 3), jadi masih tertampung oleh `top_k=8`. |

q01 dan q20 menunjukkan keterbatasan pencocokan kata kunci. Embedding kemungkinan membantu di sini — tapi itu masih perlu diukur, bukan diasumsikan.

## Masalah korpus yang ikut ketemu

1. **`Pasal 33` adalah blob 19.750 karakter.** Isinya bukan pasal 33 saja, tapi pembukaan + hampir seluruh UU (BAB I, pasal 1, dan seterusnya). Parser di `parser.py` mengira semua itu satu pasal karena nomor pasal di dalam teks lebih kecil dari nomor yang sedang aktif. Chunk sebesar ini berisiko mendominasi retrieval untuk topik umum.
2. **5 pasal gugur di ingest:** `Pasal 5`, `20`, `27`, `28`, `68`. Sebagian memang potongan parser (`Pasal 28: , dan`), tapi `Pasal 68` adalah larangan penting yang hilang.
3. **Dua jalur retrieval berbeda.** `api.py`: `top_k=8` + query rewriting via Gemini + Gemini 2.0 Flash. `query.py`: `top_k=5` + Groq llama-3.3-70b. Eval ini tidak bisa mewakili keduanya sekaligus.

## Yang belum dievaluasi

- **Kualitas jawaban (faithfulness / grounding).** Eval ini hanya mengukur apakah pasal yang benar ikut terambil. Tidak mengukur apakah LLM menjawab sesuai pasal itu atau mengarang nomor pasal.
- **Retrieval embedding asli** dengan model dan index yang dipakai produksi.
- **Query rewriting** dari riwayat chat — tidak ada eval untuk pertanyaan lanjutan seperti "lalu bagaimana hitungannya?".
- **Out-of-scope query** — belum ada uji apakah sistem menolak pertanyaan di luar UU No. 13/2003.

## Prioritas perbaikan

1. Perbaiki `parser.py` supaya `Pasal 33` tidak menelan seluruh UU, lalu rebuild `parsed_uu_fixed.json` dan index.
2. Tangani pasal pendek: jangan buang `Pasal 68`; gabungkan dengan pasal terkait atau ubah ambang minimal dengan kontrol kualitas.
3. Samakan konfigurasi retrieval di `api.py` dan `query.py`.
4. Jalankan evaluasi embedding yang sebenarnya, lalu bandingkan dengan angka baseline ini.
5. Tambah evaluasi jawaban: apakah nomor pasal yang disebut LLM benar-benar ada di konteks.
