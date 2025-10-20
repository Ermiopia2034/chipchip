# Implementation Plan: Ethiopian Horticulture E-commerce Chatbot

**Project Duration**: 10-12 days  
**Reference Document**: AI Architecture Design (created above)  
**Development Approach**: Sequential milestone completion with testing at each stage

---

## 🎯 Project Overview

Build an MVP bilingual chatbot for Ethiopian horticulture e-commerce with dual customer/supplier workflows, RAG-powered knowledge base, and dynamic pricing insights. The system must be containerized, deployable with one command, and ready for demonstration.

---

## 📋 Milestone 1: Foundation & Environment Setup
**Duration**: Day 1  
**Objective**: Establish project structure and development environment

### 1.1 Project Initialization

**Create directory structure:**
```
horticulture-chatbot/
├── frontend/
├── backend/
├── data/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

**Setup environment configuration:**
- Create `.env.example` with required variables:
  - `GEMINI_API_KEY` (get from Google AI Studio)
  - `DATABASE_URL`
  - `REDIS_URL`
  - `CHROMA_URL`
  - `ENVIRONMENT=development`
  
**Initialize Git repository:**
- Add `.gitignore` for Python, Node.js, environment files
- Exclude `data/`, `.env`, `__pycache__`, `node_modules/`

### 1.2 Docker Configuration

**Create `docker-compose.yml`:**
- Define 5 services: frontend, backend, postgres, redis, chroma
- Frontend: Port 3000, depends on backend
- Backend: Port 8000, depends on postgres/redis/chroma, mount volume for hot reload
- PostgreSQL 15: Port 5432, persistent volume, set initial credentials
- Redis 7 Alpine: Port 6379, persistent volume
- Chroma latest: Port 8001, persistent volume

**Service configurations:**
- Set restart policies to `unless-stopped`
- Configure health checks for postgres and redis
- Setup network bridge for inter-service communication
- Define named volumes for data persistence

### 1.3 Backend Project Setup

**Install FastAPI stack:**
- Create `backend/requirements.txt` with:
  - fastapi==0.104.1
  - uvicorn[standard]==0.24.0
  - python-socketio==5.10.0
  - google-generativeai==0.3.2
  - chromadb==0.4.18
  - psycopg2-binary==2.9.9
  - sqlalchemy==2.0.23
  - redis==5.0.1
  - pydantic==2.5.0
  - python-dotenv==1.0.0
  - pandas==2.1.3
  - openpyxl==3.1.2

**Create backend Dockerfile:**
- Base image: python:3.11-slim
- Set working directory to `/app`
- Copy requirements and install dependencies
- Copy application code
- Expose port 8000
- Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

**Initialize backend structure:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── orchestrator/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── prompts/
├── scripts/
│   ├── init_db.py
│   └── load_dataset.py
├── tests/
├── requirements.txt
└── Dockerfile
```

### 1.4 Frontend Project Setup

**Initialize Next.js project:**
- Use Next.js 14 with App Router and TypeScript
- Install dependencies:
  - socket.io-client
  - tailwindcss
  - @headlessui/react (for UI components)
  - lucide-react (for icons)

**Create frontend Dockerfile:**
- Base image: node:20-alpine
- Set working directory to `/app`
- Copy package files and install dependencies
- Copy application code
- Expose port 3000
- Command: `npm run dev` for development

**Initialize frontend structure:**
```
frontend/
├── app/
│   ├── page.tsx
│   ├── chat/
│   ├── layout.tsx
│   └── globals.css
├── components/
├── lib/
├── public/
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── Dockerfile
```

### Deliverables
- ✅ Complete project structure
- ✅ Docker Compose configuration tested
- ✅ All services start successfully
- ✅ Backend and frontend skeleton projects initialized
- ✅ Environment variables documented

### Success Criteria
- Run `docker-compose up` and all 5 services start without errors
- Access backend health check at `http://localhost:8000/health`
- Access frontend at `http://localhost:3000`
- Redis and PostgreSQL accept connections

---

## 📋 Milestone 2: Data Layer Implementation
**Duration**: Days 2-3  
**Objective**: Setup databases, load synthetic data, and prepare RAG knowledge base

### 2.1 PostgreSQL Schema Design

**Create database initialization script (`scripts/init_db.py`):**

**Users table:**
- `user_id`: UUID primary key (generate with uuid_generate_v4())
- `phone`: VARCHAR(15) unique, not null (Ethiopian format: 09XXXXXXXX)
- `name`: VARCHAR(100)
- `user_type`: VARCHAR(20) with CHECK constraint ('customer' or 'supplier')
- `default_location`: VARCHAR(100)
- `created_at`: TIMESTAMP default NOW()
- Index on phone for fast lookup

**Products table:**
- `product_id`: SERIAL primary key
- `product_name`: VARCHAR(100) not null, unique
- `category`: VARCHAR(50) (vegetables/fruits/dairy)
- `unit`: VARCHAR(20) (kg/liters)
- Seed with 24 products from dataset (15 horticulture + 5 dairy + 4 fruits)

**Inventory table:**
- `inventory_id`: SERIAL primary key
- `supplier_id`: UUID foreign key to users(user_id) ON DELETE CASCADE
- `product_id`: INT foreign key to products(product_id)
- `quantity_kg`: DECIMAL(10,2) not null
- `price_per_unit`: DECIMAL(10,2) not null
- `available_date`: DATE not null
- `expiry_date`: DATE nullable
- `image_url`: TEXT nullable
- `created_at`: TIMESTAMP default NOW()
- `status`: VARCHAR(20) default 'active' (active/sold_out/expired)
- Composite index on (supplier_id, product_id, status)

**Orders table:**
- `order_id`: UUID primary key
- `customer_id`: UUID foreign key to users(user_id)
- `supplier_id`: UUID foreign key to users(user_id) nullable (assigned when order accepted)
- `order_date`: TIMESTAMP default NOW()
- `delivery_date`: DATE not null
- `delivery_location`: VARCHAR(200) not null
- `total_amount`: DECIMAL(10,2) not null
- `status`: VARCHAR(20) default 'pending' (pending/confirmed/delivered/cancelled)
- `payment_method`: VARCHAR(20) default 'COD'
- `created_at`: TIMESTAMP default NOW()
- Index on customer_id and status

