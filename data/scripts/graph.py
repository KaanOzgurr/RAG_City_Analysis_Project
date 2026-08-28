from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from foundry_local_sdk import Configuration, FoundryLocalManager
import sqlite3
import numpy as np

DB_PATH = "data/sehrimi_tani.db"

# --- Foundry Local kurulumu ---
config = Configuration(app_name="SehrimiTaniGraph")
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

embed_model = manager.catalog.get_model("qwen3-embedding-0.6b")
embed_model.download()
embed_model.load()
embed_client = embed_model.get_embedding_client()

chat_model = manager.catalog.get_model("qwen2.5-1.5b")
chat_model.download()
chat_model.load()
chat_client = chat_model.get_chat_client()


# --- State tanimi ---
class GraphState(TypedDict):
    query: str
    category: Optional[str]
    chunks: List[dict]
    answer: str
    sources: List[str]


# --- Yardimci fonksiyonlar ---
def extract_vector(item):
    if hasattr(item, "embedding"):
        return item.embedding
    if hasattr(item, "vector"):
        return item.vector
    return item

def embed_query(text):
    result = embed_client.generate_embeddings([text])
    items = result.data if hasattr(result, "data") else result
    return np.array(extract_vector(items[0]), dtype=np.float32)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)


# --- Node 1: Router ---
def router_node(state: GraphState) -> GraphState:
    """Basit anahtar kelime tabanli kategori tespiti"""
    query_lower = state["query"].lower()

    keyword_map = {
    "ulasim": ["hat", "otobus", "otobüs", "metro", "iett", "durak", "guzergah", "güzergah", "ulasim", "ulaşım"],
    "atik": ["atik", "atık", "cop", "çöp", "geri donusum", "geri dönüşüm", "cevre", "çevre"],
    "afet": ["deprem", "afet", "toplanma", "acil"],
    "yesil_alan": ["park", "yesil alan", "yeşil alan", "bahce", "bahçe"],
    "hava_kalitesi": ["hava kalitesi", "aqi", "kirlilik"],
    "enerji_sarj": ["enerji", "sarj", "şarj", "elektrik"],
}

    detected = None
    for cat, keywords in keyword_map.items():
        if any(kw in query_lower for kw in keywords):
            detected = cat
            break

    state["category"] = detected
    return state


# --- Node 2: Retriever ---
def retriever_node(state: GraphState) -> GraphState:
    query_vec = embed_query(state["query"])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if state.get("category"):
        cursor.execute(
            "SELECT category, source_file, content, embedding FROM documents WHERE category=? AND embedding IS NOT NULL AND embedding != ''",
            (state["category"],)
        )
    else:
        cursor.execute("SELECT category, source_file, content, embedding FROM documents WHERE embedding IS NOT NULL AND embedding != ''")

    rows = cursor.fetchall()
    conn.close()

    scored = []
    for cat, source, content, emb_blob in rows:
        emb_vec = np.frombuffer(emb_blob, dtype=np.float32)
        score = cosine_similarity(query_vec, emb_vec)
        scored.append((score, cat, source, content))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]

    state["chunks"] = [{"category": c, "source": s, "content": ct, "score": float(sc)} for sc, c, s, ct in top]
    state["sources"] = [f"{c['source']} ({c['category']})" for c in state["chunks"]]
    return state


# --- Node 3: Generator ---
def generator_node(state: GraphState) -> GraphState:
    context = "\n\n".join([c["content"] for c in state["chunks"]])

    system_prompt = (
        "Sen Istanbul Buyuksehir Belediyesi bilgi asistanisin. "
        "SADECE asagida verilen baglami kullanarak cevap ver. "
        "Baglamda bilgi yoksa 'Bu konuda elimde bilgi yok' de. "
        "Kisa ve net cevap ver."
    )

    user_message = f"Baglam:\n{context}\n\nSoru: {state['query']}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    response = chat_client.complete_chat(messages)
    state["answer"] = response.choices[0].message.content
    return state


# --- Node 4: Fallback ---
def fallback_node(state: GraphState) -> GraphState:
    state["answer"] = "Bu konuda elimde yeterli bilgi yok. Lutfen sorunuzu farkli sekilde sormayi deneyin."
    state["sources"] = []
    return state


# --- Karar fonksiyonu: Generator mi Fallback mi ---
def should_generate_or_fallback(state: GraphState) -> str:
    if not state["chunks"]:
        return "fallback"

    best_score = state["chunks"][0]["score"]
    print(f"[DEBUG] Soru: {state['query'][:50]} | Skor: {best_score:.4f} | Kategori: {state.get('category')}")

    threshold = 0.35 if state.get("category") else 0.5

    if best_score < threshold:
        return "fallback"

    return "generator"


# --- Grafigi kur ---
graph = StateGraph(GraphState)
graph.add_node("router", router_node)
graph.add_node("retriever", retriever_node)
graph.add_node("generator", generator_node)
graph.add_node("fallback", fallback_node)

graph.set_entry_point("router")
graph.add_edge("router", "retriever")
graph.add_conditional_edges(
    "retriever",
    should_generate_or_fallback,
    {
        "generator": "generator",
        "fallback": "fallback"
    }
)
graph.add_edge("generator", END)
graph.add_edge("fallback", END)

app = graph.compile()


# --- Test ---
if __name__ == "__main__":
    test_queries = [
        "Arnavutköy'den Tuzla'ya hangi hatla giderim",
        "Ayın yüzeyinde kaç tane krater var"
    ]

    for q in test_queries:
        result = app.invoke({
            "query": q,
            "category": None,
            "chunks": [],
            "answer": "",
            "sources": []
        })

        print("=" * 50)
        print("SORU:", result["query"])
        print("TESPIT EDILEN KATEGORI:", result["category"])
        print("CEVAP:", result["answer"])
        print("KAYNAKLAR:", result["sources"])

    embed_model.unload()
    chat_model.unload()