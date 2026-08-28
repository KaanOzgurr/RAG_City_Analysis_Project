import sqlite3

conn = sqlite3.connect("data/sehrimi_tani.db")
cursor = conn.cursor()

# Herhangi bir ulasim kaydini alip ham halini görelim
cursor.execute("SELECT content FROM documents WHERE category='ulasim' LIMIT 5")
rows = cursor.fetchall()

for row in rows:
    print(repr(row[0]))
    print("---")

conn.close()