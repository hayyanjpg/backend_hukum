"""Evaluasi retrieval untuk backend_hukum tanpa API key.

Baseline BM25 dijalankan lokal terhadap parsed_uu_fixed.json. Filter panjang teks
< 50 sengaja sama dengan ingest.py, supaya korpus yang dievaluasi sama dengan
yang benar-benar di-upload ke Pinecone.

Cara jalan:
    python eval/retrieval_eval.py           # ringkas
    python eval/retrieval_eval.py --detail  # tampilkan miss per query

Untuk mengukur retrieval embedding asli (Pinecone + sentence-transformers),
lihat docs/EVALUATION.md. Script ini sengaja tidak menaruh angka embedding
yang tidak benar-benar diukur.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "parsed_uu_fixed.json"
QUERIES = ROOT / "eval" / "queries.jsonl"
MIN_LEN = 50  # sama dengan ingest.py

STOPWORDS = {
    "yang", "dan", "atau", "di", "ke", "dari", "untuk", "pada", "dengan",
    "adalah", "apa", "apakah", "bagaimana", "berapa", "boleh", "harus",
    "wajib", "tidak", "ini", "itu", "para", "oleh", "sebagai", "dalam",
    "jika", "saat", "ketika", "ada", "dapat", "mempunyai", "memiliki",
    "melakukan", "dilakukan", "menjadi", "bagi", "atas", "sesuai", "lain",
    # "jam", "hari", "bulan", "tahun" sengaja TIDAK dihapus: satuan waktu
    # itu pembeda nyata di UU ketenagakerjaan (mis. 7 jam/hari, 3 bulan).
}


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def load_corpus():
    with CORPUS.open(encoding="utf-8") as f:
        data = json.load(f)
    kept = [x for x in data if len(x["text"]) >= MIN_LEN]
    docs = []
    for x in kept:
        pasal = x["metadata"]["pasal"]
        docs.append({
            "id": x["id"],
            "pasal": pasal,
            "tokens": tokenize(x["text"]),
        })
    return data, docs


def load_queries():
    with QUERIES.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.n = len(docs)
        self.df = Counter()
        self.tf = []
        for d in docs:
            counts = Counter(d["tokens"])
            self.tf.append(counts)
            self.df.update(counts.keys())
        self.avgdl = sum(len(d["tokens"]) for d in docs) / max(self.n, 1)

    def score(self, query_tokens):
        scores = []
        for i, counts in enumerate(self.tf):
            dl = len(self.docs[i]["tokens"])
            total = 0.0
            for term in query_tokens:
                f = counts.get(term, 0)
                if not f or term not in self.df:
                    continue
                idf = math.log(1 + (self.n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                total += idf * (f * (self.k1 + 1)) / denom
            scores.append((total, i))
        scores.sort(reverse=True)
        return scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true", help="tampilkan misses per query")
    args = ap.parse_args()

    data, docs = load_corpus()
    queries = load_queries()
    indexable = {d["pasal"] for d in docs}
    bm25 = BM25(docs)

    ks = (1, 5, 8)
    hits = {k: 0 for k in ks}
    rr_total = 0.0
    missing_gold = []
    misses = []

    for q in queries:
        gold = set(q["gold"])
        available = gold & indexable
        if not available:
            missing_gold.append((q["id"], q["gold"]))

        ranked = bm25.score(tokenize(q["question"]))
        ranked_pasal = [docs[i]["pasal"] for _, i in ranked]

        for k in ks:
            if available & set(ranked_pasal[:k]):
                hits[k] += 1

        rank = next(
            (pos for pos, pasal in enumerate(ranked_pasal, 1) if pasal in available),
            None,
        )
        if rank:
            rr_total += 1.0 / rank
        misses.append({
            "id": q["id"],
            "gold": sorted(gold),
            "in_index": sorted(available),
            "top5": ranked_pasal[:5],
            "rank": rank,
        })

    total = len(queries)
    print(f"korpus: {len(data)} pasal, {len(docs)} ter-index (filter <{MIN_LEN} char)")
    print(f"query : {total}")
    print()
    for k in ks:
        print(f"hit@{k:<2}: {hits[k]}/{total} = {hits[k]/total:.1%}")
    print(f"MRR@10: {rr_total/total:.3f}")
    print(f"gold tidak ada di index: {len(missing_gold)} -> {missing_gold}")

    if args.detail:
        print("\nDetail per query:")
        for m in misses:
            status = "OK" if m["rank"] == 1 else (f"rank {m['rank']}" if m["rank"] else "MISS")
            print(f"  {m['id']} gold={','.join(m['gold'])} [{status}]")
            print(f"        top5: {m['top5']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
