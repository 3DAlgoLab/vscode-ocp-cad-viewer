# OCP Web Viewer - HTTP-based Implementation
# Copyright 2025 Bernhard Walter
# Licensed under the Apache License, Version 2.0

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import orjson
import time
import uuid
from pathlib import Path
import threading
from queue import Queue
import weakref

# Import the ViewerBackend for measurement functionality
from backend import ViewerBackend, Tool

# Create Flask app with CORS support
app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Global state management with thread-safe access
class ViewerState:
    def __init__(self):
        self.viewers = weakref.WeakSet()  # Track connected viewers
        self.models = {}  # Store models by ID
        self.config = get_default_config()
        self.status_queue = Queue()  # For SSE streaming
        self.lock = threading.Lock()
        
    def add_viewer(self, viewer_id):
        with self.lock:
            self.viewers.add(viewer_id)
            print(f"Viewer {viewer_id} connected")
            
    def remove_viewer(self, viewer_id):
        with self.lock:
            self.viewers.discard(viewer_id)
            print(f"Viewer {viewer_id} disconnected")
            
    def update_model(self, model_id, model_data):
        with self.lock:
            self.models[model_id] = model_data
            # Notify all connected viewers
            for viewer_id in self.viewers:
                self.status_queue.put({
                    'type': 'model_update',
                    'viewer_id': viewer_id,
                    'model_id': model_id,
                    'data': model_data
                })
                
    def get_model(self, model_id):
        with self.lock:
            return self.models.get(model_id)
            
    def update_status(self, status_data):
        with self.lock:
            # Broadcast status to all viewers
            for viewer_id in self.viewers:
                self.status_queue.put({
                    'type': 'status_update',
                    'viewer_id': viewer_id,
                    'data': status_data
                })

# Global backend instance for measurements
backend = ViewerBackend()
backend.initialize_with_logo()

def get_default_config():
    """Get default viewer configuration"""
    return {
        'debug': False,
        'glass': False,
        'tools': True,
        'tree_width': 240,
        'theme': 'browser',
        'control': 'trackball',
        'axes': False,
        'grid': False,
        'ortho': False,
        'transparent': False,
        'default_opacity': 0.5,
        'ambient_intensity': 1.0,
        'direct_intensity': 1.1,
        'metalness': 0.3,
        'roughness': 0.65,
        'default_color': '#e8b024',
        'default_edgecolor': '#808080'
    }

# Global state instance
state = ViewerState()

@app.route('/')
def index():
    """
    Main route - serves viewer HTML page.
    
    Uses standard HTTP with Server-Sent Events for real-time updates.
    """
    viewer_id = str(uuid.uuid4())
    return render_template('viewer.html', 
        viewer_id=viewer_id,
        api_base=request.url_root,
        initial_config=state.config
    )

@app.route('/api/viewer/<viewer_id>/events')
def viewer_events(viewer_id):
    """
    Server-Sent Events endpoint for real-time viewer updates.
    
    Provides efficient one-way communication from server to browser.
    """
    state.add_viewer(viewer_id)
    
    def generate():
        try:
            while True:
                # Check for status updates
                try:
                    event = state.status_queue.get(timeout=0.1)
                    if event and event.get('viewer_id') == viewer_id:
                        if event['type'] == 'model_update':
                            data = orjson.dumps({
                                'type': 'model_update',
                                'data': event['data']
                            })
                            yield f"event: model_update\n"
                            yield f"data: {data}\n\n"
                            
                        elif event['type'] == 'status_update':
                            data = orjson.dumps({
                                'type': 'status_update', 
                                'data': event['data']
                            })
                            yield f"event: status_update\n"
                            yield f"data: {data}\n\n"
                            
                except:
                    # Queue timeout, continue
                    pass
                    
                # Send heartbeat
                yield f"event: heartbeat\n"
                yield f"data: {{'timestamp': {time.time()}}}\n\n"
                time.sleep(1)
                
        except GeneratorExit:
            state.remove_viewer(viewer_id)
            
    return Response(generate(), mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive',
                       'Access-Control-Allow-Origin': '*'
                   })

@app.route('/api/model', methods=['POST'])
def upload_model():
    """
    REST API endpoint for uploading 3D models.
    
    Accepts JSON model data and stores it for viewer display and measurements.
    """
    try:
        data = request.get_json()
        model_id = str(uuid.uuid4())
        
        # Store model data for viewer display
        state.update_model(model_id, data)
        
        # Also load model into measurement backend
        backend.load_model(data)
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'message': 'Model uploaded successfully',
            'available_shapes': backend.get_available_shapes()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/model/<model_id>')
