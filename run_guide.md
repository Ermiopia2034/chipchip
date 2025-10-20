# Run Guide (Setup → Load DB → Enhance Data)

This guide lists copy-paste commands to get the app running, load the dataset, and enhance the loaded data by adding product categories. It is concise and avoids optional steps unless noted.

## 1) Clone and prepare env

```bash
git clone https://github.com/Ermiopia2034/chipchip.git
cd chipchip

# Prepare environment
cp .env.example .env
# Set at minimum your AI key (needed for RAG/KB embeddings)
sed -i "s/^GEMINI_API_KEY=.*/GEMINI_API_KEY=YOUR_KEY_HERE/" .env
```

## 2) Start services (Docker Compose)

```bash
docker compose up -d --build
```

Services (host ports):
- Frontend http://localhost:3005
- Backend http://localhost:8005
- Postgres localhost:5437
- Redis localhost:6384
- Chroma localhost:8006

## 3) Initialize database schema

```bash
docker compose exec backend python scripts/init_db.py
```

## 4) Load dataset (products, competitor pricing, transactions, KB)

```bash
# Ensure the two files exist (already in repo under ./data):
#  - data/synthetic_horticulture_dataset.xlsx
#  - data/product_knowledge_base.csv

docker compose exec backend python scripts/load_dataset.py
```

Notes:
- This script upserts products and loads competitor pricing + transaction history.
- If `GEMINI_API_KEY` is set, it also ingests the knowledge base into Chroma (RAG).

## 5) Enhance data: set categories for loaded products

Set `products.category` exactly for the 24 loaded product names (idempotent):

```bash
docker compose exec -T postgres psql -U postgres -d horticulture <<'SQL'
UPDATE products AS p
SET category = c.category
FROM (VALUES
  ('Apple','fruits'),
  ('Avocado','fruits'),
  ('Banana','fruits'),
  ('Beetroot','vegetables'),
  ('Bell Pepper','vegetables'),
  ('Butter','dairy'),
  ('Carrot','vegetables'),
  ('Cheese (Ayib)','dairy'),
  ('Cream','dairy'),
  ('Cucumber','vegetables'),
  ('Garlic','vegetables'),
  ('Green Chili (ስታርታ)','vegetables'),
  ('Lettuce','vegetables'),
  ('Mango','fruits'),
  ('Milk','dairy'),
  ('Orange','fruits'),
  ('Papaya','fruits'),
  ('Potato','vegetables'),
  ('Red Onion (ሃበሻ)','vegetables'),
  ('Spinach','vegetables'),
  ('Sweet Potato','vegetables'),
  ('Tomato','vegetables'),
  ('White Cabbage','vegetables'),
  ('Yogurt','dairy')
) AS c(name, category)
WHERE p.product_name = c.name;
SQL
```

## 6) Optional checks

```bash
# Validate dataset + KB counts
docker compose exec backend python scripts/validate_data.py

# Re‑ingest KB only (safe to re‑run)
docker compose exec backend \
  python -c "from scripts.load_dataset import ingest_knowledge_base; ingest_knowledge_base('/data/product_knowledge_base.csv')"
```

## 7) Open the app

```bash
xdg-open http://localhost:3005 || open http://localhost:3005 || echo "Open http://localhost:3005"
```

Backend API docs (if enabled): http://localhost:8005/docs

## Notes

- All commands reflect the documented architecture and progress notes in:
  - `architecture_document.md`
  - `project_knowledge.md`
  - `progress_report.md`
  - `production_guide.md`
