#!/usr/bin/env python3
"""
Dashboard Demo Script - Creates items to demonstrate real-time updates

This script creates items at regular intervals to show how the dashboard
updates in real-time using HTMX.
"""

import requests
import time
import random
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/items"

DEMO_ITEMS = [
    {"name": "Widget Pro", "description": "Professional-grade widget for enterprise use"},
    {"name": "Smart Sensor", "description": "IoT sensor with advanced analytics capabilities"},
    {"name": "Data Processor", "description": "High-performance data processing unit"},
    {"name": "Cloud Connector", "description": "Seamless cloud integration module"},
    {"name": "AI Assistant", "description": "Intelligent automation helper"},
    {"name": "Security Shield", "description": "Advanced cybersecurity protection system"},
    {"name": "Performance Monitor", "description": "Real-time system performance tracking"},
    {"name": "Analytics Engine", "description": "Powerful data analytics and visualization"},
    {"name": "Mobile Gateway", "description": "Cross-platform mobile application interface"},
    {"name": "Database Optimizer", "description": "Automated database performance tuning"}
]

def create_demo_item():
    """Create a single demo item with random data"""
    base_item = random.choice(DEMO_ITEMS)
    timestamp = datetime.now().strftime("%H:%M:%S")

    item_data = {
        "name": f"{base_item['name']} #{random.randint(100, 999)}",
        "description": f"{base_item['description']} (Created at {timestamp})"
    }

    try:
        response = requests.post(API_URL, json=item_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created: {result['name']} (ID: {result['id']})")
            return True
        else:
            print(f"❌ Failed to create item: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main demo function"""
    print("🚀 Dashboard Demo Script")
    print("=" * 50)
    print("This script will create items every 3 seconds to demonstrate")
    print("real-time dashboard updates. Keep your browser open to see the changes!")
    print()
    print("Dashboard URL: http://localhost:8000")
    print()

    count = 0  # Initialize counter at function level

    try:
        # Test API connection first
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not responding. Make sure the server is running.")
            return

        print("✅ API connection successful!")
        print()
        print("Creating demo items... (Press Ctrl+C to stop)")
        print("-" * 40)

        while True:
            success = create_demo_item()
            if success:
                count += 1
                print(f"📊 Total items created: {count}")

            print("⏳ Waiting 3 seconds before next item...")
            print()
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n\n🛑 Demo stopped by user")
        print(f"📊 Total items created: {count}")
        print("✨ Check your dashboard to see the final results!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print(f"📊 Total items created: {count}")

if __name__ == "__main__":
    main()
