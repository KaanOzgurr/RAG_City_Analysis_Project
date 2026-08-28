import requests

queries = [
    "İstanbul'da yıllık ne kadar atık toplanıyor",
    "Deprem toplanma alanları nerede",
    "Hava kalitesi nasıl ölçülüyor",
]

for q in queries:
    requests.post("http://localhost:8000/ask", json={"query": q}, timeout=60)