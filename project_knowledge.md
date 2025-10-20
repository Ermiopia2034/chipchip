
# Project Knowledge: Agent Orchestration & Capabilities

## Capabilities (End-to-End)
- Natural chat in English/Amharic (and Amharic Latin) with context awareness.
- Product discovery: name/category search with live availability and price.
- Knowledge answers via RAG (storage, seasonality, selection, nutrition, recipes).
- Pricing insights with competitor averages and recommendation.
- Customer flows: registration and order creation (single/multi‑item) with totals and delivery details.
- Supplier flows: registration, add inventory (with image generation), stock check, delivery schedule, flash‑sale suggestions for expiring stock.

## Orchestration Overview
- Intent detection: lightweight heuristics first (registration, schedule ranges, flash‑sale, add_inventory parsing, customer orders), then LLM fallback.
- State machine: tracks flows (idle, registering, ordering, adding_inventory, querying) and governs transitions.
- Tool routing:
  - Deterministic for: check_stock, check_schedule (accepts date ranges), flash_sale_check (accepts days), add_inventory (structured inputs), get_customer_orders.
  - LLM tool‑calling for discovery/knowledge/pricing/order when free‑form.
- Session management: Redis stores session JSON (user, type, registered, context, history, language) with TTL; last N messages kept.
- Response loop: if LLM calls a tool, execute, append tool result, and ask LLM to finalize; otherwise return text directly.

## Tools (Function Declarations)
- `search_products(query)`
- `get_pricing_insights(product_name)`
- `rag_query(query, category?)`
- `create_order(items[{product_name,quantity_kg}], delivery_date, delivery_location)`
- `add_inventory(product_name, quantity_kg, price_per_unit, available_date, expiry_date?, generate_image)`
- `check_supplier_stock()`
- `get_supplier_schedule(start_date?, end_date?)`
- `suggest_flash_sale(days_threshold?)`
- `get_customer_orders(start_date?, end_date?, status?)`

## Data & Services
- PostgreSQL: products, users, inventory, orders(+items), competitor_pricing, transaction_history.
- Chroma (HTTP): collection `product_knowledge`; client‑side embeddings using `models/text-embedding-004` via Generative Language API.
- Redis: session store with TTL and history cap.
- Image generation: real model `models/gemini-2.5-flash-image`; saves to `/static/images` with correct file extension detection.

## Realtime Interface
- Socket.IO mounted at `/socket.io` with events: `connect`, `message`, `response`, `typing`, `app_error`.
- REST: create/fetch session endpoints; WebSocket fallback available.

## Logging & Settings
- Set `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `CHROMA_HOST/PORT`.
- Debug flags: `LOG_LEVEL=DEBUG`, `TRACE_TOOLS=1`, `DB_ECHO=1`.
- Logs include intents, tool I/O, LLM parsing, image mime/size/ext/signature.

## Prompt Test Checklist (Executed)
- RAG storage: "How should I store avocados?" → room temp until ripe; refrigerate 2–3 days.
- Registration (customer): "Register me as a customer… Abebe, 0911234567, Addis Ababa" → Registration complete.
- Order (single): "2 kg of Carrot… 2025‑10‑21 Addis Ababa" → Order confirmed, total 100.00 ETB.
- Product search: "Search for Tomato" → 50.00kg available @ 55.00 ETB/kg.
- Category search: "Search for vegetables" → list with availability/price; out‑of‑stock noted.
- Pricing insights: "Provide pricing insights for Tomato" → competitor averages, historical price, recommendation.
- Registration (supplier): "Register me as a supplier… Hana, 0912345678…" → Registration complete.
- Add inventory (no image): Tomato 50kg @ 55 ETB/kg, dates → Inventory added.
- Supplier stock: "Show my current inventory" → lists Tomato with qty/price/dates.
- Supplier schedule: "Show my delivery schedule this week/next week" → none scheduled (no confirmed orders).
- Flash‑sale: "Any expiring inventory in next 3 days?" → none.
- Orders (multi‑item): "1 kg Tomato + 2 kg Carrot… 2025‑10‑22" → Order confirmed, total 155.00 ETB.
- Customer orders: "Show my orders this week/next week" → lists pending order with items.
- RAG seasonality: "When are avocados in peak season?" → Sep–Nov.
- Add inventory with image: Mango… generate image → Image saved at `/static/images/...` and renders in browser.

---

# RAG Quick Guide

## What It Does
- Stores product knowledge snippets in a Chroma vector database for semantic retrieval.
- Uses Google Generative AI embeddings (`models/text-embedding-004`) via `google-generativeai` through Chroma’s embedding function.
- Ingestion source: `data/product_knowledge_base.csv` (columns: `product_name, category, content, embedding_text, created_at`).
- Backend integration: `backend/app/services/rag_service.py` creates/uses collection `product_knowledge` over HTTP (`CHROMA_HOST`, `CHROMA_PORT`).

## End-to-End Ingestion & Semantic Read (DB + Chroma)

Prerequisites:
- Ensure `.env` has `GOOGLE_API_KEY` or `GEMINI_API_KEY` set (AI Studio key).
- Services up: `docker compose up -d postgres redis chroma backend`

1) Initialize PostgreSQL schema
- `docker compose exec backend python scripts/init_db.py`

2) Load synthetic dataset (products, competitor pricing, transactions)
- `docker compose exec backend python scripts/load_dataset.py`

3) Ingest knowledge base into Chroma (idempotent)
- `docker compose exec backend python -c "from scripts.load_dataset import ingest_knowledge_base; ingest_knowledge_base('/data/product_knowledge_base.csv')"`

4) Validate database
- Transactions count (expected ≈ 52,427):
  - `docker compose exec -T postgres psql -U postgres -d horticulture -c "SELECT COUNT(*) FROM transaction_history;"`
- Competitor pricing count (expected ≈ 14,616):
  - `docker compose exec -T postgres psql -U postgres -d horticulture -c "SELECT COUNT(*) FROM competitor_pricing;"`
- Quick product peek:
  - `docker compose exec -T postgres psql -U postgres -d horticulture -c "SELECT product_id, product_name FROM products ORDER BY product_name LIMIT 10;"`

5) Validate Chroma and run semantic searches
- Count knowledge base docs (expect ~57):
  - `docker compose exec -T backend python - <<'PY'