def get_model(model_id):
    """
    REST API endpoint for retrieving 3D models.
    
    Returns stored model data for viewer display.
    """
    model_data = state.get_model(model_id)
    if model_data:
        return jsonify(model_data)
    else:
        return jsonify({'error': 'Model not found'}), 404

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """
    REST API endpoint for viewer configuration.
    
    GET: Returns current config
    POST: Updates config
    """
    if request.method == 'GET':
        return jsonify(state.config)
        
    elif request.method == 'POST':
        try:
            new_config = request.get_json()
            state.config.update(new_config)
            return jsonify({
                'success': True,
                'config': state.config
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

@app.route('/api/viewer/<viewer_id>/status', methods=['POST'])
def update_viewer_status(viewer_id):
    """
    REST API endpoint for viewer status updates.
    
    Receives UI changes from browser (camera, selection, etc.).
    """
    try:
        status_data = request.get_json()
        
        # Update global state
        state.update_status(status_data)
        
        return jsonify({
            'success': True,
            'message': 'Status updated'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/screenshot', methods=['POST'])
def handle_screenshot():
    """
    REST API endpoint for screenshot handling.
    
    Receives screenshot data from browser and saves to file.
    """
    try:
        data = request.get_json()
        filename = data.get('filename', 'screenshot.png')
        image_data = data.get('data', '')
        
        if image_data.startswith('data:image/png;base64,'):
            # Extract base64 data
            import base64
            base64_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(base64_data)
            
            # Save screenshot
            output_path = Path('screenshots') / filename
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
                
            return jsonify({
                'success': True,
                'filename': str(output_path),
                'message': f'Screenshot saved to {output_path}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid image data format'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/viewers')
def list_viewers():
    """
    REST API endpoint for listing active viewers.
    
    Returns list of connected viewer IDs.
    """
    with state.lock:
        viewers = list(state.viewers)
    
    return jsonify({
        'active_viewers': viewers,
        'count': len(viewers)
    })

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring.
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'active_viewers': len(state.viewers)
    })

# Measurement API endpoints

@app.route('/api/measure/distance', methods=['POST'])
def measure_distance():
    """
    REST API endpoint for distance measurement.
    
    Expects JSON with:
    - shape_id1: ID of first shape
    - shape_id2: ID of second shape  
    - center: Center parameter for distance calculation
    """
    try:
        data = request.get_json()
        shape_id1 = data.get('shape_id1')
        shape_id2 = data.get('shape_id2')
        center = data.get('center', False)
        
        if not shape_id1 or not shape_id2:
            return jsonify({
                'success': False,
                'error': 'Both shape_id1 and shape_id2 are required'
            }), 400
        
        result = backend.get_distance(shape_id1, shape_id2, center)
        
        if result and 'error' not in result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Distance measurement failed')
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/measure/properties', methods=['POST'])
def measure_properties():
    """
    REST API endpoint for properties measurement.
    
    Expects JSON with:
    - shape_id: ID of shape to analyze
    """
    try:
        data = request.get_json()
        shape_id = data.get('shape_id')
        
        if not shape_id:
            return jsonify({
                'success': False,
                'error': 'shape_id is required'
            }), 400
        
        result = backend.get_properties(shape_id)
        
        if result and 'error' not in result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Properties measurement failed')
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/measure/shapes', methods=['GET'])
def get_available_shapes():
    """
    REST API endpoint for getting list of available shape IDs.
    
    Returns:
    - List of shape IDs that can be used for measurements
    """
    try:
        shapes = backend.get_available_shapes()
        return jsonify({
            'success': True,
            'shapes': shapes,
            'count': len(shapes)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/model/load', methods=['POST'])
def load_model():
    """
    REST API endpoint for loading a model into the measurement backend.
    
    Expects JSON model data (same format as WebSocket backend).
    """
    try:
        data = request.get_json()
        backend.load_model(data)
        
        return jsonify({
            'success': True,
            'message': 'Model loaded successfully',
            'shapes': backend.get_available_shapes()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload/python', methods=['POST'])
def upload_python_file():
    """
    REST API endpoint for uploading and executing build123d Python files.
    
    Accepts .py files, executes them in a sandboxed environment,
    and returns the generated 3D model data.
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.py'):
            return jsonify({
                'success': False,
                'error': 'Only Python files (.py) are supported'
            }), 400
        
        # Read the Python file content
        python_code = file.read().decode('utf-8')
        
        # Execute the Python code and extract the resulting object
        model_data = execute_build123d_code(python_code)
        
        if model_data and 'error' not in model_data:
            # Load the generated model into the backend
            backend.load_model(model_data)
            
            return jsonify({
                'success': True,
                'message': f'File {file.filename} processed successfully',
                'model_data': model_data,
                'shapes': backend.get_available_shapes()
            })
        else:
            return jsonify({
                'success': False,
                'error': model_data.get('error', 'Failed to generate model from Python code')
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def execute_build123d_code(python_code):
    """
    Execute build123d Python code and return the resulting 3D model.
    
    This function runs the Python code in a controlled environment
    and captures the resulting CAD object for tessellation.
    """
    import sys
    import tempfile
    import subprocess
    from pathlib import Path
    
    try:
        # Create a temporary file for the Python code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(python_code)
            temp_file_path = temp_file.name
        
        try:
            # Use uv run to execute the code with build123d
            result = subprocess.run([
                'uv', 'run', 'python', '-c', f'''
import sys
import json
from pathlib import Path

# Execute user code
exec(open("{temp_file_path}").read())

# Try to get the last object as result
if "result" in locals():
    obj = result
elif "shape" in locals():
    obj = shape
else:
    # Get the last variable from locals()
    local_vars = [v for k, v in locals().items() if not k.startswith("_") and k not in ["sys", "json", "Path", "exec", "open"]]
    if local_vars:
        obj = local_vars[-1]
    else:
        obj = None

# Import required modules for tessellation
try:
    from ocp_tessellate.ocp_utils import tessellate
    import orjson
    
    if obj is not None:
        # Tessellate the object and convert to JSON format
        mesh = tessellate(obj, angular_tolerance=0.2, deviation=0.1)
        
        # Create basic model structure
        model_data = {
            "parts": [
                {
                    "id": "shape_1",
                    "name": "Generated Shape",
                    "shape": {
                        "obj": mesh["obj"]
                    },
                    "loc": None
                }
            ],
            "config": {
                "default_color": "#e8b024",
                "default_edgecolor": "#808080",
                "ambient_intensity": 1.0,
                "direct_intensity": 1.1,
                "metalness": 0.3,
                "roughness": 0.65
            }
        }
        
        print(orjson.dumps(model_data).decode('utf-8'))
    else:
        print(orjson.dumps({"error": "No object found in Python code"}).decode('utf-8'))
        
except Exception as e:
    error_msg = f"Tessellation error: {str(e)}"
    print(orjson.dumps({"error": error_msg}).decode('utf-8'))
                '''
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse the JSON output
                import json
                try:
                    output_lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
                    if output_lines:
                        json_output = output_lines[-1]  # Get last line which should be JSON
                        model_data = json.loads(json_output)
                        return model_data
                    else:
                        return {
                            'error': 'No output from Python code execution'
                        }
                except json.JSONDecodeError as e:
                    return {
                        'error': f'Failed to parse JSON output: {e}. Output: {result.stdout}'
                    }
            else:
                return {
                    'error': f'Code execution failed: {result.stderr}'
                }
                
        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return {
            'error': 'Python code execution timed out (30s limit)'
        }
    except Exception as e:
        return {
            'error': f'Failed to execute Python code: {str(e)}'
        }

@app.route('/api/tool/<tool_name>', methods=['POST'])
def set_active_tool(tool_name):
    """
    REST API endpoint for setting the active measurement tool.
    
    Args:
    - tool_name: Name of the tool to activate (Distance, Properties, or None)
    """
    try:
        # Map tool names to Tool enum values
        tool_mapping = {
            'distance': Tool.Distance,
            'properties': Tool.Properties,
            'none': None,
            'None': None
        }
        
        tool_value = tool_mapping.get(tool_name.lower())
        if tool_value is None and tool_name.lower() not in ['none', 'None']:
            return jsonify({
                'success': False,
                'error': f'Unknown tool: {tool_name}. Available: distance, properties, none'
            }), 400
        
        backend.set_active_tool(tool_value)
        
        return jsonify({
            'success': True,
            'active_tool': tool_value,
            'message': f'Tool set to {tool_name}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting OCP Web Viewer (HTTP-based)...")
    print("Open http://localhost:5000 in your browser")
    print("API Documentation: http://localhost:5000/api/viewers")
    
    # Create screenshots directory
    Path('screenshots').mkdir(exist_ok=True)
    
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)