**Order_items table:**
- `item_id`: SERIAL primary key
- `order_id`: UUID foreign key to orders(order_id) ON DELETE CASCADE
- `product_id`: INT foreign key to products(product_id)
- `quantity_kg`: DECIMAL(10,2) not null
- `price_per_unit`: DECIMAL(10,2) not null
- `subtotal`: DECIMAL(10,2) generated always as (quantity_kg * price_per_unit)

**Competitor_pricing table:**
- `id`: SERIAL primary key
- `date`: DATE not null
- `product_id`: INT foreign key to products(product_id)
- `product_name`: VARCHAR(100)
- `price`: DECIMAL(10,2) not null
- `source_market_type`: VARCHAR(50) (Farm/Supermarket/Distribution Center)
- `location_detail`: VARCHAR(100)
- Composite index on (product_id, date, source_market_type) for fast pricing queries

**Transaction_history table:**
- `transaction_id`: SERIAL primary key
- `order_date`: TIMESTAMP not null
- `product_id`: INT foreign key to products(product_id)
- `product_name`: VARCHAR(100)
- `quantity_ordered`: DECIMAL(10,2)
- `price_per_unit`: DECIMAL(10,2)
- `order_total_amount`: DECIMAL(10,2)
- Index on (product_id, order_date) for historical analysis

**Enable UUID extension:**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 2.2 Data Loading Script

**Create `scripts/load_dataset.py`:**

**Load Products:**
- Read unique products from `data/synthetic_horticulture_dataset.xlsx` - Transactions sheet
- Extract product_name, unit
- Map categories (vegetables/fruits/dairy) based on product name
- Insert into products table with UPSERT logic (ON CONFLICT DO NOTHING)

**Load Competitor Pricing:**
- Read `Competitor_Pricing` sheet
- Map product_name to product_id from products table
- Bulk insert all 14,616 records using batch inserts (chunks of 1000)
- Handle duplicate dates by taking latest entry

**Load Transaction History:**
- Read `Transactions` sheet
- Map product_name to product_id
- Insert all 52,427 transactions using batch inserts
- This data is for analytics/insights only, not active orders

**Validation checks:**
- Verify record counts match expected (52,427 transactions, 14,616 pricing points)
- Check for null values in critical fields
- Validate date ranges (Jan 2024 - Aug 2025)
- Log any skipped/errored records

### 2.3 Vector Database Setup

**Create Chroma initialization in backend (`app/services/rag_service.py`):**

**Initialize Chroma client:**
- Use PersistentClient pointing to `/chroma/chroma` volume
- Create collection named `product_knowledge`
- Use GoogleGenerativeAiEmbeddingFunction with Gemini API key
- Set collection metadata: `{"hnsw:space": "cosine"}`

**Ingest knowledge base:**
- Read `data/product_knowledge_base.csv`
- For each of 56 entries:
  - Document text: `embedding_text` column (pre-formatted for embeddings)
  - Metadata: `product_name`, `category` (storage/nutrition/recipes/selection/seasonality)
  - ID: `kb_{index}` (e.g., kb_0, kb_1, ...)
- Batch insert all 56 documents in single API call

**Implement semantic search method:**
- Input: user query string
- Process: 
  - Clean and normalize query
  - Use Chroma's query method with query_texts parameter
  - Return top 3 results by default (configurable)
- Output: List of (document_text, metadata, similarity_score)

**Add category filtering:**
- Allow searches filtered by category (e.g., only nutrition facts)
- Use Chroma's `where` filter: `{"category": "nutrition"}`

### 2.4 Redis Session Structure

**Define session schema in `app/models/schemas.py`:**

**Session data structure (JSON stored as string):**
```python
{
    "session_id": "uuid-v4",
    "user_id": "uuid or null",
    "user_type": "customer|supplier|unknown",
    "registered": boolean,
    "phone": "string or null",
    "name": "string or null",
    "default_location": "string or null",
    "context": {
        "current_flow": "registration|ordering|inquiry|inventory_mgmt|idle",
        "pending_order": {
            "items": [{"product_name": str, "quantity_kg": float}],
            "delivery_date": "date or null",
            "delivery_location": "string or null",
            "total_amount": float
        },
        "pending_inventory": {
            "product_name": str,
            "quantity_kg": float,
            "available_date": "date or null",
            "expiry_date": "date or null",
            "price_per_unit": float
        },
        "last_intent": "string",
        "awaiting_confirmation": boolean
    },
    "conversation_history": [
        {"role": "user|assistant", "content": str, "timestamp": str}
    ],
    "language": "en|am|amglish|auto",
    "created_at": "ISO timestamp",
    "last_active": "ISO timestamp"
}
```

**TTL policy:**
- Active sessions: 24 hours
- Extend TTL on every user message
- Cleanup: Redis handles automatic expiration

**Key naming convention:**
- Session data: `session:{session_id}`
- User lookup: `user_sessions:{user_id}` → Set of session_ids
- Active sessions count: `active_sessions` → Redis sorted set with scores as timestamps

### Deliverables
- ✅ PostgreSQL database with all 7 tables created
- ✅ Synthetic dataset loaded (52,427 transactions, 14,616 pricing points)
- ✅ Chroma vector DB initialized with 56 knowledge entries
- ✅ Redis session structure documented and tested
- ✅ Database connection utilities implemented

### Success Criteria
- Run `docker-compose exec backend python scripts/init_db.py` successfully
- Run `docker-compose exec backend python scripts/load_dataset.py` successfully
- Query PostgreSQL: `SELECT COUNT(*) FROM transaction_history` returns 52,427
- Query Chroma: Search for "storage" returns relevant documents
- Redis connection test: Set and retrieve session data

---

## 📋 Milestone 3: Backend Core Services
**Duration**: Days 4-5  
**Objective**: Build foundational services for LLM, database operations, RAG, and image generation

### 3.1 Configuration Management

**Create `app/config.py`:**

