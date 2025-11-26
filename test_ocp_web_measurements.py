#!/usr/bin/env python3
"""
Test script for ocp_web measurement functionality
"""

import requests
import json
import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocp_web.backend import ViewerBackend, Tool

def test_backend():
    """Test the ViewerBackend directly"""
    print("Testing ViewerBackend...")
    
    backend = ViewerBackend()
    backend.initialize_with_logo()
    
    # Test getting available shapes
    shapes = backend.get_available_shapes()
    print(f"Available shapes: {shapes}")
    
    if shapes:
        # Test properties measurement
        result = backend.get_properties(shapes[0])
        print(f"Properties result: {result}")
        
        # Test distance measurement (if we have at least 2 shapes)
        if len(shapes) >= 2:
            result = backend.get_distance(shapes[0], shapes[1], False)
            print(f"Distance result: {result}")
    
    print("Backend test completed.\n")

def test_api_endpoints():
    """Test the HTTP API endpoints"""
    print("Testing HTTP API endpoints...")
    
    base_url = "http://localhost:5000"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        
        # Test getting available shapes
        response = requests.get(f"{base_url}/api/measure/shapes")
        print(f"Available shapes: {response.status_code} - {response.json()}")
        
        # Test setting active tool
        response = requests.post(f"{base_url}/api/tool/distance")
        print(f"Set tool to distance: {response.status_code} - {response.json()}")
        
        response = requests.post(f"{base_url}/api/tool/none")
        print(f"Set tool to none: {response.status_code} - {response.json()}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure the server is running on localhost:5000")
    except Exception as e:
        print(f"Error testing API: {e}")
    
    print("API test completed.\n")

def test_with_simple_model():
    """Test with a simple model upload"""
    print("Testing with simple model...")
    
    base_url = "http://localhost:5000"
    
    # Create a simple test model (similar to logo structure)
    test_model = {
        "parts": [
            {
                "id": "test_shape_1",
                "name": "Test Shape 1",
                "shape": {
                    "obj": "AQIDBA=="  # Simple base64 encoded dummy data
                },
                "loc": None
            },
            {
                "id": "test_shape_2", 
                "name": "Test Shape 2",
                "shape": {
                    "obj": "AQIDBA=="  # Simple base64 encoded dummy data
                },
                "loc": None
            }
        ]
    }
    
    try:
        # Upload model
        response = requests.post(f"{base_url}/api/model", json=test_model)
        print(f"Model upload: {response.status_code} - {response.json()}")
        
        if response.status_code == 200:
            # Test measurements on uploaded model
            response = requests.get(f"{base_url}/api/measure/shapes")
            shapes_data = response.json()
            print(f"Shapes after upload: {shapes_data}")
            
            if shapes_data.get('success') and len(shapes_data['shapes']) >= 2:
                # Test distance measurement
                response = requests.post(f"{base_url}/api/measure/distance", json={
                    "shape_id1": shapes_data['shapes'][0],
                    "shape_id2": shapes_data['shapes'][1],
                    "center": False
                })
                print(f"Distance measurement: {response.status_code} - {response.json()}")
                
                # Test properties measurement
                response = requests.post(f"{base_url}/api/measure/properties", json={
                    "shape_id": shapes_data['shapes'][0]
                })
                print(f"Properties measurement: {response.status_code} - {response.json()}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure the server is running on localhost:5000")
    except Exception as e:
        print(f"Error testing with model: {e}")
    
    print("Model test completed.\n")

if __name__ == "__main__":
    print("OCP Web Measurement Functionality Tests")
    print("=" * 50)
    
    # Test backend directly
    test_backend()
    
    # Test API endpoints (requires server to be running)
    test_api_endpoints()
    
    # Test with model upload
    test_with_simple_model()
    
    print("All tests completed.")
    print("\nTo test the full functionality:")
    print("1. Run: python ocp_web/app.py")
    print("2. Open: http://localhost:5000")
    print("3. Upload a model and try the measurement tools")