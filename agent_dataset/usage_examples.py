#!/usr/bin/env python3
"""
Quick Usage Examples for Ethiopian Horticulture Dataset
Demonstrates common data operations and analysis patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime

def load_dataset():
    """Load all components of the dataset"""
    try:
        # Load Excel file first
        xls = pd.ExcelFile('synthetic_horticulture_dataset.xlsx', engine='openpyxl')

        # Load all sheets
        df_transactions = pd.read_excel(xls, sheet_name='Transactions')
        df_suppliers = pd.read_excel(xls, sheet_name='Suppliers')
        df_pricing = pd.read_excel(xls, sheet_name='Competitor_Pricing')
        
        # Use pd.read_csv for CSV files
        df_knowledge = pd.read_csv('product_knowledge_base.csv')

        return {
            'transactions': df_transactions,
            'suppliers': df_suppliers,
            'pricing': df_pricing,
            'knowledge': df_knowledge
        }
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("Make sure synthetic_horticulture_dataset.xlsx and product_knowledge_base.csv are in the current directory")
        raise

def example_1_basic_analysis():
    """Example 1: Basic business metrics analysis"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Business Metrics Analysis")
    print("=" * 60)

    data = load_dataset()
    df = data['transactions']

    # Convert order_date to datetime
    df['order_date'] = pd.to_datetime(df['order_date'])

    # Basic metrics
    total_revenue = df['order_total_amount'].sum()
    total_orders = len(df)
    avg_order_value = df['order_total_amount'].mean()
    unique_customers = df['user_id'].nunique()

    print(f"📊 Business Metrics")
    print(f"Total Revenue: ETB {total_revenue:,.2f}")
    print(f"Total Orders: {total_orders:,}")
    print(f"Average Order Value: ETB {avg_order_value:.2f}")
    print(f"Unique Customers: {unique_customers:,}")

    # Top products by revenue
    product_revenue = df.groupby('product_name')['order_total_amount'].sum().sort_values(ascending=False)
    print(f"\n🏆 Top 5 Products by Revenue:")
    for i, (product, revenue) in enumerate(product_revenue.head().items(), 1):
        print(f"{i}. {product}: ETB {revenue:,.2f}")

    # Monthly growth
    df['month'] = df['order_date'].dt.to_period('M')
    monthly_revenue = df.groupby('month')['order_total_amount'].sum()

    print(f"\n📈 Recent Monthly Performance:")
    for month in monthly_revenue.tail(3).index:
        revenue = monthly_revenue[month]
        print(f"{month}: ETB {revenue:,.2f}")

def example_2_seasonal_analysis():
    """Example 2: Seasonal pricing and demand patterns"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Seasonal Analysis")
    print("=" * 60)

    data = load_dataset()
    df_transactions = data['transactions']
    df_pricing = data['pricing']

    # Convert dates
    df_transactions['order_date'] = pd.to_datetime(df_transactions['order_date'])
    df_pricing['date'] = pd.to_datetime(df_pricing['date'])

    # Analyze seasonal price patterns for key products
    seasonal_products = ['Tomato', 'Avocado', 'Mango', 'Red Onion (ሃበሻ)']

    print(f"🌱 Seasonal Price Patterns")
    print(f"{'Product':<20} {'Peak Season':<12} {'Low Season':<12} {'Price Variation':<15}")
    print("-" * 65)

    for product in seasonal_products:
        # CORRECTED LINE: Use .copy() to avoid SettingWithCopyWarning
        product_data = df_pricing[df_pricing['product_name'] == product].copy()

        # Monthly average prices
        product_data['month'] = product_data['date'].dt.month
        monthly_prices = product_data.groupby('month')['price'].mean()

        peak_month = monthly_prices.idxmax()
        low_month = monthly_prices.idxmin()
        price_variation = (monthly_prices.max() - monthly_prices.min()) / monthly_prices.min() * 100

        print(f"{product:<20} {peak_month:<12} {low_month:<12} {price_variation:<15.1f}%")

    # Seasonal demand patterns
    df_transactions['month'] = df_transactions['order_date'].dt.month
    monthly_orders = df_transactions.groupby('month')['order_id'].count()

    print(f"\n📊 Monthly Order Volume:")
    print(f"{'Month':<10} {'Orders':<10} {'Season':<15}")
    print("-" * 40)

    seasons = {
        'Dry': [10, 11, 12, 1, 2, 3],
        'Rainy': [6, 7, 8, 9],
        'Transition': [4, 5]
    }

    for month in range(1, 13):
        orders = monthly_orders.get(month, 0)
        season = next(k for k, v in seasons.items() if month in v)
        month_name = pd.to_datetime(f'2024-{month:02d}-01').strftime('%B')
        print(f"{month_name:<10} {orders:<10,} {season:<15}")

def example_3_competitor_analysis():
    """Example 3: Competitor pricing analysis"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Competitor Pricing Analysis")
    print("=" * 60)

    data = load_dataset()
    df_pricing = data['pricing']

    # Price comparison by market type
    price_comparison = df_pricing.groupby(['product_name', 'source_market_type'])['price'].mean().unstack()

    print(f"🏪 Competitor Price Comparison (ETB per kg/liter)")
    print(f"{'Product':<20} {'Farm':<10} {'Distribution':<12} {'Supermarket':<12} {'Spread':<10}")
    print("-" * 70)

    for product in price_comparison.index[:8]:  # Show first 8 products
        farm_price = price_comparison.loc[product, 'Farm']
        dist_price = price_comparison.loc[product, 'Distribution Center']
        super_price = price_comparison.loc[product, 'Supermarket']
        spread = super_price - farm_price

        print(f"{product:<20} {farm_price:<10.2f} {dist_price:<12.2f} {super_price:<12.2f} {spread:<10.2f}")

    # Geographic price variations
    geo_prices = df_pricing.groupby('location_detail')['price'].mean().sort_values()

    print(f"\n📍 Geographic Price Variations")
    print(f"{'Location':<25} {'Avg Price':<12}")
    print("-" * 40)

    for location in geo_prices.head().index:
        avg_price = geo_prices[location]
        print(f"{location:<25} {avg_price:<12.2f}")

