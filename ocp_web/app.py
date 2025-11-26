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
    
    Accepts JSON model data and stores it for viewer display.
    """
    try:
        data = request.get_json()
        model_id = str(uuid.uuid4())
        
        # Store model data
        state.update_model(model_id, data)
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'message': 'Model uploaded successfully'
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

if __name__ == '__main__':
    print("Starting OCP Web Viewer (HTTP-based)...")
    print("Open http://localhost:5000 in your browser")
    print("API Documentation: http://localhost:5000/api/viewers")
    
    # Create screenshots directory
    Path('screenshots').mkdir(exist_ok=True)
    
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)