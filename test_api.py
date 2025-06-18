#!/usr/bin/env python3
"""
API Test Script - Send multiple POST requests to the FastAPI

This script sends a specified number of POST requests to the API
with random data for testing purposes.

Usage:
    python test_api.py              # Interactive mode
    python test_api.py 10           # Send 10 requests with 0 delay
    python test_api.py --help       # Show help message

API URL Configuration (priority order):
    1. Uses CONNECT_SERVER + CONNECT_APP_ID from .env to construct deployed app URL
    2. Falls back to API_BASE_URL environment variable if set explicitly
    3. Defaults to http://127.0.0.1:8000 (localhost)

Examples:
    # Test deployed app (automatically uses .env values)
    python test_api.py

    # Test localhost (override .env)
    API_BASE_URL=http://127.0.0.1:8000 python test_api.py

    # Test different deployed app
    API_BASE_URL=https://other-server.com/content/app-id python test_api.py

Features:
- Command line argument support for automation
- Automatic .env file loading for deployed app testing
- Request timing and performance statistics
- Authorization header support via CONNECT_API_KEY environment variable
- Random test data generation
- Comprehensive reporting
"""

import requests
import random
import time
import json
import os
import sys
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
# Construct API_BASE_URL from CONNECT_SERVER and CONNECT_APP_ID if both are available
CONNECT_SERVER = os.getenv("CONNECT_SERVER")
CONNECT_APP_ID = os.getenv("CONNECT_APP_ID")

if CONNECT_SERVER and CONNECT_APP_ID:
    # Use values from .env to construct the deployed app URL
    API_BASE_URL = f"{CONNECT_SERVER}/content/{CONNECT_APP_ID}"
    print(f"Using API from .env: {API_BASE_URL}")
else:
    # Fall back to explicit API_BASE_URL env var, or default to localhost
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    print(f"Using API: {API_BASE_URL}")

API_ENDPOINT = f"{API_BASE_URL}/api/v1/items"

# Sample data for generating random content
SAMPLE_NAMES = [
    "Widget",
    "Gadget",
    "Tool",
    "Device",
    "Component",
    "Module",
    "System",
    "Product",
    "Item",
    "Object",
    "Element",
    "Unit",
    "Piece",
    "Article",
]

SAMPLE_DESCRIPTIONS = [
    "A high-quality product",
    "An innovative solution",
    "A reliable component",
    "A versatile tool",
    "An essential item",
    "A premium device",
    "A cutting-edge system",
    "A robust solution",
    "A flexible module",
    "An efficient component",
]


def generate_random_item() -> dict:
    """Generate a random item with name and description containing random numbers"""
    random_num = random.randint(1, 10000)

    name = f"{random.choice(SAMPLE_NAMES)} #{random_num}"
    description = f"{random.choice(SAMPLE_DESCRIPTIONS)} - Model {random.randint(100, 999)}"

    return {"name": name, "description": description}


def send_post_request(item_data: dict, request_num: int) -> Tuple[Optional[dict], float]:
    """Send a single POST request to the API"""
    start_time = time.time()

    try:
        print(f"Request #{request_num}: Sending POST to {API_ENDPOINT}")
        print(f"  Data: {json.dumps(item_data, indent=2)}")

        # Prepare headers
        headers = {"Content-Type": "application/json"}

        # Add Authorization header if CONNECT_API_KEY is set
        api_key = os.getenv("CONNECT_API_KEY")
        if api_key:
            # headers["Authorization"] = f"Key {api_key}"
            headers["Authorization"] = api_key
            print(f"  🔑 Using API key from CONNECT_API_KEY environment variable")
        else:
            print(f"  ⚠️  No CONNECT_API_KEY found in environment - proceeding without auth")

        response = requests.post(API_ENDPOINT, json=item_data, headers=headers, timeout=10)

        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Success! Created item with ID: {result.get('id')} (took {elapsed_time:.3f}s)")
            print(f"  Response: {json.dumps(result, indent=2)}")
            return result, elapsed_time
        else:
            print(f"  ❌ Error! Status: {response.status_code} (took {elapsed_time:.3f}s)")
            print(f"  Response: {response.text}")
            return None, elapsed_time

    except requests.exceptions.RequestException as e:
        elapsed_time = time.time() - start_time
        print(f"  ❌ Request failed: {e} (took {elapsed_time:.3f}s)")
        return None, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"  ❌ Unexpected error: {e} (took {elapsed_time:.3f}s)")
        return None, elapsed_time


