import ijson

path = "data/raw/ulasim/iett-hatlar.json"
output_path = "data/scripts/inspect_output.txt"

print("Başlıyor...")

with open(path, "rb") as f, open(output_path, "w", encoding="utf-8") as out:
    parser = ijson.parse(f)
    count = 0
    for prefix, event, value in parser:
        line = f"{prefix} | {event} | {value}\n"
        out.write(line)
        count += 1
        if count > 60:
            break

print(f"Bitti. {count} satır yazıldı: {output_path}")