**Load environment variables:**
- `GEMINI_API_KEY`: Required, raise error if missing
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CHROMA_HOST`: Default "chroma", port 8000
- `ENVIRONMENT`: development/production
- `LOG_LEVEL`: INFO/DEBUG
- `SESSION_TTL`: 86400 (24 hours in seconds)
- `MAX_CONVERSATION_HISTORY`: 20 messages
- `RAG_TOP_K`: 3 results

**Validation:**
- Check all required variables on startup
- Fail fast with clear error messages if misconfigured
- Log configuration (mask sensitive values)

### 3.2 Database Service Layer

**Create `app/services/db_service.py`:**

**SQLAlchemy setup:**
- Create async engine using `create_async_engine` with PostgreSQL URL
- Use `AsyncSession` for all operations
- Define SQLAlchemy ORM models matching database schema from Milestone 2.1
- Implement connection pooling (pool_size=10, max_overflow=20)

**Core database operations:**

**User operations:**
- `create_user(phone, name, user_type, location)`: Insert new user, return user_id
- `get_user_by_phone(phone)`: Lookup user, return User object or None
- `update_user(user_id, **kwargs)`: Update user fields

**Product operations:**
- `get_all_products()`: Return list of all 24 products with category
- `get_product_by_name(name)`: Case-insensitive search, return Product or None
- `search_products(query)`: Fuzzy search by name using ILIKE

**Inventory operations:**
- `add_inventory(supplier_id, product_id, quantity, price, available_date, expiry_date, image_url)`: Insert inventory
- `get_available_inventory(product_id)`: Get active inventory for product (status='active', available_date <= today)
- `get_supplier_inventory(supplier_id)`: All inventory items for supplier with product names
- `check_expiring_inventory(supplier_id, days_threshold=3)`: Find inventory expiring within N days
- `update_inventory_status(inventory_id, status)`: Mark as sold_out/expired

**Order operations:**
- `create_order(customer_id, delivery_date, delivery_location, total_amount)`: Insert order, return order_id
- `add_order_items(order_id, items_list)`: Bulk insert order items [{product_id, quantity_kg, price_per_unit}, ...]
- `get_customer_orders(customer_id, status)`: Retrieve orders with items joined
- `get_supplier_pending_orders(supplier_id)`: Orders awaiting supplier confirmation
- `update_order_status(order_id, status, supplier_id)`: Update order status
- `get_supplier_schedule(supplier_id, start_date, end_date)`: Confirmed orders in date range

**Pricing insights operations:**
- `get_competitor_prices(product_id, days_back=30)`: Recent competitor prices grouped by market type
- `get_average_competitor_price(product_id, market_type, days_back=30)`: Calculate average
- `get_historical_transaction_prices(product_id, days_back=60)`: Past selling prices
- `calculate_pricing_recommendation(product_id)`: Algorithm:
  1. Get avg prices from all 3 market types (Farm, Supermarket, Distribution)
  2. Get historical transaction avg
  3. Recommend: Farm price + 10% (competitive but profitable)
  4. Return dict with: {recommended, farm_avg, supermarket_avg, distribution_avg, historical_avg}

**Error handling:**
- Wrap all operations in try-except
- Log errors with context
- Raise custom exceptions: `DatabaseError`, `RecordNotFoundError`
- Use transactions for multi-step operations

### 3.3 LLM Service

**Create `app/services/llm_service.py`:**

**Initialize Gemini:**
- Configure `google.generativeai` with API key
- Create model instance: `GenerativeModel('gemini-2.5-pro')`
- Set generation config:
  - temperature: 0.7 (balance creativity and consistency)
  - top_p: 0.9
  - top_k: 40
  - max_output_tokens: 2048

**System prompt management:**
- Load base prompt from `app/prompts/system_prompt.py`
- Template variables: {user_type}, {registered}, {user_name}, {context_summary}
- Prompt structure:
  ```
  You are an Ethiopian horticulture marketplace assistant.
  
  LANGUAGE: Respond naturally in English, Amharic (አማርኛ), or Amharic written in Latin script (Amhar-glish). Match the user's language choice.
  
  USER CONTEXT:
  - User Type: {user_type}
  - Registered: {registered}
  - Name: {user_name}
  
  CURRENT STATE: {context_summary}
  
  GUIDELINES:
  - Be conversational, warm, and helpful - not robotic
  - For customers: Help discover products, provide knowledge, facilitate orders
  - For suppliers: Manage inventory, provide pricing insights, optimize operations
  - Always confirm critical actions before executing
  - Use tools proactively when data is needed
  - Keep responses concise but complete
  
  AVAILABLE TOOLS:
  {tool_descriptions}
  ```

**Function calling setup:**

**Define tools as Gemini function declarations:**
- Tool 1: `search_products`
  - Description: "Search for products by name or category"
  - Parameters: query (string, required)
  - Returns: List of available products with current inventory

- Tool 2: `get_pricing_insights`
  - Description: "Get competitor pricing and recommendations for a product"
  - Parameters: product_name (string, required)
  - Returns: Pricing analysis with recommendations

- Tool 3: `rag_query`
  - Description: "Search product knowledge base for storage, nutrition, recipes, selection tips, seasonality"
  - Parameters: query (string, required), category (string, optional)
  - Returns: Relevant product information

- Tool 4: `create_order`
  - Description: "Create a customer order with delivery details"
  - Parameters: items (array of {product_name, quantity_kg}), delivery_date (date), delivery_location (string)
  - Returns: Order confirmation with order_id

- Tool 5: `add_inventory`
  - Description: "Add product inventory for suppliers"
  - Parameters: product_name, quantity_kg, price_per_unit, available_date, expiry_date (optional), generate_image (boolean)
  - Returns: Inventory confirmation

- Tool 6: `check_supplier_stock`
  - Description: "View supplier's current inventory"
  - Parameters: None (uses supplier_id from session)
  - Returns: List of inventory items with quantities and status

- Tool 7: `get_supplier_schedule`
  - Description: "View supplier's delivery schedule"
  - Parameters: start_date, end_date (optional, defaults to current week)
  - Returns: List of confirmed orders with dates

- Tool 8: `suggest_flash_sale`
  - Description: "Check for expiring inventory and suggest discounts"
  - Parameters: None
  - Returns: List of expiring products with suggested discount percentages

**Chat method:**
- Input: conversation_history (list of messages), available_tools (list)
- Process:
  1. Format conversation history for Gemini API
  2. Inject system prompt as first message
  3. Call `generate_content` with tools parameter
  4. Parse response:
     - If tool call: Extract function name and arguments
     - If text: Return message content
  5. Handle errors gracefully (API limits, network issues)
- Output: Response object with type (text/tool_call) and content

**Multi-turn conversation:**
- Maintain full conversation context
- Track tool call results and inject into history
- Handle follow-up questions naturally

### 3.4 RAG Service

**Create `app/services/rag_service.py`:**

**Chroma connection:**
- Initialize client pointing to Chroma service
- Get or create `product_knowledge` collection
- Use Gemini embedding function for consistency

**Query method:**
- Input: user query, optional category filter, n_results (default 3)
- Process:
  1. Clean query (remove special characters, normalize)
  2. Build Chroma query with optional where clause for category
  3. Execute semantic search
  4. Parse results with similarity scores
- Output: List of {content, product_name, category, score}

**Context formatting:**
- Format RAG results for LLM consumption
- Structure: "Based on product knowledge: [Source 1: content] [Source 2: content]"
- Include product name for attribution

**Caching:**
- Implement simple in-memory cache for frequent queries (e.g., "how to store tomatoes")
- Cache TTL: 1 hour
- Cache key: hash of (query, category, n_results)

### 3.5 Image Generation Service

**Create `app/services/image_service.py`:**

**Initialize Gemini Image API:**
- Model: `gemini-2.5-flash-image`
- Configure safety settings (block none for product images)

**Generate product image method:**
- Input: product_name, optional style_hints
- Process:
  1. Build prompt: "Professional product photography of fresh {product_name}, high quality, vibrant colors, Ethiopian market context, clean white background, studio lighting"
  2. Call Gemini Image API
  3. Receive base64 encoded image
  4. Save to local storage: `backend/static/images/{product_name}_{timestamp}.png`
  5. Generate URL: `/static/images/{filename}`
- Output: Image URL string

**Error handling:**
- If API fails, return placeholder image URL
- Log generation failures
- Implement retry logic (max 2 retries)

**Storage consideration:**
- For MVP: Local file storage in Docker volume
- Future: Upload to S3/Cloud Storage

### 3.6 Session Manager

**Create `app/orchestrator/session_manager.py`:**

**Redis client setup:**
- Use `redis.asyncio` for async operations
- Connection pool with max connections = 50

**Session operations:**

**create_session():**
- Generate UUID for session_id
- Initialize session structure (from Milestone 2.4)
- Set in Redis with TTL
- Return session_id

**get_session(session_id):**
- Fetch from Redis
- Parse JSON
- If not found, return None
- Extend TTL on each access

**update_session(session_id, updates):**
- Get current session
- Merge updates (deep merge for nested fields)
- Update last_active timestamp
- Save back to Redis with extended TTL

**add_message(session_id, role, content):**
- Append to conversation_history
- Trim history if exceeds MAX_CONVERSATION_HISTORY (keep only recent 20)
- Update session

**get_conversation_context(session_id, n_messages):**
- Retrieve last N messages for LLM context
- Format as [{role, content}, ...]

**cleanup_expired():**
- Redis handles this automatically with TTL
- Optional: Background task to log expired sessions

### Deliverables
- ✅ Database service with all CRUD operations
- ✅ LLM service with Gemini integration and 8 tool definitions
- ✅ RAG service connected to Chroma
- ✅ Image generation service
- ✅ Session manager with Redis integration
- ✅ Unit tests for each service

### Success Criteria
- Database service can create users, products, orders without errors
- LLM service generates responses and calls tools correctly
- RAG service returns relevant knowledge for queries like "store avocados"
- Image service generates product images
- Session manager persists and retrieves session data correctly
- Run `pytest tests/services/` with >80% pass rate

---

## 📋 Milestone 4: Conversation Orchestration & Business Logic
**Duration**: Days 6-7  
**Objective**: Implement conversation flows for customer and supplier journeys

### 4.1 Tool Registry Implementation

**Create `app/orchestrator/tool_registry.py`:**

**ToolRegistry class:**
- Maintain mapping of tool names to handler functions
- Each tool has: name, description, parameters schema, handler function
- Register all 8 tools defined in Milestone 3.3

**Tool handler implementations:**

**Tool 1: search_products_handler(query):**
- Call db_service.search_products(query)
- Join with inventory to get availability and pricing
- Format response: "Found {count} products: {product_name}: {quantity}kg available at {price} ETB/kg"
- If no results: "No products found matching '{query}'. Available categories: vegetables, fruits, dairy."

**Tool 2: get_pricing_insights_handler(product_name):**
- Get product_id from product name
- Call db_service.calculate_pricing_recommendation(product_id)
- Format response with context:
  ```
  Current market prices for {product_name}:
  - Farm/Local: {farm_avg} ETB/kg
  - Supermarket: {supermarket_avg} ETB/kg
  - Distribution Center: {distribution_avg} ETB/kg
  
  Historical selling price: {historical_avg} ETB/kg
  
  Recommendation: Set price at {recommended} ETB/kg for competitive positioning and quick turnover.
  ```

**Tool 3: rag_query_handler(query, category=None):**
- Call rag_service.query(query, category)
- Format results with product attribution
- If no results: "I don't have specific information about that. Let me help you with something else."

**Tool 4: create_order_handler(items, delivery_date, delivery_location, session_id):**
- Get customer_id from session
- Validate: customer must be registered
- For each item:
  - Get product_id
  - Check inventory availability
  - Calculate subtotal
- Calculate total_amount
- Call db_service.create_order()
- Call db_service.add_order_items()
- Format confirmation:
  ```
  Order confirmed! 🎉
  Order ID: {order_id}
  Items: {items_list}
  Total: {total_amount} ETB
  Delivery: {delivery_date} to {delivery_location}
  Payment: Cash on Delivery
  ```

**Tool 5: add_inventory_handler(product_name, quantity_kg, price_per_unit, available_date, expiry_date, generate_image, session_id):**
- Get supplier_id from session
- Validate: user must be registered supplier
- Get product_id
- If generate_image=true: Call image_service.generate_product_image()
- Call db_service.add_inventory()
- Format confirmation with image URL if generated

**Tool 6: check_supplier_stock_handler(session_id):**
- Get supplier_id from session
- Call db_service.get_supplier_inventory(supplier_id)
- Format as table:
  ```
  Your Current Inventory:
  1. Tomatoes: 50kg @ 55 ETB/kg (Available: Dec 1, Expires: Dec 15)
  2. Onions: 30kg @ 45 ETB/kg (Available: Dec 2)
  ```

**Tool 7: get_supplier_schedule_handler(start_date, end_date, session_id):**
- Get supplier_id from session
- If no dates: default to current week (Monday-Sunday)
- Call db_service.get_supplier_schedule()
- Format by date:
  ```
  Your Delivery Schedule:
  Monday, Dec 2: 3 orders (150kg total)
  Wednesday, Dec 4: 2 orders (80kg total)
  Friday, Dec 6: 1 order (30kg total)
  ```

**Tool 8: suggest_flash_sale_handler(session_id):**
- Get supplier_id from session
- Call db_service.check_expiring_inventory(supplier_id, days_threshold=3)
- For each expiring item:
  - Calculate suggested discount: 
    - 1-2 days: 20% off
    - <1 day: 30% off
- Format suggestion:
  ```
  ⚠️ Expiring Inventory Alert:
  - Milk (2 liters): Expires in 2 days → Suggest 20% flash sale (50 ETB → 40 ETB)
  Would you like me to activate this sale?
  ```

**Tool execution wrapper:**
- Log all tool calls
- Handle errors gracefully
- Return structured response: {success: bool, data: any, message: str}

### 4.2 Intent Detection & Routing

**Create `app/orchestrator/intent_detector.py`:**

**Intent categories:**
- `registration_customer`: User provides name, phone, location
- `registration_supplier`: User identifies as supplier
- `product_inquiry`: Questions about products, availability
- `knowledge_query`: How-to questions (storage, nutrition, recipes)
- `place_order`: Customer wants to buy
- `add_inventory`: Supplier wants to list products
- `check_stock`: Supplier inventory check
- `check_schedule`: Supplier delivery schedule
- `flash_sale_check`: Supplier optimization
- `general_chat`: Greetings, casual conversation

**Intent detection logic:**
- Use LLM for intent classification (leverage Gemini's understanding)
- Provide intent options in system prompt
- Extract entities from user message (product names, quantities, dates)

**Routing rules:**
- If not registered → route to registration flow
- If customer registered → enable ordering and knowledge queries
- If supplier registered → enable inventory management
- Track current_flow in session to maintain conversation state

### 4.3 Conversation Orchestrator

**Create `app/orchestrator/conversation.py`:**

**ConversationOrchestrator class:**

**Main method: `process_message(session_id, user_message)`:**

1. **Load session context:**
   - Get session from Redis
   - Get conversation history
   - Get user registration status

2. **Update session:**
   - Add user message to history
   - Update last_active timestamp

3. **Detect intent:**
   - Call intent_detector
   - Update context.current_flow if intent changes

4. **Build LLM context:**
   - Prepare system prompt with user context
   - Include conversation history (last 10 messages)
   - Define available tools based on user_type

5. **Call LLM:**
   - Send to llm_service.chat()
   - Receive response (text or tool_call)

6. **Handle response:**
   - **If text response:**
     - Add to conversation history
     - Return to user
   
   - **If tool call:**
     - Extract tool name and arguments
     - Execute via tool_registry
     - Get tool result
     - Add tool call and result to conversation history
     - Call LLM again with tool result (function calling loop)
     - Return final LLM response

7. **Update session:**
   - Save updated context
   - Save conversation history

8. **Return response:**
   - Format as {type: "text", content: str, metadata: {}}

**Special handlers:**

**Registration flow:**
- Customer: Extract name, phone, location from natural conversation
- Supplier: Same + mark user_type as 'supplier'
- Call db_service.create_user() when all info collected
- Update session with user_id and registered=true
- Confirmation message

**Order confirmation flow:**
- Track pending_order in session context
- Confirm each detail: items, delivery date, location
- Set context.awaiting_confirmation = true
- When user confirms: Execute create_order tool
- **COD simulation:** After order creation, send "Order confirmed for COD" message, wait 5 seconds (asyncio.sleep(5)), then send "Payment confirmed! Your order is being processed."

**Inventory addition flow:**
- Track pending_inventory in session
- Collect details conversationally: quantity, date, expiry, price
- Get pricing insights before asking for price
- Ask about image generation
- When complete: Execute add_inventory tool

**Error handling:**
- Catch all exceptions
- Log with full context
- Return friendly error message to user
- Never expose technical errors to end users

### 4.4 Conversation State Machine

**Create `app/models/state_machine.py`:**

**Define states:**
- `IDLE`: No active flow
- `REGISTERING`: Collecting user information
- `ORDERING`: Building customer order
- `CONFIRMING_ORDER`: Awaiting order confirmation
- `ADDING_INVENTORY`: Collecting inventory details
- `CONFIRMING_INVENTORY`: Awaiting inventory confirmation
- `QUERYING`: Handling knowledge/product questions

**State transitions:**
- Define valid transitions (e.g., IDLE → REGISTERING, ORDERING → CONFIRMING_ORDER)
- Enforce transition rules
- Update context.current_flow on state changes

**State-specific prompts:**
- Each state has tailored system prompt
- Example for ORDERING state: "You are helping a customer place an order. Confirm each item and quantity clearly. Once all items are collected, ask for delivery date and location."

### Deliverables
- ✅ Tool registry with all 8 tools implemented
- ✅ Intent detection system
- ✅ Conversation orchestrator with multi-turn handling
- ✅ Registration flows for both user types
- ✅ Order placement flow with COD simulation
- ✅ Inventory management flow with pricing insights
- ✅ State machine for flow management

### Success Criteria
- Test customer registration: "My name is Abebe, phone 0911234567, I'm in Addis Ababa"
- Test order flow: "I want 5kg tomatoes" → confirmation → COD simulation
- Test supplier flow: "Add 50kg tomatoes at 55 ETB" → pricing insights shown
- Test RAG: "How to store avocados?" → relevant knowledge returned
- Test flash sale: Supplier with expiring inventory gets proactive suggestion
- All flows complete without crashes

---

## 📋 Milestone 5: Frontend Implementation
**Duration**: Days 8-9  
**Objective**: Build responsive chat UI with real-time messaging

### 5.1 Backend API Endpoints

**Create `app/main.py` FastAPI routes:**

**WebSocket endpoint:**
- `WebSocket /ws/{session_id}`: Bidirectional chat communication
  - On connect: Validate session or create new
  - On message: Call orchestrator.process_message()
  - Send response back through socket
  - Handle disconnections gracefully

**REST endpoints:**
- `POST /api/sessions`: Create new session, return session_id
- `GET /api/sessions/{session_id}`: Get session info
- `GET /api/health`: Health check endpoint
- `GET /static/{filepath}`: Serve generated images

**Socket.IO integration:**
- Use `python-socketio` with FastAPI mount
- Events:
  - `connect`: Initialize session
  - `message`: Process user message, emit `response`
  - `typing`: Emit typing indicator
  - `disconnect`: Log session end

**CORS configuration:**
- Allow origins: `http://localhost:3000` (frontend)
- Allow credentials: true
- Expose headers: *

