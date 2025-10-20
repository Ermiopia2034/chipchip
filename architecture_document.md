# AI Architecture Design: Ethiopian Horticulture E-commerce Chatbot

## 🎯 Executive Summary

A practical, MVP-focused architecture for a bilingual (English/Amharic) horticulture chatbot with RAG capabilities, dynamic pricing insights, and dual customer/supplier workflows.

---

## 📐 System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│                     Next.js Frontend                         │
│              (Chat UI + Session Management)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket/REST
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   API GATEWAY LAYER                          │
│                    FastAPI Backend                           │
│   ┌──────────────────────────────────────────────────┐      │
│   │         Conversation Orchestrator                │      │
│   │  (Session Management, Context Tracking)          │      │
│   └──────────────────────────────────────────────────┘      │
└──────┬────────┬──────────┬──────────┬────────────────┬──────┘
       │        │          │          │                │
       ↓        ↓          ↓          ↓                ↓
┌──────────┐ ┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────────┐
│  Gemini  │ │ Redis  │ │ Pg   │ │ Chroma  │ │   Gemini     │
│ 2.5 Pro  │ │Session │ │ SQL  │ │ Vector  │ │  Image Gen   │
│   LLM    │ │ Store  │ │  DB  │ │   DB    │ │   API        │
└──────────┘ └────────┘ └──────┘ └─────────┘ └──────────────┘
```

---

## 🏗️ Component Breakdown

### 1. **Frontend Layer** (Next.js)

**Purpose**: User interface for chat interactions

**Components**:
- `ChatInterface`: Main chat component with message history
- `SessionManager`: Handle WebSocket connections and session persistence
- `LanguageDetector`: Auto-detect English/Amharic/Amhar-glish
- `OrderSummary`: Display order confirmations and details

**Tech Stack**:
- Next.js 14 (App Router)
- TailwindCSS for styling
- Socket.IO client for real-time chat
- React Context for state management

**Key Files**:
```
frontend/
├── app/
│   ├── page.tsx              # Landing page
│   ├── chat/page.tsx         # Main chat interface
│   └── layout.tsx            # Root layout
├── components/
│   ├── ChatMessage.tsx       # Individual message bubble
│   ├── ChatInput.tsx         # Message input field
│   ├── OrderCard.tsx         # Order display component
│   └── TypingIndicator.tsx   # Loading animation
└── lib/
    ├── socketClient.ts       # WebSocket connection
    └── api.ts               # REST API calls
```

---

### 2. **API Gateway & Orchestration** (FastAPI)

**Purpose**: Central hub for request routing, session management, and business logic

**Core Modules**:

#### A. **Conversation Orchestrator**
```python
class ConversationOrchestrator:
    """
    Main controller for chat flow
    """
    - route_message(): Determine user intent and route to appropriate handler
    - maintain_context(): Keep conversation state in Redis
    - handle_tool_calls(): Execute database queries, RAG retrieval, image gen
```

#### B. **Session Manager** (Redis-backed)
```python
class SessionManager:
    """
    Manage user sessions and conversation history
    """
    - create_session(): Initialize new chat session
    - get_context(): Retrieve last N messages for LLM context
    - update_state(): Track user type (customer/supplier), registration status
    - store_message(): Persist chat history
```

#### C. **Tool Registry** (MCP-inspired)
```python
class ToolRegistry:
    """
    Registry of available tools for LLM function calling
    """
    Tools:
    - search_products(): Query PostgreSQL for product availability
    - get_pricing_insights(): Fetch competitor prices and recommendations
    - rag_query(): Semantic search in Chroma for product knowledge
    - create_order(): Insert order into database
    - generate_product_image(): Call Gemini Image API
    - check_supplier_stock(): Query supplier inventory
    - suggest_flash_sale(): Check expiry dates and recommend discounts