def example_4_customer_insights():
    """Example 4: Customer behavior analysis"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Customer Behavior Analysis")
    print("=" * 60)

    data = load_dataset()
    df = data['transactions']

    # Convert dates
    df['order_date'] = pd.to_datetime(df['order_date'])

    # Customer segmentation by order value
    customer_spending = df.groupby('user_id')['order_total_amount'].sum().sort_values(ascending=False)

    # Define segments
    high_value_threshold = customer_spending.quantile(0.8)
    medium_value_threshold = customer_spending.quantile(0.5)

    high_value = customer_spending[customer_spending >= high_value_threshold]
    medium_value = customer_spending[(customer_spending >= medium_value_threshold) & (customer_spending < high_value_threshold)]
    low_value = customer_spending[customer_spending < medium_value_threshold]

    print(f"👥 Customer Segmentation")
    print(f"High Value (>=80th percentile): {len(high_value)} customers")
    print(f"Medium Value (50-80th percentile): {len(medium_value)} customers")
    print(f"Low Value (<50th percentile): {len(low_value)} customers")

    # Product preferences by segment
    def get_top_products(customers_df, n=5):
        customer_ids = customers_df.index
        segment_data = df[df['user_id'].isin(customer_ids)]
        return segment_data.groupby('product_name')['order_id'].count().sort_values(ascending=False).head(n)

    print(f"\n🎯 Top Products by Customer Segment")

    segments = [
        ('High Value', high_value),
        ('Medium Value', medium_value),
        ('Low Value', low_value)
    ]

    for segment_name, segment_data in segments:
        print(f"\n{segment_name} Customers:")
        top_products = get_top_products(segment_data)
        for i, (product, orders) in enumerate(top_products.items(), 1):
            print(f"  {i}. {product}: {orders} orders")

    # Repeat purchase analysis
    repeat_customers = df.groupby('user_id')['order_id'].count()
    repeat_rate = (repeat_customers > 1).mean() * 100

    print(f"\n🔄 Customer Loyalty Metrics")
    print(f"Repeat Customer Rate: {repeat_rate:.1f}%")
    print(f"Average Orders per Customer: {repeat_customers.mean():.1f}")

def example_5_knowledge_base_usage():
    """Example 5: Using the knowledge base for chatbot"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Knowledge Base for Chatbot")
    print("=" * 60)

    data = load_dataset()
    df_knowledge = data['knowledge']

    # Sample knowledge queries
    print(f"🤖 Sample Knowledge Base Responses")

    queries = [
        ('storage', 'How should I store avocados?'),
        ('nutrition', 'What are the nutritional benefits of tomatoes?'),
        ('recipes', 'How can I use red onions in Ethiopian cooking?'),
        ('selection', 'How do I choose ripe mangoes?'),
        ('seasonality', 'When is the best time to buy potatoes?')
    ]

    for category, question in queries:
        relevant_knowledge = df_knowledge[df_knowledge['category'] == category]
        if not relevant_knowledge.empty:
            # In a real chatbot, you would use vector similarity here
            sample_answer = relevant_knowledge.iloc[0]['content']
            product = relevant_knowledge.iloc[0]['product_name']

            print(f"\nQ: {question}")
            print(f"A: {sample_answer}")

    # Knowledge base statistics
    print(f"\n📚 Knowledge Base Statistics")
    print(f"Total Entries: {len(df_knowledge)}")
    print(f"Products Covered: {df_knowledge['product_name'].nunique()}")
    print(f"Knowledge Categories: {', '.join(df_knowledge['category'].unique())}")

    # Coverage by product
    coverage = df_knowledge.groupby('product_name')['category'].nunique().sort_values(ascending=False)
    print(f"\n📖 Knowledge Coverage by Product:")
    for product in coverage.head().index:
        categories_count = coverage[product]
        print(f"  {product}: {categories_count} knowledge categories")

