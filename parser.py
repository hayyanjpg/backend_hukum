import re
import json

def parse_uu_smart(file_path):
    
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    text = " ".join(raw_text.split())

    # Pola: Mencari "Pasal <angka>"
    tokens = re.split(r'(Pasal\s+\d+)', text)

    parsed_data = []
    
    # Buffer untuk menyimpan teks sementara
    current_pasal_num = 0
    current_header = ""
    current_content = tokens[0] # Ambil preamble

    # Loop token (mulai index 1 karena 0 adalah preamble)
    # Token ganjil = "Pasal X", Token genap = Isi teks
    for i in range(1, len(tokens), 2):
        header_candidate = tokens[i]      # Contoh: "Pasal 5"
        content_candidate = tokens[i+1]   # Contoh: "Setiap tenaga kerja..."

        # Ekstrak angka dari "Pasal X"
        match_num = re.search(r'\d+', header_candidate)
        if match_num:
            num = int(match_num.group())

            # --- LOGIKA KUNCI: Sequential Check ---
            # Jika angka ini > angka pasal terakhir, berarti ini Pasal BARU (Header)
            # Kecuali jika selisihnya terlalu jauh (misal loncat dari 1 ke 100), itu aneh (opsional check)
            if num > current_pasal_num:
                
                # 1. Simpan pasal SEBELUMNYA ke list (jika ada header)
                if current_header:
                    parsed_data.append({
                        "id": current_header.lower().replace(" ", "_"),
                        "metadata": {
                            "source": "UU No 13 Tahun 2003",
                            "pasal": current_header
                        },
                        "text": f"{current_header}: {current_content.strip()}"
                    })

                # 2. Reset untuk Pasal BARU ini
                current_pasal_num = num
                current_header = header_candidate
                current_content = content_candidate
            
            else:
                # Jika angka ini <= angka terakhir, berarti ini REFERENSI/SITASI di dalam teks
                # Contoh: Lagi di Pasal 160, ketemu teks "...sesuai Pasal 156..."
                # Jangan di-split! Gabungkan ke konten pasal yang sedang aktif.
                current_content += f" {header_candidate} {content_candidate}"
        
    # Jangan lupa simpan pasal TERAKHIR
    if current_header:
        parsed_data.append({
            "id": current_header.lower().replace(" ", "_"),
            "metadata": {
                "source": "UU No 13 Tahun 2003",
                "pasal": current_header
            },
            "text": f"{current_header}: {current_content.strip()}"
        })

    return parsed_data

# EKSEKUSI
try:
    data = parse_uu_smart('uu_naker.txt')
    
    # Simpan
    output_filename = 'parsed_uu_fixed.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"DONE. Disimpan ke {output_filename}")
    print(f"Total Pasal terdeteksi: {len(data)}")
    
    # Cek Pasal 156 (Pesangon) - Harus 1 blok utuh
    p156 = next((item for item in data if item["metadata"]["pasal"] == "Pasal 156"), None)
    if p156:
        print("\n--- Pengecekan Pasal 156 ---")
        print(f"Panjang Karakter: {len(p156['text'])}")
        print("Snippet Awal:", p156['text'][:100])
        print("Snippet Akhir:", p156['text'][-100:])
        print("(Jika panjang karakter > 2000, kemungkinan besar sudah benar)")
    else:
        print("Pasal 156 tidak ditemukan (Error)")

except FileNotFoundError:
    print("File uu_naker.txt hilang.")