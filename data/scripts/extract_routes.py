import ijson
import json

path = "data/raw/ulasim/iett-hatlar.json"
output_path = "data/raw/ulasim/hatlar-ozet.json"

print("Basliyor...")

routes = []

with open(path, "rb") as f:
    features = ijson.items(f, "features.item")
    for i, feature in enumerate(features):
        props = feature.get("properties", {})

        route_info = {
            "hat_kodu": props.get("HAT_KODU", ""),
            "hat_adi": props.get("HAT_ADI", ""),
            "guzergah_adi": props.get("GUZERGAH_ADI", ""),
            "hat_basi": props.get("HAT_BASI", ""),
            "hat_sonu": props.get("HAT_SONU", ""),
            "uzunluk": props.get("UZUNLUK", ""),
            "sure": props.get("SURE", ""),
            "durum": props.get("DURUM", ""),
        }
        routes.append(route_info)

        if i % 500 == 0:
            print(f"{i} hat islendi...")

print(f"Toplam {len(routes)} hat bulundu.")

with open(output_path, "w", encoding="utf-8") as out:
    json.dump(routes, out, ensure_ascii=False, indent=2)

print(f"Ozet dosya kaydedildi: {output_path}")