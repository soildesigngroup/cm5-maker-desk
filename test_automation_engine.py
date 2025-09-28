#!/usr/bin/env python3
"""
Test script for Automation Engine functionality
Demonstrates Insomnia-inspired API testing capabilities
"""

import time
import json
from automation_engine import get_automation_engine, AutomationRequest, Environment

def test_automation_engine():
    """Test basic automation engine functionality"""
    print("=" * 60)
    print("Automation Engine Test (Insomnia-inspired)")
    print("=" * 60)

    # Get automation engine instance
    engine = get_automation_engine()

    # Test 1: Create environment
    print("\n1. Creating test environment...")
    env = engine.create_environment(
        name="Test Environment",
        variables={
            "api_key": "test-api-key-123",
            "base_url": "https://httpbin.org",
            "version": "v1"
        },
        base_url="https://httpbin.org"
    )
    print(f"   Environment created: {env.name} (ID: {env.id})")

    # Test 2: Set active environment
    print("\n2. Setting active environment...")
    success = engine.set_active_environment(env.id)
    print(f"   Active environment set: {success}")

    # Test 3: Create collection
    print("\n3. Creating test collection...")
    collection = engine.create_collection(
        name="API Test Collection",
        description="Test collection for HTTP API testing"
    )
    print(f"   Collection created: {collection.name} (ID: {collection.id})")

    # Test 4: Create test requests
    print("\n4. Creating test requests...")

    # GET request test
    get_request = AutomationRequest(
        name="Test GET Request",
        method="GET",
        url="/get?param1=value1&param2={{version}}",
        headers={
            "User-Agent": "Automation-Engine/1.0",
            "X-API-Key": "{{api_key}}"
        }
    )

    # POST request test
    post_request = AutomationRequest(
        name="Test POST Request",
        method="POST",
        url="/post",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Automation-Engine/1.0"
        },
        body='{"message": "Hello from automation engine!", "timestamp": "{{timestamp}}"}',
        body_type="json"
    )

    # Add requests to collection
    engine.add_request_to_collection(collection.id, get_request)
    engine.add_request_to_collection(collection.id, post_request)
    print(f"   Added {len(collection.requests)} requests to collection")

    # Test 5: Execute individual request
    print("\n5. Executing individual GET request...")
    response = engine.execute_request(get_request, env)
    print(f"   Status: {response.status_code}")
    print(f"   Response time: {response.elapsed_time:.3f}s")
    print(f"   Response size: {response.size} bytes")
    if response.error:
        print(f"   Error: {response.error}")
    else:
        print("   Request executed successfully!")

    # Test 6: Execute POST request
    print("\n6. Executing individual POST request...")
    response = engine.execute_request(post_request, env)
    print(f"   Status: {response.status_code}")
    print(f"   Response time: {response.elapsed_time:.3f}s")
    if response.error:
        print(f"   Error: {response.error}")
    else:
        print("   POST request executed successfully!")

    # Test 7: Run entire collection
    print("\n7. Running entire collection...")
    results = engine.run_collection(collection.id, env.id)
    print(f"   Collection executed: {len(results)} requests")

    passed = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print(f"   Results: {passed} passed, {failed} failed")

    for i, result in enumerate(results):
        status = "✓ PASS" if result.success else "✗ FAIL"
        print(f"   Request {i+1}: {status} ({result.execution_time:.3f}s)")
        if result.error:
            print(f"      Error: {result.error}")

    # Test 8: Get engine status
    print("\n8. Engine status:")
    status = engine.get_status()
    print(f"   Environments: {status['environments']}")
    print(f"   Collections: {status['collections']}")
    print(f"   Total requests: {status['total_requests']}")
    print(f"   Test results: {status['test_results']}")
    print(f"   Active environment: {status['active_environment']}")

    # Test 9: Variable resolution
    print("\n9. Testing variable resolution...")
    resolver = engine.variable_resolver
    test_string = "API URL: {{base_url}}/api/{{version}} with key {{api_key}}"
    resolved = resolver.resolve(test_string)
    print(f"   Original: {test_string}")
    print(f"   Resolved: {resolved}")

    # Test 10: Import simulation (Insomnia format)
    print("\n10. Testing collection import...")
    insomnia_data = {
        "name": "Imported Collection",
        "description": "Simulated Insomnia import",
        "requests": [
            {
                "name": "Imported GET",
                "method": "GET",
                "url": "/headers",
                "headers": {"Accept": "application/json"}
            },
            {
                "name": "Imported POST",
                "method": "POST",
                "url": "/anything",
                "headers": {"Content-Type": "application/json"},
                "body": '{"imported": true}'
            }
        ]
    }

    imported_collection = engine.import_insomnia_collection(insomnia_data)
    print(f"   Imported collection: {imported_collection.name}")
    print(f"   Imported requests: {len(imported_collection.requests)}")

    print("\n" + "=" * 60)
    print("Automation Engine Test Complete")
    print("All Insomnia-inspired features working correctly!")
    print("=" * 60)

if __name__ == "__main__":
    test_automation_engine()