# Frontend Geometry Data Transfer Analysis

## Overview
The frontend geometry data transfer system handles the complex pipeline from Python CAD objects to interactive 3D visualization using the three-cad-viewer component. This analysis covers the complete data flow, encoding/decoding mechanisms, and rendering integration.

## Architecture Overview

### Core Components
- **Python Backend**: Tessellates CAD objects using ocp-tessellate
- **WebSocket Communication**: Real-time bidirectional data transfer
- **JavaScript Frontend**: Decodes and renders geometry using three-cad-viewer
- **three-cad-viewer**: External 3D visualization library (v3.6.3)

## Data Transfer Pipeline

### 1. Python Backend Processing

#### Tessellation (`backend.py:146-194`)
```python
def load_model(self, raw_model):
    # Walk through model hierarchy
    for v in model["parts"]:
        # Deserialize base64-encoded OCP geometry
        compound = deserialize(base64.b64decode(v["shape"]["obj"]))
        # Extract faces, edges, vertices
        faces = get_faces(compound)
        edges = get_edges(compound) 
        vertices = get_vertices(compound)
```

#### Geometry Serialization
- **Format**: Base64 encoded binary OCP (OpenCASCADE) geometry
- **Structure**: Hierarchical parts tree with shape references
- **Metadata**: Location transforms, shape IDs, object properties

### 2. WebSocket Message Protocol

#### Message Types (`comms.py:71-81`)
- **DATA (D:)**: Tessellated geometry data
- **COMMAND (C:)**: Viewer commands (screenshot, status)
- **CONFIG (S:)**: Configuration updates
- **UPDATES (U:)**: UI state changes

#### Data Encoding (`comms.py:108-117`)
```python
def default(obj):
    if is_topods_shape(obj):
        return base64.b64encode(serialize(obj)).decode("utf-8")
    elif is_toploc_location(obj):
        return loc_to_tq(obj)
```

### 3. Frontend Data Decoding

#### Binary Data Processing (`viewer.html:162-288`)
The frontend implements sophisticated binary data decoding:

```javascript
function decode(data) {
    // Convert base64/hex to typed arrays
    function convert(obj) {
        if (typeof obj.buffer == "string") {
            var buffer = obj.codec === "b64" ? fromB64(obj.buffer) : fromHex(obj.buffer);
            if (obj.dtype === "float32") {
                result = new Float32Array(buffer.buffer);
            } else if (obj.dtype === "int32") {
                result = new Uint32Array(buffer.buffer);
            }
        }
    }
}
```

#### Geometry Attributes Decoded
- **vertices**: Vertex positions (Float32Array)
- **normals**: Surface normals (Float32Array)  
- **triangles**: Triangle indices (Uint32Array)
- **edges**: Edge connectivity (Uint32Array)
- **face_types**: Face classification (Uint32Array)
- **edge_types**: Edge classification (Uint32Array)

### 4. three-cad-viewer Integration

#### Viewer Initialization (`viewer.html:467-515`)
```javascript
function showViewer(shapes, config) {
    viewer = new Viewer(display, displayOptions, nc, null);
    if (_shapes) render();
}
```

#### Rendering Pipeline (`viewer.html:517-917`)
1. **Bounding Box Calculation**: Compute scene extents
2. **Camera Setup**: Position camera based on model size
3. **Material Configuration**: Set colors, opacity, lighting
4. **Geometry Upload**: Send decoded meshes to three-cad-viewer
5. **Scene Rendering**: Display with configured options

#### Key Rendering Options
```javascript
const renderOptions = {
    ambientIntensity: 1.0,
    directIntensity: 1.1, 
    metalness: 0.3,
    roughness: 0.65,
    edgeColor: 0x707070,
    defaultOpacity: 0.5
};
```

## Data Structure Details

### Model Hierarchy
```
data
├── data
│   ├── shapes (main geometry tree)
│   │   ├── parts (recursive hierarchy)
│   │   └── shape (geometry reference or data)
│   └── instances (shared geometry data)
│       ├── vertices (typed arrays)
│       ├── normals
│       ├── triangles
│       └── edges
```

### Instance Optimization
- **Shared Geometry**: Common meshes stored as instances
- **References**: Shape objects reference instance data by index
- **Memory Efficiency**: Reduces redundant vertex/face data

## Performance Optimizations

### 1. Binary Data Transfer
- **Typed Arrays**: Direct binary-to-Float32Array/Uint32Array conversion
- **Base64 Encoding**: Efficient text-based binary transport
- **Minimal JSON**: Only metadata as JSON, geometry as binary

### 2. Geometry Caching
```javascript
// Instance reuse for shared geometry
if (obj.shape.ref !== undefined) {
    obj.shape = instances[obj.shape.ref];
}
```

### 3. Incremental Updates
- **State Preservation**: Maintain viewer state between updates
- **Selective Updates**: Only modify changed properties
- **Animation Support**: Smooth transitions for configuration changes

## Interactive Features

### 1. Real-time Communication
```javascript
// Status updates from viewer to Python
function nc(change) {
    send("status", message);
}
```

### 2. Measurement Tools
- **Distance Measurement**: Select 3 points for distance calculation
- **Properties Tool**: Get geometric properties of selected objects
- **Backend Integration**: Measurements processed in Python backend

### 3. Screenshot Capability
```javascript
if (data.type === "screenshot") {
    var promise = viewer.getImage(data.filename);
    promise.then((result) => {
        send("screenshot", {
            filename: result.task,
            data: result.dataUrl
        });
    });
}
```

## Configuration System

### Dynamic Configuration
- **Runtime Updates**: Configuration changes applied without reload
- **Theme Support**: Light/dark theme switching
- **Camera Controls**: Zoom, position, quaternion management
- **Clipping Planes**: Interactive sectioning capabilities

### State Management
```javascript
// Preserve viewer state across updates
var old_states = viewer.treeview.getStates();
// Apply state to new geometry
viewer.setState(key, old_states[key]);
```

## Error Handling & Debugging

### Debug Logging
```javascript
function debugLog(tag, obj) {
    console.log(tag, obj);
    send("log", tag + " " + JSON.stringify(obj));
}
```

### Performance Timing
```javascript
const timer = new Timer("webView", data.config.timeit);
timer.split("data decoded");
timer.stop();
```

## Security Considerations

### Data Validation
- **Type Checking**: Verify binary data types before conversion
- **Bounds Checking**: Validate array lengths and indices
- **Memory Management**: Proper cleanup of typed arrays

### WebSocket Security
- **Localhost Only**: Default binding to 127.0.0.1
- **No Authentication**: Intended for local development use
- **CORS Handling**: Same-origin policy for webview integration

## Conclusion

The frontend geometry data transfer system efficiently bridges Python CAD processing with JavaScript 3D visualization through:

1. **Optimized Binary Encoding**: Base64-encoded typed arrays for performance
2. **Hierarchical Data Structure**: Efficient representation of complex assemblies  
3. **Real-time Communication**: WebSocket-based bidirectional updates
4. **three-cad-viewer Integration**: Leverages mature 3D visualization library
5. **Interactive Features**: Measurement, screenshot, and configuration capabilities

This architecture enables smooth, responsive CAD visualization with minimal latency and efficient memory usage.