**Error handling middleware:**
- Catch all unhandled exceptions
- Log errors
- Return generic error message to client
- Never expose stack traces

### 5.2 Next.js Application Structure

**Create pages:**

**`app/page.tsx` (Landing):**
- Welcome message
- Language selection buttons (English/አማርኛ/Amharic-Latin)
- "Start Chat" button → navigates to /chat
- Brief feature highlights

**`app/chat/page.tsx` (Main Chat):**
- Chat interface component
- Socket.IO connection on mount
- Message list (scrollable)
- Input field with send button
- Language indicator
- Session persistence

**`app/layout.tsx` (Root Layout):**
- Global styles
- Font configuration
- Metadata (title, description)
- TailwindCSS setup

### 5.3 Chat UI Components

**Create `components/ChatMessage.tsx`:**
- Props: message {role, content, timestamp}
- User messages: Right-aligned, blue background
- Assistant messages: Left-aligned, gray background
- Markdown rendering for formatted text
- Timestamp display
- Avatar icons (user/bot)

**Create `components/ChatInput.tsx`:**
- Text input field with placeholder
- Send button (disabled when empty)
- Character limit: 1000 characters
- Enter key to send (Shift+Enter for newline)
- Loading state during response
- Auto-focus on mount

**Create `components/TypingIndicator.tsx`:**
- Animated dots when bot is "thinking"
- Show only when waiting for response
- Smooth fade-in/out animation

