# Ethiopian Horticulture E-commerce Synthetic Dataset

## Overview

This synthetic dataset expands the original edataset.xlsx to provide **20 months of historical operations** (January 1, 2024 to August 31, 2025) for an Ethiopian horticulture e-commerce platform. The dataset enables comprehensive RAG pipeline development for LLMs (Gemini 2.5, etc.), business intelligence, pricing analysis, and customer behavior insights.

## Dataset Structure

### 1. Transactions Sheet
**Records**: 52,427 transactions
**Time Period**: Jan 1, 2024 - Aug 31, 2025

**Columns**:
- `order_id`: Unique transaction identifier
- `order_date`: Timestamp of transaction
- `user_id`: Customer identifier
- `user_name`: Customer name
- `phone`: Customer phone number (Ethiopian format)
- `supplier_id`: Supplier identifier
- `product_id`: Product identifier
- `product_name`: Product name
- `quantity_ordered`: Quantity in kg or liters
- `unit`: Unit of measurement (kg/liters)
- `price_per_unit`: Price per unit in Ethiopian Birr (ETB)
- `order_total_amount`: Total transaction amount

### 2. Competitor_Pricing Sheet
**Records**: 14,616 price points
**Frequency**: Every 3 days sampling
**Market Tiers**: Farm, Supermarket, Distribution Center

**Columns**:
- `date`: Price observation date
- `product_id`: Product identifier
- `product_name`: Product name
- `price`: Price in ETB per kg/liter
- `source_market_type`: Competitor tier (Farm/Supermarket/Distribution Center)
- `location_detail`: Ethiopian geographic location
- `product_remark`: Additional product information
- `created_at`: Record creation timestamp

### 3. Product_Knowledge_Base Sheet
**Records**: 56 knowledge entries
**Purpose**: Vector DB embeddings for RAG pipeline with existing LLMs (Gemini 2.5, etc.)

**Columns**:
- `product_name`: Product name
- `category`: Knowledge category (storage/nutrition/recipes/selection/seasonality/general)
- `content`: Detailed product information
- `embedding_text`: Text formatted for vector embeddings
- `created_at`: Entry creation timestamp

### 4. Suppliers Sheet
**Records**: 10 suppliers

**Columns**:
- `supplier_id`: Unique supplier identifier
- `supplier_name`: Supplier name (Ethiopian names)
- `specialty_products`: List of products supplier specializes in

## Product Portfolio

### Horticulture Products (15 items)
**Vegetables**:
- Red Onion (ሃበሻ) - Premium Ethiopian onion variety
- Tomato - Year-round staple
- Potato - Various varieties
- Garlic - Essential cooking ingredient
- Carrot - Root vegetable
- Beetroot - Root vegetable
- White Cabbage - Leafy vegetable
- Green Chili (ስታርታ) - Ethiopian hot pepper
- Lettuce - Leaf vegetable
- Spinach - Leaf vegetable
- Cucumber - Gourd vegetable
- Bell Pepper - Sweet pepper
- Sweet Potato - Root vegetable

**Fruits**:
- Avocado - Premium fruit
- Papaya - Tropical fruit
- Mango - Seasonal tropical fruit
- Banana - Year-round fruit
- Orange - Citrus fruit
- Apple - Imported fruit

### Dairy Products (5 items)
- Milk - Fresh dairy
- Yogurt - Fermented dairy
- Cheese (Ayib) - Traditional Ethiopian cheese
- Butter - Dairy fat
- Cream - Dairy product

## Geographic Coverage

**12 Ethiopian Locations**:
- Tigray - Mekele
- Amhara - Kobo, Bahir Dar
- Oromia - Meki, Jimma, Shashemene, Asella, Adama
- Sidama - Sidama, Dale
- Addis Ababa
- Dire Dawa

## Key Features

### 1. Seasonal Pricing Patterns
The dataset incorporates realistic seasonal variations:
- **Tomatoes**: Higher prices during rainy season (Jun-Aug), lower during dry seasons
- **Avocados**: Peak season Sep-Nov with 30% price reduction
- **Mangoes**: Peak season May-Jul with 40% price reduction
- **Onions**: Peak season Oct-Jan with 30% price reduction
- **Potatoes**: Peak season Nov-Feb with 20% price reduction

### 2. Inflation Trends
Gradual price inflation throughout the 20-month period reflecting Ethiopian market conditions.

### 3. Competitor Price Tiers
- **Farm**: 30% below baseline (direct from farm)
- **Distribution Center**: Baseline pricing
- **Supermarket**: 30% above baseline (retail premium)

### 4. Customer Behavior Patterns
- **Holiday Season** (Nov-Jan): 80-150 daily transactions
- **Rainy Season** (Jun-Aug): 40-80 daily transactions
- **Normal Season**: 60-120 daily transactions

