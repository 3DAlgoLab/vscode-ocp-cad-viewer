# Communication Analysis: ocp_vscode/standalone.py

## Overview
`standalone.py` implements a Flask-based web server with WebSocket communication to provide a standalone CAD viewer interface. It bridges Python backend logic with a JavaScript frontend through real-time bidirectional communication.

## Architecture

### Server Setup
- **Flask Web Server**: Serves the HTML viewer interface at `/viewer` endpoint
- **WebSocket Integration**: Uses `flask_sock` to handle WebSocket connections at `/` route
- **Dual Client Management**: Maintains separate connections for Python clients and JavaScript browser clients

### Communication Flow

#### 1. Initial Connection
- Browser accesses `http://host:port/viewer` → Flask serves `viewer.html` template
- JavaScript establishes WebSocket connection to `ws://host:port/`
- Client registration via "L:" message type

#### 2. Message Protocol
Messages use a type prefix system:
- **"C:"** - Commands from Python client (status, config, screenshot)
- **"D:"** - Model data from Python to JavaScript
- **"U:"** - UI updates from JavaScript to Python  
- **"S:"** - Configuration updates
- **"L:"** - Client registration
- **"B:"** - Backend model data
- **"R:"** - Backend responses

#### 3. Key Communication Patterns

**Python → JavaScript (Model Data)**
```python
# Message type "D:" - sends CAD model data
self.javascript_client.send(data)
```

**JavaScript → Python (UI Updates)**
```javascript
// Message type "U:" - sends viewer state changes
const msg = `U:${JSON.stringify(status)}`;
this.socket.send(msg);
```

**Screenshot Workflow**
1. Python sends screenshot command ("C:" with type="screenshot")
2. JavaScript captures screenshot and sends back ("U:" with command="screenshot")
3. Python saves PNG data to file system

### Frontend Integration

#### JavaScript Comms Class (`static/js/comms.js`)
- **WebSocket Management**: Handles connection lifecycle
- **Message Routing**: Forwards messages to viewer via `window.postMessage()`
- **Status Reporting**: Sends viewer state changes back to server

#### Template Integration
The `viewer.html` template receives:
- WebSocket connection parameters via `COMMS()` function
- Static asset paths for three-cad-viewer
- Configuration parameters merged into template context

### Configuration Management
- **Default Settings**: Extensive default configuration for viewer behavior
- **File-based Config**: Loads from `~/.ocpvscode_standalone` YAML file
- **Runtime Updates**: Configuration changes propagated via WebSocket

### Key Features

#### Port Management
- Comprehensive port availability checking (IPv4/IPv6)
- Dual-stack socket testing for robustness
- Graceful error handling for port conflicts

#### Client State Tracking
- Maintains separate `python_client` and `javascript_client` references
- Handles client registration/deregistration
- Provides error messages when required clients unavailable

#### Backend Integration
- `ViewerBackend` instance handles CAD model processing
- Event-driven architecture for model updates
- Supports incremental UI changes and full model replacements

## Security Considerations
- WebSocket connections limited to localhost by default
- No authentication mechanism (intended for local development)
- File system access for screenshot saving

## Performance Optimizations
- Uses `orjson` for fast JSON serialization
- Binary message support for efficient data transfer
- Connection pooling and timeout management

This architecture enables real-time interactive CAD viewing with bidirectional synchronization between Python computational backend and JavaScript visualization frontend.