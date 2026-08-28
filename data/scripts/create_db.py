import sqlite3
import os

db_path = "data/sehrimi_tani.db"

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    source_file TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON documents(category)")

cursor.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    value TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

conn.commit()
conn.close()

print(f"Veritabani olusturuldu/guncellendi: {db_path}")