### 5. Product Knowledge Categories
Each main product includes:
- **Storage**: Proper storage techniques and shelf life
- **Nutrition**: Calorie count and nutritional benefits
- **Recipes**: Usage in Ethiopian cuisine
- **Selection**: How to choose quality products
- **Seasonality**: Peak seasons and price patterns

## Data Quality Metrics

### Transaction Data Quality
- **Completeness**: 100% - All fields populated
- **Consistency**: Validated - No logical inconsistencies
- **Accuracy**: Realistic - Ethiopian market pricing patterns
- **Timeliness**: Current - Up to August 2025

### Pricing Data Quality
- **Coverage**: 100% - All products across all locations
- **Frequency**: Regular - Every 3 days sampling
- **Accuracy**: Market-realistic - Seasonal patterns applied
- **Completeness**: 100% - All required fields present

### Knowledge Base Quality
- **Accuracy**: High - Ethnically appropriate Ethiopian context
- **Completeness**: Comprehensive - Multiple categories per product
- **Usability**: Ready - Formatted for vector embeddings

## Applications

### 1. RAG Pipeline Development
- LLM context retrieval for Gemini 2.5 and other existing LLMs
- Product knowledge base for chatbot responses
- Vector embeddings for semantic search
- Ethiopian market context for AI queries

### 2. Business Intelligence
- Competitor price comparison across 3 tiers
- Seasonal pricing optimization
- Regional price variation analysis
- Dynamic pricing recommendations

### 3. Inventory Management
- Seasonal demand forecasting
- Regional demand patterns
- Supplier performance analysis
- Stock level optimization

### 4. Customer Insights
- Purchase behavior analysis
- Regional preference patterns
- Seasonal buying trends
- Customer lifetime value

### 5. Market Analysis
- Geographic market penetration
- Product performance by region
- Seasonal market trends
- Competitive positioning

## Technical Specifications

### Data Formats
- **Primary**: Excel (.xlsx) with 4 sheets
- **Knowledge Base**: CSV for easy Vector DB import
- **Encoding**: UTF-8 (supports Amharic characters)

### Data Volume
- **Total Records**: 67,103
- **File Size**: ~15MB (Excel)
- **Memory Usage**: ~50MB when loaded

### Dependencies
- Python 3.6+
- pandas
- numpy
- openpyxl

## Usage Examples

### 1. Load Data in Python
```python
import pandas as pd

# Load all sheets
df_transactions = pd.read_excel('synthetic_horticulture_dataset.xlsx', sheet_name='Transactions')
df_pricing = pd.read_excel('synthetic_horticulture_dataset.xlsx', sheet_name='Competitor_Pricing')
df_knowledge = pd.read_excel('product_knowledge_base.csv')

# Load for Vector DB
knowledge_texts = df_knowledge['embedding_text'].tolist()
```

### 2. Analyze Seasonal Trends
```python
# Monthly average prices
monthly_prices = df_pricing.groupby([df_pricing['date'].dt.month, 'product_name'])['price'].mean().unstack()

# Seasonal transaction patterns
df_transactions['month'] = df_transactions['order_date'].dt.month
monthly_transactions = df_transactions.groupby('month')['order_total_amount'].sum()
```

### 3. Regional Analysis
```python
# Regional pricing comparison
regional_prices = df_pricing.groupby(['location_detail', 'product_name'])['price'].mean()

# Regional demand analysis
regional_demand = df_transactions.merge(df_suppliers, left_on='supplier_id', right_on='supplier_id')
```

## Limitations and Considerations

### 1. Synthetic Data
- Generated algorithmically, not from real transactions
- Based on realistic patterns but may not capture all market nuances
- Should be validated against real market data when available

### 2. Price Basis
- Prices in Ethiopian Birr (ETB)
- Based on 2024-2025 market conditions
- Regional variations may not reflect actual transport costs

### 3. Product Coverage
- Focus on horticulture and dairy products
- May not represent complete Ethiopian market
- Some products may have limited regional availability

### 4. Temporal Coverage
- 20 months of data (Jan 2024 - Aug 2025)
- May not capture multi-year cyclical patterns
- External economic factors not modeled

## Data Refresh Strategy

### Recommended Update Frequency
- **Transaction Data**: Daily integration
- **Competitor Pricing**: Weekly collection
- **Knowledge Base**: Monthly review and updates
- **Supplier Information**: Quarterly validation

### Data Validation Rules
- Price ranges within realistic bounds
- Transaction amounts match quantity × unit price
- Geographic consistency checks
- Temporal sequence validation

## Support and Maintenance

This dataset is designed for:
- RAG pipeline development for existing LLMs (Gemini 2.5, etc.)
- Business intelligence dashboard development
- LLM knowledge base population for context retrieval
- Market analysis and research
- Pricing strategy development

For questions or customizations, refer to the synthetic_dataset_generator.py script for modification parameters.

---

**Generated**: October 2025
**Coverage**: 20 months (Jan 2024 - Aug 2025)
**Products**: 24 horticulture and dairy items
**Locations**: 12 Ethiopian regions
**Records**: 67,103 total data points