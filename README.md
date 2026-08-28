# 🏙️RAG_City_Analysis_Project

**Istanbul Metropolitan Municipality Information Assistant — Offline RAG System**

An AI assistant contributing to UN SDG 11 (Sustainable Cities and Communities), running entirely offline, powered by Istanbul Metropolitan Municipality's (İBB) open data.

---

## 📋 Project Purpose

"Know My City" is a RAG (Retrieval-Augmented Generation) assistant that lets citizens get information about municipal services (transportation, waste management, disaster response, green spaces, air quality, energy) without needing an internet connection.

### Why Offline?

- **Reduces the digital divide** — works in areas with limited internet access
- **Critical in disaster scenarios** — provides access to life-saving information (e.g. earthquake assembly points) even during internet outages
- **Data privacy** — no query is ever sent to the cloud, everything runs on-device
- **Lower carbon footprint** — local inference consumes far less energy than large cloud servers

## 🎯 Contribution to SDG 11

| Sub-target                                   | Contribution                                            |
| -------------------------------------------- | ------------------------------------------------------- |
| 11.6 - Air quality and waste management      | Easy access to waste and air quality data               |
| 11.7 - Universal access to green/safe spaces | Queryable park and green space information              |
| 11.b - Disaster risk management              | Offline access to earthquake assembly point information |

## 🏗️ Architecture

```
[JS Frontend]
     ↓ fetch (HTTP)
[FastAPI Backend]
     ↓
[LangGraph Pipeline]
   Router → Retriever → (conditional branch) → Generator / Fallback
     ↓
[SQLite: documents table, including embeddings]
     ↓
[Foundry Local: qwen3-embedding-0.6b + qwen2.5-1.5b, fully offline]
```

### LangGraph Nodes

- **Router**: Keyword-based category detection (transportation, waste, disaster, green space, air quality, energy)
- **Retriever**: Embedding-based cosine similarity search, category-filterable
- **Generator**: Context-grounded answer generation using a Foundry Local chat model
- **Fallback**: A safety layer that prevents hallucination when similarity scores are low

## 🛠️ Tech Stack

- **Foundry Local** — offline model inference (embedding + chat)
- **LangGraph** — RAG pipeline orchestration
- **FastAPI** — backend API
- **SQLite** — vector + document storage
- **JavaScript (Vanilla)** — frontend UI
- **pandas, pdfplumber, ijson** — data processing

## 📊 Data Source

All data is sourced from the **İBB Open Data Portal** (data.ibb.gov.tr):

| Category       | Source                                | Chunk Count |
| -------------- | ------------------------------------- | ----------- |
| Transportation | İETT Bus Route Data                   | 771         |
| Waste          | Annual Waste Amounts                  | 9           |
| Disaster       | Earthquake Scenario Analysis          | 959         |
| Green Space    | Parks and Green Areas                 | 2           |
| Energy         | Electricity Production Amounts        | 28          |
| Air Quality    | Air Quality Web Service Documentation | 5           |

**Total: 1774 chunks, 1774 embedding vectors (1024-dimensional)**

## ✅ Test Results

A 10-question test suite achieved **10/10 correct behavior**:

- 6/6 category-specific questions answered correctly (with source citations)
- 3/3 out-of-scope questions (moon craters, pizza recipe, Python's release date) correctly rejected with no hallucination
- Average response time: ~10-15 seconds (can reach ~60 seconds for the air_quality category, see Known Limitations)

## ⚠️ Known Limitations

- Chunks in the **air_quality** category (PDF-derived) are longer than others, which can push response time up to ~60 seconds
- The **green_space** category has only 2 chunks, limiting data diversity
- The Router relies on simple keyword matching; complex or indirect questions may fail category detection

## 🚀 Setup

```bash
# Backend dependencies
pip install fastapi uvicorn langgraph langchain-core pandas openpyxl pdfplumber ijson

# Start the backend
python -m uvicorn backend.main:app --reload --port 8000 --reload-dir backend

# Start the frontend (separate terminal)
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500` in your browser.

## 🔮 Future Improvements

- Add the noise map (gürültü) category
- Compare answer quality with a larger chat model (e.g. phi-3.5-mini)
- Real pilot use with a local NGO or neighborhood administration (SDG 17 connection)
- Admin panel for live document updates

## 👤 Author

**Kaan Özgür**
GitHub: [@KaanOzgurr](https://github.com/KaanOzgurr)

Developed as the final project for the Microsoft Foundry Local Summer School program, with a focus on SDG 11.
