import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"query": "Arnavutkoyden Tuzlaya hangi hatla giderim"}
)

response.encoding = "utf-8"  # encoding'i acikca belirtiyoruz

data = response.json()
print(repr(data["answer"]))
print("---")
print(data["answer"])