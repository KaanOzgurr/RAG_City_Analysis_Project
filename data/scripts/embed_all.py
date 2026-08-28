import sqlite3
import numpy as np
import time

from foundry_local_sdk import Configuration, FoundryLocalManager


DB_PATH = "data/sehrimi_tani.db"

# Normal durumda 64 kayıt birlikte işlenecek
BATCH_SIZE = 64

# Her batch en fazla iki kez denenecek
MAX_RETRIES = 2


config = Configuration(app_name="EmbedAll")
FoundryLocalManager.initialize(config)

manager = FoundryLocalManager.instance
model = manager.catalog.get_model("qwen3-embedding-0.6b")

model.download()
model.load()

embed_client = model.get_embedding_client()


def extract_vector(item):
    """
    Foundry Local sonucundan embedding vektörünü çıkarır.
    """

    if isinstance(item, dict):
        if "embedding" in item:
            return item["embedding"]

        if "vector" in item:
            return item["vector"]

    if hasattr(item, "embedding"):
        return item.embedding

    if hasattr(item, "vector"):
        return item.vector

    if isinstance(item, (list, tuple)):
        return item

    raise ValueError(
        f"Vektor bulunamadi: {type(item)}"
    )


def generate_embeddings_with_retry(contents):
    """
    Bir batch embedding üretmeyi dener.
    Geçici hata olursa tekrar dener.
    """

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            result = embed_client.generate_embeddings(contents)

            items = (
                result.data
                if hasattr(result, "data")
                else result
            )

            if len(items) != len(contents):
                raise ValueError(
                    f"Beklenen embedding sayisi: {len(contents)}, "
                    f"gelen: {len(items)}"
                )

            return items

        except Exception as error:
            last_error = error

            wait_seconds = 2 ** attempt

            print(
                f"Batch hatasi "
                f"(deneme {attempt + 1}/{MAX_RETRIES}): {error}"
            )

            if attempt < MAX_RETRIES - 1:
                print(
                    f"{wait_seconds} saniye sonra tekrar deneniyor..."
                )
                time.sleep(wait_seconds)

    raise RuntimeError(
        f"Batch {MAX_RETRIES} denemede basarisiz oldu: "
        f"{last_error}"
    )


def generate_embeddings_adaptive(contents):
    """
    Büyük batch başarısız olursa otomatik olarak küçültür.

    Örnek:
    64 kayıt başarısız olursa:
    32 + 32 denenir.

    32 başarısız olursa:
    16 + 16 denenir.
    """

    try:
        return generate_embeddings_with_retry(contents)

    except Exception as error:
        batch_length = len(contents)

        # Tek kayıt da başarısız olursa üst seviyeye bildir
        if batch_length == 1:
            raise RuntimeError(
                f"Tek kayit embed edilemedi: {error}"
            )

        middle = batch_length // 2

        left_contents = contents[:middle]
        right_contents = contents[middle:]

        print(
            f"Batch {batch_length} kayit basarisiz oldu. "
            f"{len(left_contents)} + {len(right_contents)} "
            f"olarak bolunuyor..."
        )

        left_items = generate_embeddings_adaptive(
            left_contents
        )

        right_items = generate_embeddings_adaptive(
            right_contents
        )

        return left_items + right_items


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


cursor.execute("SELECT COUNT(*) FROM documents")
total_documents = cursor.fetchone()[0]


cursor.execute(
    """
    SELECT COUNT(*)
    FROM documents
    WHERE embedding IS NOT NULL
      AND length(embedding) > 0
    """
)
already_embedded = cursor.fetchone()[0]


remaining_documents = (
    total_documents - already_embedded
)


print(f"Toplam kayit: {total_documents}")
print(
    f"Daha once embed edilen: "
    f"{already_embedded}"
)
print(
    f"Kalan kayit: "
    f"{remaining_documents}"
)


processed = already_embedded
newly_processed = 0
start_time = time.time()


try:
    while True:
        """
        Hem NULL hem de boş BLOB kayıtlarını seç.
        Böylece daha önce hata almış kayıtlar da tekrar denenir.
        """

        cursor.execute(
            """
            SELECT id, content
            FROM documents
            WHERE embedding IS NULL
               OR length(embedding) = 0
            LIMIT ?
            """,
            (BATCH_SIZE,)
        )

        rows = cursor.fetchall()

        if not rows:
            break

        ids = [row[0] for row in rows]
        contents = [row[1] for row in rows]

        try:
            # Normalde 64 kayıt birlikte işlenir.
            # Hata olursa otomatik olarak küçültülür.
            items = generate_embeddings_adaptive(
                contents
            )

            if len(items) != len(rows):
                raise ValueError(
                    f"Sonuc sayisi uyusmuyor. "
                    f"Beklenen: {len(rows)}, "
                    f"Gelen: {len(items)}"
                )

            for doc_id, item in zip(ids, items):
                vector = extract_vector(item)

                vector_np = np.asarray(
                    vector,
                    dtype=np.float32
                ).reshape(-1)

                if vector_np.size == 0:
                    raise ValueError(
                        f"Bos vektor uretildi. "
                        f"Kayit ID: {doc_id}"
                    )

                cursor.execute(
                    """
                    UPDATE documents
                    SET embedding = ?
                    WHERE id = ?
                    """,
                    (
                        vector_np.tobytes(),
                        doc_id
                    )
                )

            # Her batch sonrasında kaydet
            conn.commit()

        except Exception as error:
            # Tamamlanan önceki batch'ler korunur.
            conn.rollback()

            print(
                f"\nEmbedding islemi durduruldu: {error}"
            )
            print(
                "Tamamlanan embedding'ler korundu."
            )
            print(
                "Scripti tekrar calistirarak "
                "devam edebilirsin."
            )

            raise

        processed += len(rows)
        newly_processed += len(rows)

        elapsed = time.time() - start_time

        rate = (
            newly_processed / elapsed
            if elapsed > 0
            else 0
        )

        remaining = total_documents - processed

        remaining_minutes = (
            remaining / rate / 60
            if rate > 0
            else 0
        )

        print(
            f"{processed}/{total_documents} islendi. "
            f"Hiz: {rate:.2f} kayit/sn. "
            f"Tahmini kalan sure: "
            f"{remaining_minutes:.1f} dk"
        )

finally:
    conn.close()
    model.unload()


print("TUM EMBEDDING ISLEMI TAMAMLANDI.")