**Create `components/OrderCard.tsx`:**
- Display order summary in chat
- Props: order {items, total, delivery_date, location}
- Formatted layout with icons
- Expandable/collapsible details

**Create `components/LanguageSelector.tsx`:**
- Dropdown or toggle for language preference
- Options: English, አማርኛ, Amharic-Latin
- Store selection in localStorage
- Display current language in header

### 5.4 WebSocket Client Integration

**Create `lib/socketClient.ts`:**

**Socket.IO client setup:**
- Connect to `http://localhost:8000` with session_id
- Auto-reconnect on connection loss
- Emit `message` event with user text
- Listen for `response` event from server

**Event handlers:**
- `connect`: Log connection, initialize chat
- `message`: Append user message to UI
- `response`: Append bot response to UI
- `error`: Show error toast
- `disconnect`: Show reconnecting indicator

**Message queue:**
- Queue messages if connection lost
- Send queued messages on reconnect
- Prevent message loss

### 5.5 State Management

**Create `lib/chatStore.ts` (React Context):**

**ChatContext:**
- State:
  - messages: Array of message objects
  - sessionId: Current session ID
  - isConnected: Socket connection status
  - isTyping: Bot typing indicator
  - language: Selected language
- Actions:
  - sendMessage(text): Send to socket, add to UI
  - addMessage(message): Append to messages array
  - setTyping(bool): Toggle typing indicator
  - setLanguage(lang): Update language preference
  - clearChat(): Reset conversation

