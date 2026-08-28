import sqlite3

conn = sqlite3.connect("data/sehrimi_tani.db")
cursor = conn.cursor()

cursor.execute("SELECT category, COUNT(*) FROM documents GROUP BY category")
print("=== Kategori bazinda sayilar ===")
for cat, cnt in cursor.fetchall():
    print(f"{cat}: {cnt}")

print("\n=== Ornek icerikler ===")
for cat in ["ulasim", "yesil_alan", "atik", "enerji_sarj", "afet"]:
    cursor.execute("SELECT content FROM documents WHERE category=? LIMIT 1", (cat,))
    row = cursor.fetchone()
    print(f"\n[{cat}]")
    print(row[0] if row else "VERI YOK")

conn.close()