def example_6_rag_pipeline_usage():
    """Example 6: RAG Pipeline Usage for LLMs"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: RAG Pipeline Usage for LLMs")
    print("=" * 60)

    data = load_dataset()
    df = data['transactions']
    df_pricing = data['pricing']

    # Convert dates
    df['order_date'] = pd.to_datetime(df['order_date'])
    df_pricing['date'] = pd.to_datetime(df_pricing['date'])

    # RAG Pipeline Usage Examples
    print(f"🤖 RAG Pipeline Implementation Examples")

    # Example: Product query context retrieval
    print(f"\n📚 Context Retrieval for LLM Queries:")

    # Sample queries and their contexts
    sample_queries = [
        "How should I store ripe avocados?",
        "What's the nutritional value of Ethiopian cheese?",
        "When is the best season to buy tomatoes?",
        "How do I select good quality mangoes?",
        "What Ethiopian dishes use red onions?"
    ]

    # Load knowledge base
    df_knowledge = data['knowledge']

    print(f"Sample Query -> Context Retrieval:")
    print("-" * 50)

    for i, query in enumerate(sample_queries[:3], 1):
        # Simple keyword matching (in real RAG, use embeddings)
        query_lower = query.lower()

        # Find relevant knowledge entries
        relevant_entries = []
        for _, row in df_knowledge.iterrows():
            content_lower = row['content'].lower()
            if any(word in content_lower for word in query_lower.split() if len(word) > 3):
                relevant_entries.append(row['content'])

        print(f"\nQuery {i}: {query}")
        print(f"Retrieved Context: {relevant_entries[0] if relevant_entries else 'No direct match found'}")
        print(f"Total Relevant Entries: {len(relevant_entries)}")

    # Vector DB preparation example
    print(f"\n💾 Vector DB Preparation:")
    print(f"Knowledge texts ready for embedding: {len(df_knowledge)} entries")
    print(f"Embedding text field available: {'embedding_text' in df_knowledge.columns}")

    # Sample embedding text
    sample_embedding_text = df_knowledge['embedding_text'].iloc[0]
    print(f"Sample embedding text: '{sample_embedding_text[:100]}...'")

    # Pricing context for LLM
    print(f"\n💰 Real-time Pricing Context:")

    # Current market prices for context
    current_prices = df_pricing[df_pricing['date'] == df_pricing['date'].max()]
    if not current_prices.empty:
        sample_products = current_prices.groupby('product_name')['price'].mean().head(3)
        print(f"Available pricing context for {len(sample_products)} products:")
        for product, price in sample_products.items():
            print(f"  {product}: ETB {price:.2f} per kg/liter")

    print(f"\n🔧 RAG Pipeline Integration Steps:")
    print(f"1. Vectorize knowledge_texts using your embedding model")
    print(f"2. Store embeddings in vector database (Pinecone, Chroma, etc.)")
    print(f"3. Implement semantic search for query matching")
    print(f"4. Retrieve relevant context for Gemini 2.5 or other LLMs")
    print(f"5. Use retrieved context to generate informed responses")

def main():
    """Run all examples"""
    print("🇪🇹 ETHIOPIAN HORTICULTURE DATASET - USAGE EXAMPLES")
    print("=" * 60)

    try:
        example_1_basic_analysis()
        example_2_seasonal_analysis()
        example_3_competitor_analysis()
        example_4_customer_insights()
        example_5_knowledge_base_usage()
        example_6_rag_pipeline_usage()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("💡 Use these patterns for RAG pipeline development with existing LLMs")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        print("Make sure synthetic_horticulture_dataset.xlsx is in the current directory")

if __name__ == "__main__":
    main()