**Provider setup:**
- Wrap app in ChatProvider
- Initialize socket connection in provider
- Persist session_id in localStorage
- Load conversation history on mount (if returning user)

### 5.6 Styling & Responsiveness

**TailwindCSS configuration:**
- Custom color scheme: Ethiopian flag colors (green, yellow, red) as accents
- Custom fonts: Clean, readable sans-serif
- Dark mode support (optional)

**Responsive design:**
- Mobile-first approach
- Chat takes full viewport height on mobile
- Side-by-side layout on desktop (chat + info panel)
- Touch-friendly button sizes (min 44px)

**Animations:**
- Message slide-in on new message
- Typing indicator pulse
- Button hover effects
- Smooth scrolling in message list

### 5.7 Error Handling & UX Polish

**Loading states:**
- Show skeleton loaders while fetching
- Disable input during processing
- Show typing indicator when bot is responding

**Error handling:**
- Connection errors: "Reconnecting..." banner
- Message send failures: Retry button
- Generic errors: Toast notification with retry option

**Auto-scroll:**
- Scroll to bottom on new message
- Disable auto-scroll if user scrolled up (preserve reading position)
- "Scroll to bottom" button when not at bottom

**Message timestamps:**
- Format: "10:30 AM" for today, "Dec 1, 10:30 AM" for older
- Group messages by date with date separators

**Welcome message:**
- On fresh session, bot sends: "Hello! I'm your Ethiopian horticulture marketplace assistant. How can I help you today? 👋"

### Deliverables
- ✅ FastAPI WebSocket endpoint functional
- ✅ Next.js chat interface complete
- ✅ Socket.IO real-time communication working
- ✅ All chat components implemented and styled
- ✅ Responsive design tested on mobile/desktop
- ✅ Error handling and loading states

### Success Criteria
- Open `http://localhost:3000`, click "Start Chat"
- Send message: "Hello" → Receive bot greeting
- Test conversation flow: Registration → Order → Confirmation
- Disconnect internet → See reconnecting indicator
- Refresh page → Session persists, conversation reloads
- Test on mobile viewport → UI adapts correctly

---

## 📋 Milestone 6: Integration, Testing & Deployment
**Duration**: Days 10-12  
**Objective**: End-to-end testing, documentation, and production-ready deployment

### 6.1 Integration Testing

**Create `tests/integration/test_flows.py`:**

**Test scenarios:**

**Customer registration and order flow:**
```python
1. Create new session
2. Send: "Hi, I'm Abebe"
3. Assert: Bot asks for phone
4. Send: "0911234567"
5. Assert: Bot asks for location
6. Send: "Addis Ababa"
7. Assert: Registration confirmation
8. Send: "How do I store tomatoes?"
9. Assert: RAG response with storage info
10. Send: "I want 5kg tomatoes"
11. Assert: Bot confirms availability and asks for details
12. Send: "Deliver December 5th to Bole"
13. Assert: Order confirmation with COD simulation
14. Wait 5 seconds
15. Assert: Payment confirmed message
```

**Supplier inventory and pricing flow:**
```python
1. Create session
2. Send: "I'm a supplier, name Kebede, phone 0912345678"
3. Assert: Registration success
4. Send: "I want to add 50kg tomatoes"
5. Assert: Bot provides pricing insights (Farm/Supermarket/Distribution prices)
6. Send: "Set price at 55 ETB per kg, available tomorrow"
7. Assert: Bot asks about expiry date
8. Send: "Expires in 10 days"
9. Assert: Bot asks about image generation
10. Send: "Yes, generate image"
11. Assert: Image generated confirmation with URL
```

**Flash sale suggestion flow:**
```python
1. Create supplier session with expiring inventory in DB
2. Send: "Check my inventory"
3. Assert: Bot shows inventory with expiry warning
4. Assert: Bot proactively suggests flash sale
5. Send: "Yes, activate 20% sale"
6. Assert: Price updated, confirmation shown
```