def test_api_multiple_requests(num_requests: int, delay_seconds: float = 0.5):
    """Send multiple POST requests to the API"""
    print(f"🚀 Starting API test with {num_requests} requests")
    print(f"📡 Target endpoint: {API_ENDPOINT}")
    print(f"⏱️  Delay between requests: {delay_seconds} seconds")

    # Check for API key
    api_key = os.getenv("CONNECT_API_KEY")
    if api_key:
        print(f"🔑 Authorization: Using API key (***{api_key[-4:]})")
    else:
        print(f"⚠️  Authorization: No CONNECT_API_KEY environment variable found")

    print("-" * 60)

    successful_requests = 0
    failed_requests = 0
    created_items = []
    request_times = []

    for i in range(1, num_requests + 1):
        # Generate random item data
        item_data = generate_random_item()

        # Send the request
        result, elapsed_time = send_post_request(item_data, i)
        request_times.append(elapsed_time)

        if result:
            successful_requests += 1
            created_items.append(result)
        else:
            failed_requests += 1

        # Add delay between requests (except for the last one)
        if i < num_requests:
            time.sleep(delay_seconds)

        print("-" * 40)

    # Calculate timing statistics
    avg_time = sum(request_times) / len(request_times) if request_times else 0
    min_time = min(request_times) if request_times else 0
    max_time = max(request_times) if request_times else 0

    # Summary
    print(f"\n📊 Test Summary:")
    print(f"  Total requests: {num_requests}")
    print(f"  Successful: {successful_requests}")
    print(f"  Failed: {failed_requests}")
    print(f"  Success rate: {(successful_requests/num_requests)*100:.1f}%")
    print(f"\n⏱️  Timing Statistics:")
    print(f"  Average time per request: {avg_time:.3f} seconds")
    print(f"  Minimum time: {min_time:.3f} seconds")
    print(f"  Maximum time: {max_time:.3f} seconds")

    # if created_items:
    #     print(f"\n📝 Created Items Summary:")
    #     for item in created_items:
    #         print(f"  - ID {item.get('id')}: {item.get('name')}")


def main():
    """Main function with command line argument support"""
    print("🔧 FastAPI Test Script")
    print("=" * 50)

    # Check for API key at startup
    api_key = os.getenv("CONNECT_API_KEY")
    if not api_key:
        print("⚠️  Warning: CONNECT_API_KEY environment variable not found!")
        print("   If your API requires authentication, set it with:")
        print("   export CONNECT_API_KEY=your_api_key_here")
        print()

    try:
        # Declare global variables at the start of the function
        global API_BASE_URL, API_ENDPOINT

        # Check for command line argument
        if len(sys.argv) > 1:
            # Check for help request
            if sys.argv[1] in ["-h", "--help", "help"]:
                print("Usage: python test_api.py [number_of_requests]")
                print()
                print("Arguments:")
                print("  number_of_requests    Number of POST requests to send (uses 0 delay)")
                print()
                print("Examples:")
                print("  python test_api.py        # Interactive mode")
                print("  python test_api.py 10     # Send 10 requests with 0 delay")
                print("  python test_api.py 100    # Send 100 requests with 0 delay")
                print()
                print("Environment Variables:")
                print("  CONNECT_API_KEY          API key for authentication")
                return

            # Use command line argument for number of requests
            try:
                num_requests = int(sys.argv[1])
                delay = 0  # Use 0 delay when command line argument is provided
                print(f"📝 Using command line argument: {num_requests} requests with 0 delay")

                # # Still allow URL customization via input
                # custom_url = input(f"Enter API base URL (default: {API_BASE_URL}): ").strip()
                # if custom_url:
                #     API_BASE_URL = custom_url.rstrip("/")
                #     API_ENDPOINT = f"{API_BASE_URL}/api/v1/items"

                print(f"\n🎯 Configuration:")
                print(f"  Requests: {num_requests}")
                print(f"  Delay: {delay}s")
                print(f"  URL: {API_ENDPOINT}")

                # Auto-proceed when using command line arguments
                print("▶️  Auto-proceeding with command line configuration...")

            except ValueError:
                print(f"❌ Invalid command line argument: '{sys.argv[1]}' is not a valid number")
                print("Usage: python test_api.py [number_of_requests]")
                print("Use 'python test_api.py --help' for more information")
                return
        else:
            # Interactive mode - get input from user
            num_requests = input("Enter number of POST requests to send (default: 5): ").strip()
            num_requests = int(num_requests) if num_requests else 5

            # Get delay between requests
            delay = input("Enter delay between requests in seconds (default: 0.5): ").strip()
            delay = float(delay) if delay else 0.5

            # Get custom API URL if needed
            custom_url = input(f"Enter API base URL (default: {API_BASE_URL}): ").strip()
            if custom_url:
                API_BASE_URL = custom_url.rstrip("/")
                API_ENDPOINT = f"{API_BASE_URL}/api/v1/items"

            print(f"\n🎯 Configuration:")
            print(f"  Requests: {num_requests}")
            print(f"  Delay: {delay}s")
            print(f"  URL: {API_ENDPOINT}")

            confirm = input(f"\nProceed with test? (y/N): ").strip().lower()
            if confirm not in ["y", "yes"]:
                print("❌ Test cancelled.")
                return

        # Run the test
        test_api_multiple_requests(num_requests, delay)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
