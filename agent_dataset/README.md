# Ethiopian Horticulture E-commerce Synthetic Dataset

A comprehensive synthetic dataset for Ethiopian horticulture e-commerce operations, covering **20 months of historical data** (January 2024 - August 2025) with realistic seasonal patterns, pricing variations, and customer behavior.

## 🚀 Quick Start

### For RAG Pipeline Integration

```python
import pandas as pd

# Load knowledge base for LLM context
df_knowledge = pd.read_csv('product_knowledge_base.csv')
knowledge_texts = df_knowledge['embedding_text'].tolist()

# Use these texts in your RAG pipeline with Gemini 2.5 or other LLMs
# Example: vectorize and store in your vector database
```

### For Analytics

```python
import pandas as pd

# Load transaction data for analysis
df_transactions = pd.read_excel('synthetic_horticulture_dataset.xlsx',
                                sheet_name='Transactions', engine='openpyxl')
df_pricing = pd.read_excel('synthetic_horticulture_dataset.xlsx',
                           sheet_name='Competitor_Pricing', engine='openpyxl')

# Basic analysis
print(f"Total Revenue: ETB {df_transactions['order_total_amount'].sum():,.2f}")
print(f"Total Orders: {len(df_transactions):,}")
print(f"Date Range: {df_transactions['order_date'].min()} to {df_transactions['order_date'].max()}")
```

## 📊 Dataset Overview

| Component | Records | Description |
|-----------|---------|-------------|
| **Transactions** | 52,427 | Customer orders with product details |
| **Competitor Pricing** | 14,616 | Price tracking across 3 market tiers |
| **Product Knowledge Base** | 56 | Chatbot knowledge entries |
| **Suppliers** | 10 | Supplier information |

## 🛍️ Products Covered

### Horticulture (15 items)
- **Vegetables**: Red Onion (ሃበሻ), Tomato, Potato, Garlic, Carrot, Beetroot, White Cabbage, Green Chili (ስታርታ), Lettuce, Spinach, Cucumber, Bell Pepper, Sweet Potato
- **Fruits**: Avocado, Papaya, Mango, Banana, Orange, Apple

### Dairy (5 items)
- Milk, Yogurt, Cheese (Ayib), Butter, Cream

## 🌍 Geographic Coverage

**12 Ethiopian Locations**:
- Addis Ababa, Dire Dawa
- Tigray - Mekele
- Amhara - Kobo, Bahir Dar
- Oromia - Meki, Jimma, Shashemene, Asella, Adama
- Sidama - Sidama, Dale

## 📈 Key Features

### 🎯 Seasonal Pricing Patterns
- **Realistic seasonal variations** based on Ethiopian growing seasons
- **Competitor price tracking** across Farm, Supermarket, and Distribution Center tiers
- **Inflation trends** throughout the 20-month period

### 📊 Customer Behavior
- **500 unique customers** with realistic purchasing patterns
- **Seasonal demand fluctuations** (higher sales during holidays, lower during rainy seasons)
- **Product preferences** by customer segment

### 🤖 RAG Pipeline Ready
- **Product knowledge base** with storage, nutrition, recipes, and selection tips
- **Vector embeddings ready** format for LLM context retrieval
- **Ethiopian context** with Amharic language support
- **Optimized for Gemini 2.5 and other existing LLMs**

## 🔧 Files Included

- `synthetic_horticulture_dataset.xlsx` - Main dataset with 4 sheets
- `product_knowledge_base.csv` - Knowledge base for Vector DB
- `synthetic_dataset_generator.py` - Dataset generation script
- `data_quality_analysis.py` - Quality analysis and validation
- `usage_examples.py` - Comprehensive usage examples
- `DATASET_DOCUMENTATION.md` - Detailed documentation
- `README.md` - This file

## 💡 Usage Examples

### Business Intelligence
```python
# Monthly revenue trends
df_transactions['order_date'] = pd.to_datetime(df_transactions['order_date'])
monthly_revenue = df_transactions.groupby(df_transactions['order_date'].dt.to_period('M'))['order_total_amount'].sum()

# Top performing products
product_performance = df_transactions.groupby('product_name')['order_total_amount'].sum().sort_values(ascending=False)
```

### Pricing Analysis
```python
# Competitor price comparison
price_comparison = df_pricing.groupby(['product_name', 'source_market_type'])['price'].mean().unstack()

# Regional price variations
regional_prices = df_pricing.groupby('location_detail')['price'].mean()
```

### RAG Pipeline Integration
```python
# Load knowledge base for LLM context retrieval
knowledge_texts = df_knowledge['embedding_text'].tolist()
product_categories = df_knowledge.groupby('product_name')['category'].unique()

# Use in your RAG pipeline:
# 1. Vectorize these texts using your embedding model
# 2. Store in vector database (Pinecone, Chroma, etc.)
# 3. Retrieve relevant context for Gemini 2.5 queries
```

## 🎯 Business Applications

- **RAG Pipeline Development** - Context-aware AI responses
- **Demand Forecasting** - Seasonal trend analysis
- **Price Optimization** - Competitor pricing intelligence
- **Customer Segmentation** - Purchase behavior analysis
- **Inventory Management** - Regional demand patterns
- **Market Expansion** - Geographic opportunity analysis
- **AI Chatbot Integration** - Product knowledge for LLM context

## 📋 Data Quality

✅ **100% Data Completeness** - No missing values
✅ **Validated Relationships** - All data integrity checks passed
✅ **Realistic Patterns** - Based on Ethiopian market conditions
✅ **Temporal Consistency** - Proper date sequencing
✅ **Geographic Accuracy** - Ethiopian regional coverage

## 🛡️ Limitations

- **Synthetic Data** - Generated algorithmically, not from real transactions
- **Price Basis** - Ethiopian Birr (ETB) based on 2024-2025 conditions
- **Product Focus** - Horticulture and dairy products only
- **Temporal Coverage** - 20 months (Jan 2024 - Aug 2025)

## 🤝 Support

For questions, customizations, or issues:
1. Check `DATASET_DOCUMENTATION.md` for detailed specifications
2. Review `usage_examples.py` for implementation patterns
3. Use `data_quality_analysis.py` for validation

## 📄 License

This dataset is generated for educational and development purposes. Please validate against real market data before production use.

---

**Generated**: October 2025
**Coverage**: 20 months of Ethiopian horticulture e-commerce operations
**Purpose**: RAG pipeline development for LLMs (Gemini 2.5, etc.), business intelligence, and market analysis