**Multi-language handling:**
```python
1. Send in English: "Hello"
2. Assert: English response
3. Send in Amharic: "ሰላም"
4. Assert: Amharic response
5. Send in Amhar-glish: "selam"
6. Assert: Natural language response
```

**Run tests:**
- Use pytest with async support
- Mock external APIs when needed (Gemini, image gen)
- Capture failed test screenshots
- Generate coverage report (aim for >70%)

### 6.2 Load Testing

**Create `tests/load/load_test.py`:**

**Simulate concurrent users:**
- Use `locust` or `pytest-asyncio`
- Test scenarios:
  - 10 concurrent sessions, 100 messages each
  - 50 concurrent searches
  - 20 concurrent order placements

**Metrics to measure:**
- Response time (p50, p95, p99)
- Throughput (messages per second)
- Error rate
- Database connection pool usage
- Redis memory usage

**Performance targets:**
- Average response time: <2 seconds
- p95 response time: <5 seconds
- Error rate: <1%
- Support 100 concurrent users

### 6.3 Data Validation & Cleanup

**Create `scripts/validate_data.py`:**

**Validation checks:**
- Verify all 52,427 transactions loaded
- Check all 14,616 competitor pricing records
- Validate all 56 knowledge base entries in Chroma
- Ensure product_ids consistent across tables
- Check for orphaned records (foreign key integrity)
- Validate date ranges (no future dates in historical data)

**Run validation:**
```bash
docker-compose exec backend python scripts/validate_data.py
```

**Data cleanup script (optional):**
- Remove test orders
- Reset demo accounts
- Clear expired sessions

### 6.4 Documentation

**Update `README.md` with complete guide:**

**Structure:**
1. Project Overview
2. Architecture Diagram (ASCII or link to image)
3. Prerequisites (Docker, API keys)
4. Quick Start (one-command setup)
5. Environment Variables
6. Database Schema
7. API Documentation
8. Testing Guide (manual + automated)
9. Troubleshooting
10. Future Improvements

**Testing script for demo:**
```markdown
## Demo Script

### Customer Journey
1. **Registration**
   - User: "Hello"
   - Bot: Greeting
   - User: "My name is Abebe, phone 0911234567, I live in Addis Ababa"
   - Bot: Confirmation

2. **Knowledge Query**
   - User: "How should I store ripe avocados?"
   - Bot: RAG response with storage tips

3. **Product Discovery**
   - User: "What vegetables are available?"
   - Bot: List of available products with prices

4. **Ordering**
   - User: "I want 5kg red onions and 2 liters milk"
   - Bot: Confirmation with pricing
   - User: "Deliver on December 5th to Bole, Addis Ababa"
   - Bot: Order confirmed + COD simulation (5 second pause) + payment confirmation

### Supplier Journey
1. **Registration**
   - User: "I'm a supplier, my name is Kebede, phone 0912345678"
   - Bot: Supplier registration confirmed

2. **Add Inventory with Pricing Insights**
   - User: "I want to add tomatoes"
   - Bot: Asks for quantity
   - User: "50kg available tomorrow"
   - Bot: Provides pricing insights (Farm: 50 ETB, Supermarket: 65 ETB, recommended: 55 ETB)
   - User: "Set price at 55 ETB per kg"
   - Bot: Asks for expiry date
   - User: "Expires in 12 days"
   - Bot: Asks about image generation
   - User: "Yes, generate image"
   - Bot: Confirmation with image URL

3. **Check Inventory**
   - User: "Show my inventory"
   - Bot: List of all supplier's products

4. **Check Schedule**
   - User: "What's my delivery schedule for this week?"
   - Bot: List of confirmed orders by date

5. **Flash Sale (if applicable)**
   - User: "Check if any products are expiring soon"
   - Bot: Lists expiring inventory with flash sale suggestions
   - User: "Yes, activate the sale"
   - Bot: Confirms price reduction
```

**API documentation:**
- Document all REST endpoints
- WebSocket event types
- Request/response examples
- Error codes

### 6.5 Containerization & Deployment

**Optimize Docker images:**

**Backend Dockerfile production-ready:**
- Multi-stage build to reduce image size
- Use python:3.11-slim as base
- Install only production dependencies
- Non-root user for security
- Health check: `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`

**Frontend Dockerfile production-ready:**
- Multi-stage build: build stage + runtime stage
- Build with `npm run build`
- Serve with production server (not dev server)
- Environment variable injection at runtime

**Docker Compose production profile:**
- Create `docker-compose.prod.yml`
- Remove volume mounts (except data volumes)
- Add restart policies: `restart: always`
- Configure resource limits (CPU, memory)
- Use secrets for sensitive data

**Deployment instructions:**
```markdown
## Deployment on Server

### Prerequisites
- Ubuntu 20.04+ or similar Linux server
- Docker 24+ installed
- Docker Compose V2 installed
- Minimum 4GB RAM, 2 CPU cores, 20GB storage

### Steps
1. SSH into server
2. Clone repository
3. Copy and configure .env file
4. Run: `docker-compose -f docker-compose.prod.yml up -d`
5. Initialize database: `docker-compose exec backend python scripts/init_db.py`
6. Load data: `docker-compose exec backend python scripts/load_dataset.py`
7. Verify: `docker-compose ps` (all services healthy)
8. Access at: `http://your-server-ip:3000`

