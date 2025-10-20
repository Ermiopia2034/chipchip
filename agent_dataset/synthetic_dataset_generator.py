#!/usr/bin/env python3
"""
Synthetic Dataset Generator for Ethiopian Horticulture E-commerce Bot
Expands existing dataset to cover 1+ year of historical operations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid
import json

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

class SyntheticDatasetGenerator:
    def __init__(self):
        # Base products from existing dataset + additional horticulture/dairy items
        self.base_products = [
            # Vegetables (from existing)
            'Potato', 'Red Onion (ሃበሻ)', 'White Cabbage', 'Garlic',
            'Green Chili (ስታርታ)', 'Tomato', 'Beetroot', 'Carrot',

            # Fruits (from existing + additions)
            'Avocado', 'Papaya', 'Mango', 'Banana', 'Orange', 'Apple',

            # Additional horticulture items
            'Lettuce', 'Spinach', 'Cucumber', 'Bell Pepper', 'Sweet Potato',

            # Dairy items (new additions)
            'Milk', 'Yogurt', 'Cheese (Ayib)', 'Butter', 'Cream'
        ]

        # Ethiopian regions
        self.regions = [
            'Tigray - Mekele', 'Amhara - Kobo', 'Oromia - Meki',
            'Oromia - Jimma', 'Sidama - Sidama', 'Oromia - Shashemene',
            'Oromia - Asella', 'Sidama - Dale', 'Amhara - Bahir Dar',
            'Oromia - Adama', 'Addis Ababa', 'Dire Dawa'
        ]

        # Supplier names (expanded from existing)
        self.supplier_names = [
            'alem', 'lema', 'kasu', 'girma', 'mesfin',
            'bekele', 'tadesse', 'worku', 'habte', 'kaleb'
        ]

        # Competitor tiers (matching benchmark dataset)
        self.competitor_tiers = ['Farm', 'Supermarket', 'Distribution Center']

        # Base prices per kg/liter (Ethiopian Birr)
        self.base_prices = {
            'Potato': 25, 'Red Onion (ሃበሻ)': 35, 'White Cabbage': 20, 'Garlic': 80,
            'Green Chili (ስታርታ)': 45, 'Tomato': 30, 'Beetroot': 25, 'Carrot': 28,
            'Avocado': 60, 'Papaya': 40, 'Mango': 55, 'Banana': 35, 'Orange': 30,
            'Apple': 65, 'Lettuce': 22, 'Spinach': 35, 'Cucumber': 25,
            'Bell Pepper': 40, 'Sweet Potato': 20, 'Milk': 45, 'Yogurt': 55,
            'Cheese (Ayib)': 120, 'Butter': 180, 'Cream': 200
        }

        # Seasonal factors for products (1.0 = normal, >1.0 = higher price in season)
        self.seasonal_factors = {
            'Tomato': {'peak_months': [10, 11, 12], 'factor': 0.8, 'low_months': [6, 7, 8], 'factor_low': 1.3},
            'Avocado': {'peak_months': [9, 10, 11], 'factor': 0.7, 'low_months': [3, 4, 5], 'factor_low': 1.4},
            'Mango': {'peak_months': [5, 6, 7], 'factor': 0.6, 'low_months': [11, 12, 1], 'factor_low': 1.5},
            'Banana': {'peak_months': [4, 5, 6, 7], 'factor': 0.8, 'low_months': [11, 12, 1, 2], 'factor_low': 1.2},
            'Red Onion (ሃበሻ)': {'peak_months': [10, 11, 12, 1], 'factor': 0.7, 'low_months': [5, 6, 7], 'factor_low': 1.4},
            'Potato': {'peak_months': [11, 12, 1, 2], 'factor': 0.8, 'low_months': [6, 7, 8], 'factor_low': 1.3},
        }

    def generate_seasonal_price(self, product, date):
        """Generate price with seasonal variation"""
        base_price = self.base_prices[product]
        month = date.month

        if product in self.seasonal_factors:
            season_info = self.seasonal_factors[product]
            if month in season_info['peak_months']:
                price_factor = season_info['factor']
            elif month in season_info['low_months']:
                price_factor = season_info['factor_low']
            else:
                price_factor = 1.0
        else:
            # Small random variation for non-seasonal products
            price_factor = np.random.normal(1.0, 0.1)

        # Add random noise and inflation trend
        inflation_factor = 1.0 + (date - datetime(2024, 1, 1)).days * 0.0001
        random_factor = np.random.normal(1.0, 0.05)

        final_price = base_price * price_factor * inflation_factor * random_factor
        return max(final_price, base_price * 0.5)  # Minimum 50% of base price

    def generate_competitor_pricing_history(self):
        """Generate 1+ year of competitor pricing data"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2025, 8, 31)
        current_date = start_date

        pricing_data = []

        while current_date <= end_date:
            for product in self.base_products:
                for tier in self.competitor_tiers:
                    # Tier-specific price adjustments
                    tier_multiplier = {
                        'Farm': 0.7,  # Farm prices (lowest)
                        'Supermarket': 1.3,  # Supermarket premiums
                        'Distribution Center': 1.0  # Baseline
                    }[tier]

                    base_price = self.generate_seasonal_price(product, current_date)
                    final_price = base_price * tier_multiplier * np.random.normal(1.0, 0.08)

                    # Random location
                    location = random.choice(self.regions)

                    pricing_data.append({
                        'date': current_date.date(),
                        'product_id': str(uuid.uuid4()),
                        'product_name': product,
                        'price': round(final_price, 2),
                        'source_market_type': tier,
                        'location_detail': location,
                        'product_remark': f'{product} pricing data',
                        'created_at': current_date.strftime('%Y-%m-%d %H:%M:%S')
                    })

            # Move to next date (sample every 3 days for manageable dataset size)
            current_date += timedelta(days=3)

        return pd.DataFrame(pricing_data)

    def generate_transaction_history(self):
        """Generate 1+ year of transaction data with seasonal trends"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2025, 8, 31)
        current_date = start_date

        transactions = []

        # Generate customer base
        customer_base = []
        for i in range(500):  # 500 regular customers
            customer_base.append({
                'user_id': str(uuid.uuid4()),
                'user_name': f'Customer_{i}',
                'phone': f'2519{random.randint(10000000, 99999999)}',
                'preferred_products': random.sample(self.base_products, random.randint(1, 5))
            })

        # Generate suppliers
        suppliers = []
        for name in self.supplier_names:
            suppliers.append({
                'supplier_id': str(uuid.uuid4()),
                'supplier_name': name,
                'specialty_products': random.sample(self.base_products, random.randint(3, 8))
            })

        daily_transactions = 0
        while current_date <= end_date:
            # Seasonal demand patterns
            month = current_date.month
            if month in [11, 12, 1]:  # Holiday season
                daily_transactions = random.randint(80, 150)
            elif month in [6, 7, 8]:  # Rainy season
                daily_transactions = random.randint(40, 80)
            else:
                daily_transactions = random.randint(60, 120)

            # Generate daily transactions
            for _ in range(daily_transactions):
                customer = random.choice(customer_base)
                supplier = random.choice(suppliers)

                # Choose product (prefer customer's preferred products)
                if random.random() < 0.7:  # 70% chance of preferred product
                    product = random.choice(customer['preferred_products'])
                else:
                    product = random.choice(self.base_products)

                # Generate quantity (kg or liters)
                if product in ['Milk', 'Yogurt', 'Butter', 'Cream']:
                    quantity = round(random.uniform(0.5, 5.0), 1)  # Liters
                    unit = 'liters'
                else:
                    quantity = round(random.uniform(0.5, 10.0), 1)  # KG
                    unit = 'kg'

                # Calculate price
                unit_price = self.generate_seasonal_price(product, current_date)
                total_amount = round(quantity * unit_price, 2)

                # Random time during business hours
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                order_datetime = current_date.replace(hour=hour, minute=minute)

                transactions.append({
                    'order_id': str(uuid.uuid4()),
                    'order_date': order_datetime,
                    'user_id': customer['user_id'],
                    'user_name': customer['user_name'],
                    'phone': customer['phone'],
                    'supplier_id': supplier['supplier_id'],
                    'product_id': str(uuid.uuid4()),
                    'product_name': product,
                    'quantity_ordered': quantity,
                    'unit': unit,
                    'price_per_unit': round(unit_price, 2),
                    'order_total_amount': total_amount
                })

            current_date += timedelta(days=1)

        return pd.DataFrame(transactions), pd.DataFrame(suppliers)

    def generate_product_knowledge_base(self):
        """Generate product knowledge base for Vector DB"""
        knowledge_base = []

        product_info = {
            'Red Onion (ሃበሻ)': {
                'storage': 'Store in cool, dry place with good air circulation. Can last 2-3 months when properly stored.',
                'nutrition': 'Rich in vitamin C, vitamin B6, and antioxidants. Low in calories, about 40 calories per 100g.',
                'recipes': 'Essential for Ethiopian dishes like Doro Wat, Shiro, and Tibs. Can be used raw in salads or cooked.',
                'selection': 'Choose firm onions with dry, papery skin. Avoid soft spots or sprouting onions.',
                'seasonality': 'Peak season: October to January. Lower prices during harvest, higher in rainy season.'
            },
            'Tomato': {
                'storage': 'Store at room temperature until ripe, then refrigerate. Use within 1 week after ripening.',
                'nutrition': 'High in vitamin C, potassium, and lycopene. About 18 calories per 100g.',
                'recipes': 'Perfect for salads, sauces, and stews. Key ingredient in Ethiopian Sega Wat.',
                'selection': 'Choose bright red, firm tomatoes. Avoid bruises or soft spots.',
                'seasonality': 'Best quality during dry seasons. Prices increase in rainy months.'
            },
            'Avocado': {
                'storage': 'Store at room temperature until ripe, then refrigerate 2-3 days.',
                'nutrition': 'Rich in healthy fats, fiber, and potassium. About 160 calories per 100g.',
                'recipes': 'Great in salads, sandwiches, or as a spread. Can be used in smoothies.',
                'selection': 'Choose avocados that yield to gentle pressure. Avoid very soft ones.',
                'seasonality': 'Peak season: September to November. Best quality and prices during this period.'
            },
            'Mango': {
                'storage': 'Store at room temperature until ripe, then refrigerate 3-5 days.',
                'nutrition': 'High in vitamin C and vitamin A. About 60 calories per 100g.',
                'recipes': 'Excellent fresh, in juices, or desserts. Popular during Ethiopian summer.',
                'selection': 'Choose fragrant mangoes that give slightly to pressure. Avoid wrinkled skin.',
                'seasonality': 'Peak season: May to July. Abundant and affordable during this time.'
            },
            'Milk': {
                'storage': 'Refrigerate immediately. Use within 5-7 days of opening.',
                'nutrition': 'Excellent source of calcium, protein, and vitamin D. About 42 calories per 100ml.',
                'recipes': 'Used in Ethiopian coffee, tea, and for making traditional dishes.',
                'selection': 'Check expiration date. Choose fresh milk with proper refrigeration.',
                'seasonality': 'Generally consistent pricing year-round with slight variations.'
            },
            'Cheese (Ayib)': {
                'storage': 'Refrigerate in sealed container. Use within 2 weeks.',
                'nutrition': 'High in protein and calcium. About 280 calories per 100g.',
                'recipes': 'Traditional Ethiopian cheese. Served with injera, in salads, or as side dish.',
                'selection': 'Choose white, fresh cheese without off-odors. Should be firm but not hard.',
                'seasonality': 'Consistent availability. Prices may vary with milk production cycles.'
            },
            'Potato': {
                'storage': 'Store in cool, dark place. Avoid refrigeration as it affects texture.',
                'nutrition': 'Good source of vitamin C, potassium, and fiber. About 77 calories per 100g.',
                'recipes': 'Versatile for boiling, baking, frying. Used in Ethiopian potato salads.',
                'selection': 'Choose firm potatoes without green spots or sprouts.',
                'seasonality': 'Best availability after main harvest. Peak season: November to February.'
            },
            'Banana': {
                'storage': 'Store at room temperature. Can refrigerate when ripe to extend life.',
                'nutrition': 'Rich in potassium and vitamin B6. About 89 calories per 100g.',
                'recipes': 'Great as snack, in smoothies, or desserts. Popular with Ethiopian coffee.',
                'selection': 'Choose yellow bananas with brown speckles for optimal ripeness.',
                'seasonality': 'Available year-round with peak supplies during summer months.'
            }
        }

        # Generate knowledge base entries
        for product, info in product_info.items():
            for category, content in info.items():
                knowledge_base.append({
                    'product_name': product,
                    'category': category,
                    'content': content,
                    'embedding_text': f'{product} {category}: {content}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        # Add general information for other products
        other_products = [p for p in self.base_products if p not in product_info]
        for product in other_products:
            knowledge_base.append({
                'product_name': product,
                'category': 'general',
                'content': f'Fresh {product} available in Ethiopian markets. Quality varies by season. Store properly for maximum freshness.',
                'embedding_text': f'{product}: Fresh produce available in Ethiopian markets with seasonal quality variations.',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        return pd.DataFrame(knowledge_base)

    def generate_complete_dataset(self):
        """Generate all components of the synthetic dataset"""
        print("Generating synthetic dataset...")

        print("1. Generating competitor pricing history...")
        competitor_pricing = self.generate_competitor_pricing_history()

        print("2. Generating transaction history...")
        transactions, suppliers = self.generate_transaction_history()

        print("3. Generating product knowledge base...")
        knowledge_base = self.generate_product_knowledge_base()

        print("4. Creating summary statistics...")
        summary_stats = {
            'dataset_generated': datetime.now().isoformat(),
            'date_range': {
                'start': '2024-01-01',
                'end': '2025-08-31'
            },
            'transaction_count': len(transactions),
            'product_count': len(self.base_products),
            'supplier_count': len(suppliers),
            'competitor_price_points': len(competitor_pricing),
            'knowledge_entries': len(knowledge_base),
            'geographic_coverage': self.regions,
            'competitor_tiers': self.competitor_tiers
        }

        return {
            'transactions': transactions,
            'suppliers': suppliers,
            'competitor_pricing': competitor_pricing,
            'knowledge_base': knowledge_base,
            'summary_stats': summary_stats
        }

if __name__ == "__main__":
    generator = SyntheticDatasetGenerator()
    dataset = generator.generate_complete_dataset()

    # Save to Excel files
    print("\nSaving dataset files...")
    with pd.ExcelWriter('synthetic_horticulture_dataset.xlsx', engine='openpyxl') as writer:
        dataset['transactions'].to_excel(writer, sheet_name='Transactions', index=False)
        dataset['suppliers'].to_excel(writer, sheet_name='Suppliers', index=False)
        dataset['competitor_pricing'].to_excel(writer, sheet_name='Competitor_Pricing', index=False)
        dataset['knowledge_base'].to_excel(writer, sheet_name='Product_Knowledge_Base', index=False)

        # Create summary sheet
        summary_df = pd.DataFrame([dataset['summary_stats']])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Save knowledge base as CSV for easy import
    dataset['knowledge_base'].to_csv('product_knowledge_base.csv', index=False)

    print(f"\nDataset generation complete!")
    print(f"- Transactions: {len(dataset['transactions']):,} records")
    print(f"- Competitor Pricing: {len(dataset['competitor_pricing']):,} records")
    print(f"- Knowledge Base: {len(dataset['knowledge_base'])} entries")
    print(f"- Suppliers: {len(dataset['suppliers'])} records")
    print(f"- Date Range: Jan 1, 2024 to Aug 31, 2025 (20 months)")
    print(f"- Products: {len(generator.base_products)} items")
    print(f"- Regions: {len(generator.regions)} Ethiopian locations")
    print(f"\nFiles saved:")
    print("- synthetic_horticulture_dataset.xlsx (complete dataset)")
    print("- product_knowledge_base.csv (knowledge base for Vector DB)")