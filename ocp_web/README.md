# OCP Web Viewer - HTTP-based Implementation

## 🌐 Why HTTP + SSE is Better than WebSocket

### **WebSocket Issues:**
- ❌ **Firewall problems** - Many corporate networks block WebSocket
- ❌ **Proxy incompatibility** - HTTP proxies don't support WebSocket
- ❌ **Load balancer issues** - WebSocket connections get dropped
- ❌ **Complex state management** - Need custom protocols
- ❌ **Debugging difficulty** - Hard to inspect WebSocket traffic

### **HTTP + SSE Benefits:**
- ✅ **Universal compatibility** - Works through any HTTP infrastructure
- ✅ **Standard web patterns** - REST API + Server-Sent Events
- ✅ **Easy debugging** - Standard HTTP tools work
- ✅ **Load balancer friendly** - HTTP is designed for it
- ✅ **CORS support** - Built-in cross-origin handling
- ✅ **Scalable** - HTTP caching, CDNs, etc.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Python Client  │    │   Flask Server   │    │   Browser Client │
│                 │    │                 │    │                 │
│ show() → HTTP   │    │  REST API       │    │  SSE Stream    │
│ POST /api/model │    │                 │    │                 │
│                 │    │ ← HTTP Response │    │ ← Events       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📡 Communication Flow

### **1. Model Upload (Python → Server)**
```python
# Python client uploads model
import requests

response = requests.post('http://localhost:5000/api/model', json={
    'shapes': {...},
    'config': {...}
})
model_id = response.json()['model_id']
```

### **2. Real-time Updates (Server → Browser)**
```javascript
// Browser receives updates via Server-Sent Events
const eventSource = new EventSource('/api/viewer/123/events');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'model_update') {
        showViewer(data.data.shapes, data.data.config);
    }
};
```

### **3. Status Updates (Browser → Server)**
```javascript
// Browser sends UI changes via HTTP POST
await fetch('/api/viewer/123/status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        'zoom': 1.5,
        'position': [0, 0, 10],
        'selected': ['object1', 'object2']
    })
});
```

## 🛠️ API Endpoints

| Endpoint | Method | Purpose | Example |
|---------|--------|---------|---------|
| `/` | GET | Serve viewer HTML | Browser opens page |
| `/api/model` | POST | Upload 3D model | `show()` calls |
| `/api/model/<id>` | GET | Retrieve stored model | Viewer loads data |
| `/api/viewer/<id>/events` | GET | SSE stream for updates | Real-time sync |
| `/api/viewer/<id>/status` | POST | Update viewer state | UI changes |
| `/api/config` | GET/POST | Get/update config | Settings |
| `/api/screenshot` | POST | Save screenshot | Export feature |
| `/api/viewers` | GET | List active viewers | Monitoring |
| `/health` | GET | Health check | Monitoring |

## 🚀 Usage

### **Start Server:**
```bash
cd ocp_web
pip install -r requirements.txt
python app.py
# Server runs on http://localhost:5000
```

### **Python Integration:**
```python
import requests

# Upload model
response = requests.post('http://localhost:5000/api/model', json={
    'shapes': tessellated_shapes,
    'config': {'theme': 'dark', 'axes': True}
})

model_id = response.json()['model_id']
print(f"Model uploaded with ID: {model_id}")
```

### **Browser Usage:**
1. Open `http://localhost:5000`
2. Viewer automatically connects via SSE
3. Real-time updates work seamlessly
4. Multiple viewers can connect simultaneously

## 🔧 Key Features

### **Thread-Safe State Management**
- WeakRef tracking for automatic cleanup
- Queue-based event broadcasting
- Lock-protected shared state

### **Robust Error Handling**
- Automatic SSE reconnection
- Graceful degradation
- Comprehensive error logging

### **Scalable Design**
- Stateless API endpoints
- Efficient SSE streaming
- Minimal memory footprint

### **Development Friendly**
- Standard HTTP debugging tools
- Clear API documentation
- Health check endpoints

## 📊 Comparison with WebSocket Approach

| Feature | WebSocket | HTTP + SSE |
|---------|-----------|-------------|
| **Firewall Friendly** | ❌ | ✅ |
| **Proxy Compatible** | ❌ | ✅ |
| **Debuggable** | 🔧 | ✅✅ |
| **Load Balanced** | ❌ | ✅ |
| **Standard Tools** | ❌ | ✅ |
| **CORS Simple** | 🔧 | ✅ |
| **Scalable** | 🔧 | ✅ |

This HTTP + SSE approach provides the same CAD viewer functionality with much better web compatibility and easier deployment!