### Optional: Nginx Reverse Proxy
- Install Nginx on host
- Configure proxy_pass to backend:8000 and frontend:3000
- Setup SSL with Let's Encrypt
- Configure custom domain
```

### 6.6 Monitoring & Logging

**Setup logging:**
- Backend: Python logging to stdout + file
- Frontend: Console logging (dev), external service (prod)
- Log levels: DEBUG (dev), INFO (prod)
- Log format: JSON for easy parsing

**Key logs to capture:**
- All LLM requests/responses (for debugging)
- Tool calls and results
- Database query performance
- Error stack traces
- User sessions created/expired
- WebSocket connections/disconnections

**Monitoring tools (optional for MVP):**
- Docker stats: `docker stats` to monitor resource usage
- PostgreSQL slow query log
- Redis memory usage
- Application metrics dashboard (Grafana if time permits)

### 6.7 Security Hardening

**Backend security:**
- Rate limiting: 100 requests per minute per IP
- Input validation: Sanitize all user inputs
- SQL injection prevention: Use parameterized queries
- XSS prevention: Escape HTML in responses
- CORS: Restrict to specific origins
- API key security: Never expose in client code

**Frontend security:**
- Content Security Policy headers
- HTTPS only in production
- Sanitize user-generated content before rendering
- Secure session storage (HttpOnly cookies if needed)

**Database security:**
- Use strong passwords (not default)
- Restrict PostgreSQL access to backend only
- Regular backups: Setup automated backup script
- Encrypt sensitive data at rest (future enhancement)

### 6.8 Final Testing Checklist

**Functional testing:**
- [ ] Customer registration flow works
- [ ] Supplier registration flow works
- [ ] Order placement with COD simulation works
- [ ] Inventory addition with pricing insights works
- [ ] RAG knowledge queries return accurate info
- [ ] Image generation works
- [ ] Flash sale suggestions appear for expiring inventory
- [ ] Multi-language support works (English/Amharic/Amhar-glish)
- [ ] Session persistence works (page refresh)
- [ ] Error handling graceful (network loss, API failures)

**Performance testing:**
- [ ] Response time <2 seconds average
- [ ] System handles 50 concurrent users
- [ ] Database queries optimized (no N+1 queries)
- [ ] Frontend loads in <3 seconds

**UX testing:**
- [ ] Chat UI intuitive and responsive
- [ ] Mobile view works correctly
- [ ] Loading indicators show appropriately
- [ ] Error messages clear and helpful
- [ ] Conversation flows naturally (not robotic)

**Deployment testing:**
- [ ] Docker Compose starts all services
- [ ] Database initialization script works
- [ ] Data loading script completes successfully
- [ ] All environment variables configured
- [ ] Health checks pass
- [ ] Logs accessible and readable

### Deliverables
- ✅ Comprehensive test suite with >70% coverage
- ✅ Load testing results documented
- ✅ Complete README with architecture diagram and demo script
- ✅ Production-ready Docker configuration
- ✅ Deployment guide for server setup
- ✅ Security hardening implemented
- ✅ Logging and monitoring configured
- ✅ All tests passing

### Success Criteria
- Run full test suite: `pytest tests/ -v` → All tests pass
- Deploy to test server → All services start successfully
- Execute manual demo script → All flows work end-to-end
- Load test → System handles 50 concurrent users with <2s response time
- Documentation review → Clear enough for another developer to deploy

---

## 📊 Project Summary

### Total Timeline
- **Milestone 1**: 1 day - Foundation
- **Milestone 2**: 2 days - Data Layer
- **Milestone 3**: 2 days - Backend Services
- **Milestone 4**: 2 days - Orchestration
- **Milestone 5**: 2 days - Frontend
- **Milestone 6**: 3 days - Integration & Deployment

**Total: 12 days**

### Key Deliverables
1. ✅ Fully functional bilingual chatbot (English/Amharic/Amhar-glish)
2. ✅ Dual customer/supplier workflows
3. ✅ RAG-powered product knowledge base (56 entries)
4. ✅ Dynamic pricing insights from 14,616 historical price points
5. ✅ AI-generated product images
6. ✅ Flash sale suggestions for expiring inventory
7. ✅ COD payment simulation with 5-second delay
8. ✅ Containerized deployment (one command)
9. ✅ Complete documentation and demo script

### Tech Stack Summary
- **Frontend**: Next.js 14 + TailwindCSS + Socket.IO
- **Backend**: FastAPI + Gemini 2.5 Pro + Python 3.11
- **Databases**: PostgreSQL 15 + Chroma + Redis 7
- **Infrastructure**: Docker + Docker Compose
- **AI**: Gemini 2.5 Pro (LLM) + Gemini 2.5 Flash Image (Image Gen)

### Post-MVP Roadmap
1. Cloud deployment (AWS/Azure/GCP)
2. SMS notifications integration
3. Payment gateway (Chapa/Telebirr)
4. Mobile app (React Native)
5. Admin dashboard with analytics
6. Advanced ML: Demand forecasting, price optimization
7. Multi-vendor marketplace expansion

---

## 🎯 Developer Quick Reference

### Daily Checklist
- [ ] Pull latest code
- [ ] Start Docker Compose: `docker-compose up`
- [ ] Run tests: `pytest tests/`
- [ ] Check logs: `docker-compose logs -f backend`
- [ ] Manual test: Follow demo script
- [ ] Commit progress with descriptive messages
- [ ] Update README if architecture changes

### Common Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose up --build

# Initialize database
docker-compose exec backend python scripts/init_db.py

# Load dataset
docker-compose exec backend python scripts/load_dataset.py

# Run tests
docker-compose exec backend pytest tests/ -v

# Access PostgreSQL
docker-compose exec postgres psql -U user -d horticulture

# Access Redis CLI
docker-compose exec redis redis-cli

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### Troubleshooting Quick Fixes
- **Backend won't start**: Check GEMINI_API_KEY in .env
- **Database connection error**: Wait 10 seconds for PostgreSQL to initialize
- **Chroma connection error**: Ensure Chroma service is running
- **Frontend can't connect**: Check CORS configuration in backend
- **Session not persisting**: Verify Redis is running and connected
- **RAG returns no results**: Re-run knowledge base ingestion script

---

## 📝 Implementation Notes

### Design Principles
1. **Simplicity First**: MVP mindset - no over-engineering
2. **Modularity**: Each service independent and testable
3. **Containerization**: One-command deployment anywhere
4. **Graceful Degradation**: Handle errors without crashing
5. **Developer Experience**: Clear code, good logging, easy debugging

### What Makes This Architecture MVP-Friendly
- ✅ No complex orchestration frameworks (no LangChain, no Airflow)
- ✅ Direct API integrations (Gemini SDK, not abstraction layers)
- ✅ Simple session management (Redis key-value, not complex state machines)
- ✅ Straightforward RAG (Chroma semantic search, not custom pipelines)
- ✅ Minimal dependencies (only what's necessary)
- ✅ Fast iteration (hot reload for both frontend and backend)
- ✅ Clear separation of concerns (easy to debug and extend)

### Why This Will Succeed
1. **Complete yet simple**: All required features without complexity
2. **Production-ready**: Containerized, tested, documented
3. **Scalable foundation**: Can grow to thousands of users with minimal changes
4. **Clear value**: Solves real problems for Ethiopian horticulture market
5. **Demo-ready**: Impressive features that showcase AI capabilities

---

**This implementation plan, combined with the architecture document, provides everything a developer needs to build this chatbot from scratch. No external references required. Good luck with the implementation! 🚀**
