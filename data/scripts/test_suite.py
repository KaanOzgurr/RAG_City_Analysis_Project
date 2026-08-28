import requests
import json
import time

BASE_URL = "http://localhost:8000/ask"

test_cases = [
    # (soru, beklenen_kategori, cevaplanabilir_mi)
    ("Arnavutköy'den Tuzla'ya hangi hatla giderim", "ulasim", True),
    ("Kadıköy'den hangi otobüs hatları geçiyor", "ulasim", True),
    ("İstanbul'da yıllık ne kadar atık toplanıyor", "atik", True),
    ("Deprem toplanma alanları nerede", "afet", True),
    ("Park ve yeşil alan miktarı ne kadar", "yesil_alan", True),
    ("Hava kalitesi nasıl ölçülüyor", "hava_kalitesi", True),
    ("Güneş enerjisi santrallerinden ne kadar üretim var", "enerji_sarj", True),

    # Kasıtlı alakasız sorular - fallback tetiklenmeli
    ("Ayın yüzeyinde kaç tane krater var", None, False),
    ("En iyi pizza tarifi nedir", None, False),
    ("Python programlama dili ne zaman çıktı", None, False),
]

results = []

for query, expected_cat, should_answer in test_cases:
    start = time.time()
    try:
        response = requests.post(BASE_URL, json={"query": query}, timeout=120)
        response.encoding = "utf-8"
        data = response.json()
        elapsed = time.time() - start

        is_fallback = "elimde yeterli bilgi yok" in data["answer"]
        correct_behavior = (is_fallback and not should_answer) or (not is_fallback and should_answer)

        results.append({
            "soru": query,
            "beklenen_kategori": expected_cat,
            "tespit_edilen_kategori": data.get("category"),
            "cevap": data["answer"][:100] + "...",
            "fallback_mi": is_fallback,
            "dogru_davranis": correct_behavior,
            "sure_sn": round(elapsed, 2)
        })
    except Exception as e:
        results.append({"soru": query, "hata": str(e)})

print("\n" + "=" * 70)
for r in results:
    status = "✅" if r.get("dogru_davranis") else "❌"
    print(f"{status} [{r.get('sure_sn', '?')}s] {r['soru']}")
    print(f"   Kategori: {r.get('tespit_edilen_kategori')} | Fallback: {r.get('fallback_mi')}")
    print(f"   Cevap: {r.get('cevap')}")
    print("-" * 70)

correct = sum(1 for r in results if r.get("dogru_davranis"))
print(f"\nTOPLAM: {correct}/{len(test_cases)} dogru davranis")

with open("data/scripts/test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)