```

**Tech Stack**:
- FastAPI with async support
- Redis for session persistence
- Pydantic for data validation
- Socket.IO for WebSocket support

**Key Files**:
```
backend/
├── main.py                    # FastAPI app entry
├── orchestrator/
│   ├── conversation.py        # Main orchestration logic
│   ├── session_manager.py     # Redis session handling
│   └── tool_registry.py       # Tool definitions
├── services/
│   ├── llm_service.py         # Gemini API wrapper
│   ├── rag_service.py         # Vector DB queries
│   ├── db_service.py          # PostgreSQL operations
│   └── image_service.py       # Image generation
├── models/
│   ├── schemas.py             # Pydantic models
│   └── prompts.py             # System prompts
└── utils/
    ├── language_utils.py      # Amharic handling
    └── pricing_logic.py       # Pricing algorithms
```

---

### 3. **LLM Service** (Gemini 2.5 Pro)

**Purpose**: Natural language understanding and generation

**Implementation**:
```python
class LLMService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    async def chat(self, messages: List[Dict], tools: List[Tool]):
        """
        Send conversation to Gemini with available tools
        """
        response = await self.model.generate_content(
            messages,
            tools=tools,  # Function calling definitions
            generation_config={
                'temperature': 0.7,
                'top_p': 0.9
            }
        )
        return self._parse_response(response)
```

**System Prompt Strategy**:
```python
SYSTEM_PROMPT = """
You are a helpful Ethiopian horticulture marketplace assistant.
You speak English, Amharic, and Amharic written in Latin script naturally.

Current user type: {user_type}
Registration status: {registered}

Available tools: {tool_list}

Guidelines:
- Be conversational and friendly, not robotic
- For customers: Help discover products, provide knowledge, facilitate orders
- For suppliers: Help manage inventory, provide pricing insights, suggest optimizations
- Always confirm critical actions (orders, price changes)
- Use tools proactively when context requires data
"""
```

---

### 4. **Database Layer**

#### A. **PostgreSQL** (Relational Data)

**Schema Design**:

```sql
-- Users (unified for customers and suppliers)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    phone VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100),
    user_type ENUM('customer', 'supplier'),
    default_location VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit VARCHAR(20)
);

-- Supplier Inventory
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    supplier_id UUID REFERENCES users(user_id),
    product_id INT REFERENCES products(product_id),
    quantity_kg DECIMAL(10,2),
    price_per_unit DECIMAL(10,2),
    available_date DATE,
    expiry_date DATE,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Orders
CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    customer_id UUID REFERENCES users(user_id),
    order_date TIMESTAMP DEFAULT NOW(),
    delivery_date DATE,
    delivery_location VARCHAR(200),
    total_amount DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending'
);

-- Order Items
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id UUID REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity_kg DECIMAL(10,2),
    price_per_unit DECIMAL(10,2)
);

-- Competitor Pricing (from dataset)
CREATE TABLE competitor_pricing (
    id SERIAL PRIMARY KEY,
    date DATE,
    product_id INT REFERENCES products(product_id),
    price DECIMAL(10,2),
    source_market_type VARCHAR(50),
    location_detail VARCHAR(100)
);

-- Transactions History (from dataset - for analytics)
CREATE TABLE transaction_history (
    transaction_id SERIAL PRIMARY KEY,
    order_date TIMESTAMP,
    product_id INT,
    quantity_ordered DECIMAL(10,2),
    price_per_unit DECIMAL(10,2),
    order_total_amount DECIMAL(10,2)
);
```

**Service Class**:
```python
class DatabaseService:
    async def get_product_availability(self, product_name: str):
        """Check current inventory"""
        
    async def get_pricing_insights(self, product_name: str):
        """Get competitor prices and historical trends"""
        
    async def create_order(self, order_data: OrderSchema):
        """Insert new order"""
        
    async def check_expiring_inventory(self, supplier_id: str):
        """Find products nearing expiry"""
