import sqlite3
import json
import pandas as pd
import pdfplumber
import os

from collections import defaultdict


DB_PATH = "data/sehrimi_tani.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def insert_chunk(cursor, category, source_file, chunk_index, content):
    cursor.execute(
        """
        INSERT INTO documents
        (category, source_file, chunk_index, content)
        VALUES (?, ?, ?, ?)
        """,
        (category, source_file, chunk_index, content)
    )


def parse_number(value):
    """
    Sayısal değeri güvenli şekilde float'a çevirir.
    Örnek:
    9260.52  -> 9260.52
    '9260,52' -> 9260.52
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(" ", "")

    if not text:
        return None

    # Hem nokta hem virgül varsa Türkiye formatını dikkate al
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # 9.260,52 -> 9260.52
            text = text.replace(".", "").replace(",", ".")
        else:
            # 9,260.52 -> 9260.52
            text = text.replace(",", "")
    else:
        # 9260,52 -> 9260.52
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def ingest_ulasim(cursor):
    path = "data/raw/ulasim/hatlar-ozet.json"

    with open(path, encoding="utf-8") as f:
        routes = json.load(f)

    grouped = defaultdict(list)

    for route in routes:
        hat_adi = route.get("hat_adi")

        if hat_adi:
            grouped[hat_adi].append(route)

    idx = 0
    count = 0

    for hat_adi, segments in grouped.items():
        seen_pairs = set()
        pairs = []

        for segment in segments:
            hat_basi = segment.get("hat_basi", "")
            hat_sonu = segment.get("hat_sonu", "")

            pair = (hat_basi, hat_sonu)

            if hat_basi and hat_sonu and pair not in seen_pairs:
                seen_pairs.add(pair)
                pairs.append(f"{hat_basi} - {hat_sonu}")

        if not pairs:
            continue

        raw_uzunluk = next(
            (
                segment.get("uzunluk")
                for segment in segments
                if segment.get("uzunluk") is not None
            ),
            None
        )

        raw_sure = next(
            (
                segment.get("sure")
                for segment in segments
                if segment.get("sure") is not None
            ),
            None
        )

        durum = next(
            (
                segment.get("durum")
                for segment in segments
                if segment.get("durum") is not None
            ),
            None
        )

        uzunluk = parse_number(raw_uzunluk)
        sure = parse_number(raw_sure)

        parts = [
            f"Hat: {hat_adi}",
            "Guzergah: " + "; ".join(pairs[:10])
        ]

        # Ham verinin metre olduğu varsayılıyor
        if uzunluk is not None:
            uzunluk_km = uzunluk / 1000
            parts.append(f"Uzunluk: {uzunluk_km:.2f} km")

        # Ham verinin saniye olduğu varsayılıyor
        if sure is not None:
            sure_dakika = sure / 60
            parts.append(f"Süre: {sure_dakika:.2f} dakika")

        if durum is not None:
            parts.append(f"Durum: {durum}")

        content = ". ".join(parts) + "."

        insert_chunk(
            cursor,
            "ulasim",
            "hatlar-ozet.json",
            idx,
            content
        )

        idx += 1
        count += 1

    print(f"[ulasim] {count} chunk eklendi (hat bazında gruplandı).")


def ingest_xlsx(cursor, category, filepath):
    df = pd.read_excel(filepath)
    df = df.fillna("")

    count = 0
    idx = 0

    for _, row in df.iterrows():
        parts = [
            f"{column}: {row[column]}"
            for column in df.columns
            if str(row[column]).strip()
        ]

        if not parts:
            continue

        content = ". ".join(parts) + "."

        insert_chunk(
            cursor,
            category,
            os.path.basename(filepath),
            idx,
            content
        )

        idx += 1
        count += 1

    print(
        f"[{category}] {count} chunk eklendi "
        f"({os.path.basename(filepath)})."
    )


def ingest_csv(cursor, category, filepath):
    try:
        df = pd.read_csv(filepath, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(filepath, encoding="windows-1254")
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="latin1")

    df = df.fillna("")

    count = 0

    for index, row in df.iterrows():
        parts = [
            f"{column}: {row[column]}"
            for column in df.columns
            if str(row[column]).strip()
        ]

        if not parts:
            continue

        content = ". ".join(parts) + "."

        insert_chunk(
            cursor,
            category,
            os.path.basename(filepath),
            index,
            content
        )

        count += 1

    print(
        f"[{category}] {count} chunk eklendi "
        f"({os.path.basename(filepath)})."
    )


def ingest_pdf(cursor, category, filepath):
    count = 0

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()

            if not text or not text.strip():
                continue

            paragraphs = [
                paragraph.strip()
                for paragraph in text.split("\n\n")
                if paragraph.strip()
            ]

            if not paragraphs:
                paragraphs = [text.strip()]

            for paragraph_index, paragraph in enumerate(paragraphs):
                if len(paragraph) < 20:
                    continue

                chunk_index = page_num * 100 + paragraph_index

                insert_chunk(
                    cursor,
                    category,
                    os.path.basename(filepath),
                    chunk_index,
                    paragraph
                )

                count += 1

    print(
        f"[{category}] {count} chunk eklendi "
        f"({os.path.basename(filepath)})."
    )


if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()

    # Bu işlem mevcut chunk'ları ve embedding'leri siler.
    cursor.execute("DELETE FROM documents")

    ingest_ulasim(cursor)

    ingest_xlsx(
        cursor,
        "yesil_alan",
        "data/raw/yesil_alan/"
        "2022-park-bahce-ve-yeil-alanlar-dairesi-bakanl-verileri.xlsx"
    )

    ingest_xlsx(
        cursor,
        "atik",
        "data/raw/atik/"
        "cevre-hizmetlerine-gore-yllk-atk-miktar-2025.xlsx"
    )

    ingest_xlsx(
        cursor,
        "enerji_sarj",
        "data/raw/enerji_sarj/"
        "ibb-mudurlukleri-elektrik-enerjisi-uretim-miktarlar_aym-1.xlsx"
    )

    ingest_csv(
        cursor,
        "afet",
        "data/raw/afet/"
        "deprem-senaryosu-analiz-sonuclar.csv"
    )

    ingest_pdf(
        cursor,
        "hava_kalitesi",
        "data/raw/hava_kalitesi/"
        "kullanim_dokumani.pdf"
    )

    # Gürültü verisi henüz eklenmedi.
    # ingest_pdf(cursor, "gurultu", "data/raw/gurultu/ornek.pdf")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM documents")
    total = cursor.fetchone()[0]

    print(f"\nTOPLAM: {total} chunk veritabanında.")

    conn.close()