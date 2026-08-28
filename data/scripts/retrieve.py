import json
import sqlite3
from pathlib import Path

import numpy as np
from foundry_local_sdk import Configuration, FoundryLocalManager


# Proje kök dizininden bağımsız, dosyanın konumuna göre veritabanı yolu
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "sehrimi_tani.db"


# Foundry Local embedding modelini başlat
config = Configuration(app_name="Retrieve")
FoundryLocalManager.initialize(config)

manager = FoundryLocalManager.instance
model = manager.catalog.get_model("qwen3-embedding-0.6b")
model.download()
model.load()

embed_client = model.get_embedding_client()


def extract_vector(item):
    if isinstance(item, dict):
        if "embedding" in item:
            return item["embedding"]
        if "vector" in item:
            return item["vector"]

    if hasattr(item, "embedding"):
        return item.embedding

    if hasattr(item, "vector"):
        return item.vector

    return item


def embed_query(text):
    result = embed_client.generate_embeddings([text])
    items = result.data if hasattr(result, "data") else result

    vector = extract_vector(items[0])
    return np.asarray(vector, dtype=np.float32).reshape(-1)


def cosine_similarity(a, b):
    if a.size == 0 or b.size == 0:
        return 0.0

    if a.size != b.size:
        return 0.0

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def decode_embedding(value):
    if value is None:
        return None

    if isinstance(value, memoryview):
        value = value.tobytes()

    # SQLite BLOB formatı
    if isinstance(value, (bytes, bytearray)):
        if len(value) == 0:
            return None

        return np.frombuffer(value, dtype=np.float32).reshape(-1)

    # JSON metin formatı
    if isinstance(value, str):
        if not value.strip():
            return None

        vector = json.loads(value)
        return np.asarray(vector, dtype=np.float32).reshape(-1)

    return np.asarray(value, dtype=np.float32).reshape(-1)


def get_top_chunks(query, k=3, category=None):
    query_vec = embed_query(query)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        if category:
            cursor.execute(
                """
                SELECT id, category, source_file, content, embedding
                FROM documents
                WHERE category=?
                  AND embedding IS NOT NULL
                  AND length(embedding) > 0
                """,
                (category,),
            )
        else:
            cursor.execute(
                """
                SELECT id, category, source_file, content, embedding
                FROM documents
                WHERE embedding IS NOT NULL
                  AND length(embedding) > 0
                """
            )

        rows = cursor.fetchall()

    scored = []
    skipped = 0

    for row_id, cat, source, content, emb_blob in rows:
        try:
            emb_vec = decode_embedding(emb_blob)

            if emb_vec is None or emb_vec.size == 0:
                skipped += 1
                continue

            if emb_vec.size != query_vec.size:
                print(
                    f"Embedding boyutu uyumsuz: "
                    f"kayıt={emb_vec.size}, sorgu={query_vec.size}"
                )
                skipped += 1
                continue

            score = cosine_similarity(query_vec, emb_vec)
            scored.append((score, cat, source, content))

        except Exception as error:
            print(f"Kayıt atlandı: {error}")
            skipped += 1

    scored.sort(key=lambda item: item[0], reverse=True)

    print(f"Geçerli embedding sonucu: {len(scored)}")
    print(f"Atlanan kayıt: {skipped}")

    return scored[:k]


if __name__ == "__main__":
    test_query = "Arnavutköy'den Tuzla'ya nasıl giderim"

    try:
        print(f"Soru: {test_query}\n")

        results = get_top_chunks(test_query, k=3)

        if not results:
            print("Henüz geçerli embedding bulunamadı.")
        else:
            for score, category, source, content in results:
                print(f"[{score:.3f}] ({category} - {source})")
                print(content)
                print("---")

    finally:
        model.unload()