from app.services.rag_service import VectorDBService
s = VectorDBService()
print('KB doc count:', s.collection.count())
PY`
- Basic semantic search (top 3):
  - `docker compose exec -T backend python - <<'PY'
from app.services.rag_service import VectorDBService
s = VectorDBService()
r = s.semantic_search('storage', 3)
for doc, meta, dist in zip(r['documents'][0], r['metadatas'][0], r['distances'][0]):
    print(f"{dist:.3f} | {meta['product_name']} [{meta['category']}] | {doc[:120]}")
PY`
- Filtered search (storage only):
  - `docker compose exec -T backend python - <<'PY'
from app.services.rag_service import VectorDBService
s = VectorDBService()
r = s.semantic_search('keep apples fresh', 5, category='storage')
for doc, meta, dist in zip(r['documents'][0], r['metadatas'][0], r['distances'][0]):
    print(f"{dist:.3f} | {meta['product_name']} [{meta['category']}]\n  ", doc[:160])
PY`

## Retrieval Flow
- Embed the user query with the same embedding model.
- Query Chroma for top-K nearest documents; optional filter by `category`.
- Results include `documents`, `metadatas` (`product_name`, `category`), and `distances` (lower is better, cosine space).

## Runtime Commands
- Start services (backend + Chroma):
  - `docker compose up -d chroma backend`
- Health check (backend):
  - `curl -sS http://localhost:8005/health`
- Ingest KB only (idempotent, safe to re-run):
  - `docker compose exec backend python -c "from scripts.load_dataset import ingest_knowledge_base; ingest_knowledge_base('/data/product_knowledge_base.csv')"`
- Verify count and a sample search:
  - `docker compose exec backend python -c "from app.services.rag_service import VectorDBService; s=VectorDBService(); print(len(s.collection.get()['ids']))"`
  - `docker compose exec backend python -c "from app.services.rag_service import VectorDBService; s=VectorDBService(); print(s.semantic_search('storage', 3))"`

## Add Or Update Entries
- Edit `data/product_knowledge_base.csv` and add a row:
  - `product_name`: e.g., `Apple`
  - `category`: one of `storage|selection|nutrition|recipes|seasonality|general` (project uses these buckets)
  - `content`: human-readable text
  - `embedding_text`: a concise, embedding-ready string (e.g., `Apple storage: …`)
  - `created_at`: timestamp (ISO or `YYYY-MM-DD HH:MM:SS`)
- Re-ingest to update the vector DB:
  - `docker compose exec backend python -c "from scripts.load_dataset import ingest_knowledge_base; ingest_knowledge_base('/data/product_knowledge_base.csv')"`
- Notes:
  - Re-ingest replaces existing KB IDs; safe to run after edits.
  - Keep `embedding_text` explicit and topical for best retrieval.

## Testing Queries
- Quick multi-query check:
  - `docker compose exec -T backend python - <<'PY'
from app.services.rag_service import VectorDBService
s = VectorDBService()
queries = [
  "storage", "store tomatoes", "store milk", "shelf life of potato", "keep apples fresh"
]
for q in queries:
    r = s.semantic_search(q, 3)
    print("---", q)
    for doc, meta, dist in zip(r['documents'][0], r['metadatas'][0], r['distances'][0]):
        print(f"{dist:.3f}", meta, "|", doc[:90])
PY`
- Filter by category (optional):
  - `docker compose exec -T backend python - <<'PY'
from app.services.rag_service import VectorDBService
s = VectorDBService()
print(s.semantic_search('keep apples fresh', 5, category='storage'))
PY`

## Requirements & Troubleshooting
- Set `GEMINI_API_KEY` in `.env` for embeddings. Ensure outbound network access and that the API key’s IP restrictions allow your host egress.
- If your key is IP-restricted, add the server IP in Google Console. As a temporary fallback (no embeddings, degraded search):
  - `docker compose exec -e GEMINI_API_KEY= backend python -c "from scripts.load_dataset import ingest_knowledge_base; ingest_knowledge_base('/data/product_knowledge_base.csv')"`
- Ensure services are running: `docker compose ps`. Chroma listens on `chroma:8000` inside the network (host port `8006`).

## Current Backend Integrations
- LLM: `gemini-2.5-pro` with function calling; tools registered: `search_products`, `get_pricing_insights`, `rag_query`, `create_order`, `add_inventory`, `check_supplier_stock`, `get_supplier_schedule`, `suggest_flash_sale`. Prompt at `backend/app/prompts/system_prompt.py`.
- RAG: Chroma HTTP client with client-side embeddings via Generative Language v1 using API key header; default top-K from `RAG_TOP_K`.
- DB: Async SQLAlchemy (`asyncpg`) aligned to schema; pricing recommendation = farm average + 10% (fallback to historical average).
- Sessions: Redis at `REDIS_URL` with TTL `SESSION_TTL`; conversation history capped by `MAX_CONVERSATION_HISTORY`.
- Images: Real image generation via `models/gemini-2.5-flash-image`; saves to `/static/images/{filename}` with correct extension; on failure, inventory is added and response includes "Image generation failed." (no placeholders).
