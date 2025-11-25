# comms.js Usage in Frontend Analysis

## Overview
`comms.js` serves as the **WebSocket communication bridge** between the frontend JavaScript application and the Python backend server. It provides a real-time bidirectional communication channel for CAD geometry data, configuration updates, and user interactions.

## Architecture

### Core Components
- **Comms Class**: WebSocket wrapper with connection management
- **Message Handler**: Routes incoming messages to main viewer logic
- **Status Reporter**: Sends viewer state changes back to backend
- **Abstraction Layer**: Enables VS Code extension and standalone compatibility

## Implementation Details

### 1. Class Structure

```javascript
class Comms {
    constructor(host, port) {
        this.socket = new WebSocket(`ws://${host}:${port}`);
        this.ready = false;
        
        // Event handlers for connection lifecycle
        this.socket.onopen = (event) => { /* ... */ };
        this.socket.onmessage = (event) => { /* ... */ };
        this.socket.onerror = (error) => { /* ... */ };
        this.socket.onclose = (event) => { /* ... */ };
    }
}
```

### 2. Connection Management

#### Initialization (`comms.js:7-15`)
```javascript
this.socket.onopen = (event) => {
    console.log("WebSocket connection established");
    this.ready = true;
    this.register();  // Send registration message
};
```

#### Registration (`comms.js:34-37`)
```javascript
register() {
    const msg = "L:{}";
    this.socket.send(msg);
}
```

Sends "L:" message type to register as JavaScript client with the server.

#### Message Reception (`comms.js:17-23`)
```javascript
this.socket.onmessage = (event) => {
    console.log("Message received from server:", event.data.substring(0, 200) + "...");
    handleMessage(event.data);
};
```

### 3. Message Forwarding System

#### Bridge Function (`comms.js:1-4`)
```javascript
function handleMessage(message) {
    console.log("Handling message");
    window.postMessage(message, window.location.origin);
}
```

**Purpose**: Routes WebSocket messages to the main viewer event system through `window.postMessage()`.

**Benefits**:
- Decouples WebSocket handling from viewer logic
- Enables consistent message processing across deployment modes
- Provides debugging visibility

### 4. Upstream Communication

#### Status Reporting (`comms.js:39-44`)
```javascript
sendStatus(status) {
    if (this.ready) {
        const msg = `U:${JSON.stringify(status)}`;
        this.socket.send(msg);
    }
}
```

**Usage**: Sends viewer state changes to Python backend:
- Camera position/zoom/quaternion changes
- Clipping plane adjustments
- Selection state updates
- Tool activation status

## Integration Points

### 1. Template Injection (`standalone.py:96-110`)

```javascript
const comms = new Comms("{host}", {port});
const vscode = {
    postMessage: (msg) => {
        comms.sendStatus(msg);
    }
};
const standaloneViewer = () => {
    const ocpLogo = logo();
    decode(ocpLogo);
    viewer = showViewer(ocpLogo.data.shapes, ocpLogo.config);
    window.viewer = viewer;
}
window.showViewer = standaloneViewer;
```

**Key Features**:
- Dynamic host/port configuration from server
- `vscode` abstraction layer for compatibility
- Automatic logo loading on startup

### 2. Message Sending Interface (`viewer.html:311-316`)

```javascript
function send(command, message) {
    vscode.postMessage({
        command: command,
        text: message
    });
}
```

**Usage Examples**:
- `send("status", message)` - State changes
- `send("screenshot", data)` - Screenshot results
- `send("log", message)` - Debug messages

### 3. Status Update Flow (`viewer.html:387-389`)

```javascript
if (changed) {
    send("status", message);
}
```

**Triggers**:
- Camera movements
- Clipping plane changes
- Tool state modifications
- Selection updates

### 4. Screenshot Handling (`viewer.html:1026-1029`)

```javascript
send("screenshot", {
    filename: result.task,
    data: result.dataUrl
});
```

**Process**:
1. Python requests screenshot via "C:" message
2. Frontend captures image using three-cad-viewer
3. Frontend sends PNG data back via `send("screenshot")`

## Communication Flow

### Downstream (Python → Frontend)
```
Python Backend → WebSocket → comms.js → window.postMessage → Viewer Logic
```

**Message Types**:
- **"D:"** - Geometry data (vertices, triangles, normals)
- **"S:"** - Configuration updates (camera, materials, tools)
- **"C:"** - Commands (screenshot, status request)
- **"R:"** - Backend responses

### Upstream (Frontend → Python)
```
Viewer Logic → send() → vscode.postMessage → comms.sendStatus() → WebSocket → Python Backend
```

**Message Types**:
- **"U:"** - Status updates (camera, clipping, selections)
- **Screenshot data** - PNG base64 encoded images
- **Log messages** - Debug information

## Deployment Compatibility

### VS Code Extension Mode
- Uses native VS Code webview messaging API
- `vscode.postMessage` directly communicates with extension
- No WebSocket needed

### Standalone Mode
- Uses WebSocket communication via `comms.js`
- `vscode.postMessage` abstraction routes to `comms.sendStatus()`
- Enables same frontend code for both modes

## Error Handling

### Connection Events (`comms.js:25-31`)
```javascript
this.socket.onerror = (error) => {
    console.error("WebSocket error:", error);
};

this.socket.onclose = (event) => {
    console.log("WebSocket connection closed");
};
```

### Ready State Management
```javascript
sendStatus(status) {
    if (this.ready) {  // Prevents sending before connection established
        const msg = `U:${JSON.stringify(status)}`;
        this.socket.send(msg);
    }
}
```

## Performance Considerations

### Message Logging
- Truncates large messages for console display
- Prevents browser console overflow with geometry data

### Connection State
- `ready` flag prevents premature message sending
- Graceful handling of connection drops

### JSON Serialization
- Efficient JSON.stringify for status updates
- Minimal overhead for frequent state changes

## Debugging Features

### Console Logging
```javascript
console.log("WebSocket connection established");
console.log("Message received from server:", event.data.substring(0, 200) + "...");
console.log("Handling message");
```

### Message Inspection
- First 200 characters of messages logged
- Helps identify message types and content
- Useful for troubleshooting geometry data issues

## Security Considerations

### Same-Origin Policy
- `window.postMessage` uses `window.location.origin`
- Ensures messages only accepted from same domain
- Prevents cross-origin message injection

### WebSocket Security
- Default localhost binding in standalone mode
- No authentication (intended for local development)
- Direct TCP connection for performance

## Conclusion

`comms.js` provides a robust, flexible communication layer that:

1. **Enables Real-time Updates**: Bidirectional WebSocket communication
2. **Maintains Compatibility**: Works with both VS Code extension and standalone modes
3. **Handles Complexity**: Manages connection lifecycle and message routing
4. **Supports Debugging**: Comprehensive logging and error handling
5. **Optimizes Performance**: Efficient message serialization and state management

This architecture allows the frontend to focus on CAD visualization while `comms.js` handles the complexities of real-time communication with the Python backend.