```

#### B. **Chroma** (Vector Database for RAG)

**Purpose**: Semantic search for product knowledge

**Data Ingestion**:
```python
class VectorDBService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="product_knowledge",
            embedding_function=embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=GEMINI_API_KEY
            )
        )
    
    async def ingest_knowledge_base(self, knowledge_df):
        """
        Load Product_Knowledge_Base sheet into Chroma
        """
        self.collection.add(
            documents=knowledge_df['embedding_text'].tolist(),
            metadatas=knowledge_df[['product_name', 'category']].to_dict('records'),
            ids=[f"kb_{i}" for i in range(len(knowledge_df))]
        )
    
    async def semantic_search(self, query: str, n_results=3):
        """
        Find relevant product knowledge
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results['documents'][0]
```

**Indexed Data Categories**:
- Storage tips (56 entries)
- Nutritional information (56 entries)
- Recipe suggestions (56 entries)
- Selection guides (56 entries)
- Seasonality information (56 entries)

---

### 5. **Image Generation Service**

**Purpose**: Generate product images for supplier listings

```python
class ImageService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    async def generate_product_image(self, product_name: str):
        """
        Generate realistic product image
        """
        prompt = f"Professional product photography of fresh {product_name}, high quality, Ethiopian market context, white background"
        
        response = await self.model.generate_images(
            prompt=prompt,
            num_images=1
        )
        
        # Save to local storage or cloud
        image_url = self._save_image(response.images[0])
        return image_url
```

---

### 6. **Redis Session Store**

**Purpose**: Fast session state management

**Data Structure**:
```python
# Session Key: session:{session_id}
{
    "user_id": "uuid",
    "user_type": "customer|supplier",
    "registered": true|false,
    "context": {
        "current_flow": "ordering|registration|inquiry",
        "pending_order": {...},
        "conversation_history": [...]
    },
    "language": "en|am|amglish"
}

# TTL: 24 hours
```

**Operations**:
```python
class RedisSessionStore:
    def __init__(self):
        self.redis = redis.Redis(host='redis', decode_responses=True)
    
    async def get_session(self, session_id: str):
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def update_session(self, session_id: str, data: dict):
        self.redis.setex(
            f"session:{session_id}",
            86400,  # 24 hours
            json.dumps(data)
        )
```

---

## 🔄 Data Flow Diagrams

### Customer Order Flow

```
User: "I want 5kg of red onions"
    ↓
Frontend → WebSocket → FastAPI
    ↓
Orchestrator:
    1. Get session context from Redis
    2. Detect intent: "place_order"
    3. Extract entities: product="red onions", quantity=5
    ↓
Tool Call: search_products("red onions")
    ↓
PostgreSQL: Query inventory for availability
    ↓
LLM generates response with confirmation
    ↓
User confirms
    ↓
Tool Call: create_order(...)
    ↓
PostgreSQL: Insert into orders table
    ↓
Return confirmation to user
```

### Supplier Pricing Insight Flow

```
Supplier: "I want to add tomatoes, 50kg"
    ↓
Orchestrator detects intent: "add_inventory"
    ↓
Tool Call: get_pricing_insights("tomatoes")
    ↓
PostgreSQL Query:
    - Competitor pricing (last 30 days avg)
    - Historical transaction prices
    - Seasonal patterns
    ↓
Pricing Logic:
    - Calculate recommended price range
    - Consider current inventory levels
    ↓
LLM: "Current prices: Local ~50 ETB, Supermarket ~65 ETB. 
      Recommend: 55 ETB for quick turnover."
    ↓
Supplier sets price: "55 ETB"
    ↓
Tool Call: generate_product_image("tomatoes")
    ↓
Gemini Image API → Save image
    ↓
Insert into inventory table
```

### RAG Knowledge Query Flow

```
Customer: "How should I store avocados?"
    ↓
Orchestrator detects intent: "knowledge_query"
    ↓
Tool Call: rag_query("store avocados")
    ↓
Chroma Vector DB:
    - Embed query using Gemini embeddings
    - Semantic search for top 3 results
    ↓
Retrieved context:
    "Store ripe avocados in refrigerator for 3-5 days.
     Unripe avocados should be kept at room temperature..."
    ↓
LLM generates natural response with retrieved knowledge
    ↓
Return to user
```

---

## 📦 Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 | React-based UI with SSR |
| | TailwindCSS | Styling framework |
| | Socket.IO Client | Real-time communication |
| **Backend** | FastAPI | Async Python API |
| | Uvicorn | ASGI server |
| | Socket.IO | WebSocket support |
| **LLM** | Gemini 2.5 Pro | Conversation & function calling |
| | Gemini 2.5 Flash Image | Image generation |
| **Databases** | PostgreSQL 15 | Transactional data |
| | Chroma | Vector embeddings for RAG |
| | Redis | Session persistence |
| **Infrastructure** | Docker & Docker Compose | Containerization |
| | Nginx | Reverse proxy (optional) |
| **Python Libs** | google-generativeai | Gemini SDK |
| | chromadb | Vector database |
| | psycopg2 | PostgreSQL driver |
| | redis-py | Redis client |
| | pydantic | Data validation |

---

## 🐳 Deployment Architecture

### Docker Compose Setup

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/horticulture
      - REDIS_URL=redis://redis:6379
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres
      - redis
      - chroma
    volumes:
      - ./backend:/app

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=horticulture
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  postgres_data:
  redis_data:
  chroma_data:
```

### Single Command Deployment

```bash
# Clone repo
git clone <repo-url>
cd horticulture-chatbot

# Set environment variables
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Start all services
docker-compose up -d

# Initialize databases
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/load_dataset.py

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

---

## 🎨 Project Structure

```
horticulture-chatbot/
├── frontend/                    # Next.js application
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py             # Entry point
│   │   ├── orchestrator/       # Conversation logic
│   │   ├── services/           # LLM, DB, RAG services
│   │   ├── models/             # Pydantic schemas
│   │   ├── utils/              # Helper functions
│   │   └── prompts/            # System prompts
│   ├── scripts/
│   │   ├── init_db.py          # Database initialization
│   │   └── load_dataset.py     # Load synthetic data
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/                        # Dataset files
│   ├── synthetic_horticulture_dataset.xlsx
│   └── product_knowledge_base.csv
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Days 1-2)
- ✅ Setup Docker environment
- ✅ Initialize PostgreSQL with schema
- ✅ Load synthetic dataset
- ✅ Setup Redis connection
- ✅ Initialize Chroma and ingest knowledge base

### Phase 2: Core Backend (Days 3-4)
- ✅ FastAPI app skeleton
- ✅ Gemini API integration
- ✅ Tool registry setup
- ✅ Session manager implementation
- ✅ Database service layer

### Phase 3: Conversation Logic (Days 5-6)
- ✅ Orchestrator implementation
- ✅ Customer flow handlers
- ✅ Supplier flow handlers
- ✅ RAG integration
- ✅ Function calling setup

### Phase 4: Frontend (Days 7-8)
- ✅ Next.js chat UI
- ✅ WebSocket integration
- ✅ Message components
- ✅ Order display components

### Phase 5: Features (Days 9-10)
- ✅ Image generation integration
- ✅ Pricing insights logic
- ✅ Flash sale suggestions
- ✅ COD simulation (5-second delay)

### Phase 6: Testing & Polish (Days 11-12)
- ✅ End-to-end testing
- ✅ Language handling refinement
- ✅ Error handling
- ✅ Documentation

---

## 🔒 Security Considerations (MVP Level)

1. **API Key Management**: Store Gemini API key in environment variables, never in code
2. **Input Validation**: Use Pydantic for all request/response validation
3. **SQL Injection Prevention**: Use parameterized queries via SQLAlchemy ORM
4. **Session Security**: Generate secure random session IDs, implement TTL
5. **Rate Limiting**: Basic rate limiting on FastAPI endpoints (10 requests/minute per session)

---

## 📊 Monitoring & Observability (Simple)

```python
# Logging setup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

# Key metrics to log
- Conversation turns per session
- Tool call frequency
- Average response time
- Error rates
- User type distribution
```

---

## 🎯 Testing Strategy

### 1. Unit Tests
```python
# test_pricing_logic.py
def test_calculate_recommendation():
    competitor_prices = [50, 55, 65]
    recommended = calculate_recommendation(competitor_prices)
    assert 48 <= recommended <= 67  # Within range
```

### 2. Integration Tests
```python
# test_order_flow.py
async def test_complete_order_flow():
    session_id = create_test_session()
    
    # Register customer
    response = await send_message(session_id, "My name is Abebe, phone 0911234567")
    assert "registered" in response.lower()
    
    # Place order
    response = await send_message(session_id, "I want 5kg of tomatoes")
    assert "confirm" in response.lower()
```

### 3. Manual Test Script (README.md)
```markdown
## Testing Guide

### Customer Flow Test
1. Start chat: "Hello"
2. Register: "My name is Abebe, phone 0911234567, I live in Addis Ababa"
3. Knowledge query: "How do I store ripe avocados?"
4. Order: "I want 5kg red onions and 2 liters milk"
5. Confirm delivery: "Deliver on November 1st to Bole"
6. Payment: Observe 5-second COD simulation

### Supplier Flow Test
1. Start: "Hi"
2. Register as supplier: "I'm a supplier, name is Kebede, phone 0912345678"
3. Add product: "I want to add tomatoes"
   - Observe pricing insights from bot
4. Set details: "50kg available, price 55 ETB per kg, available tomorrow"
5. Image gen: "Yes, generate image"
6. Check stock: "Show my inventory"
7. Check schedule: "What's my delivery schedule for this week?"
```

---

## 🔮 Future Enhancements (Post-MVP)

1. **Scalability**
   - Move to managed services (AWS RDS, ElastiCache, Pinecone)
   - Implement horizontal scaling with load balancer
   - Add caching layer for frequent queries

2. **Features**
   - SMS notifications via Twilio
   - Payment gateway integration (Chapa, Telebirr)
   - Mobile app (React Native)
   - Admin dashboard for analytics

3. **AI Improvements**
   - Fine-tune LLM on Ethiopian agricultural domain
   - Add speech-to-text for voice orders
   - Multi-modal support (image-based product search)

4. **MLOps**
   - Model performance monitoring
   - A/B testing for prompts
   - Feedback loop for conversation quality

---

## ⚡ Quick Start Commands

```bash
# Clone and setup
git clone <repo>
cd horticulture-chatbot
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# Start everything
docker-compose up --build

# In new terminal - Initialize data
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/load_dataset.py

# Access
# Chat UI: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Chroma: http://localhost:8001

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

---

## 📝 Key Design Decisions

1. **Why Gemini 2.5 Pro?**
   - Native Amharic support without additional translation layers
   - Built-in function calling for tool use
   - Cost-effective for MVP scale

2. **Why FastAPI over Flask?**
   - Native async support for better concurrency
   - Automatic OpenAPI documentation
   - Built-in data validation with Pydantic

3. **Why Chroma over Pinecone?**
   - Self-hosted, no external API costs
   - Simple Docker deployment
   - Sufficient for 56 knowledge base entries (MVP scale)

4. **Why Redis for Sessions?**
   - Sub-millisecond latency
   - Simple key-value store perfect for sessions
   - Easy TTL management

5. **Why Not Use LangChain?**
   - Avoided over-engineering
   - Direct Gemini SDK is simpler and more transparent
   - Custom tool registry gives more control
   - Faster debugging and fewer dependencies

---

## 🎬 Conclusion

This architecture provides a **production-ready MVP** that:
- ✅ Handles bilingual conversations naturally
- ✅ Integrates RAG for product knowledge
- ✅ Provides intelligent pricing insights
- ✅ Scales to hundreds of concurrent users
- ✅ Deploys in one command with Docker
- ✅ Maintains clean separation of concerns
- ✅ Avoids over-engineering while being extensible

**Total Implementation Time**: 10-12 days for full-stack developer

**Deployment Time**: < 5 minutes on any server with Docker

The architecture is pragmatic, maintainable, and ready for your demo presentation! 🚀
