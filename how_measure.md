# Distance Measurement Implementation Flow

This document describes the complete flow of distance measurement from frontend to backend in the OCP CAD Viewer.

## Overview
The distance measurement feature allows users to measure the distance between two CAD objects in the 3D viewer. The implementation spans multiple layers: frontend JavaScript, WebSocket communication, backend Python processing, and geometric calculation functions.

## Complete Flow

### 1. Frontend: User Interaction
- User activates **Distance Measurement Tool** in the viewer UI
- `DistanceMeasurement` class (frontend) handles the interaction
- User clicks on **two CAD objects** in the 3D viewer

### 2. Frontend: Data Collection
- `DistanceMeasurement._getMaxObjSelected()` returns `2` (needs 2 objects)
- When user selects objects, frontend collects:
  - Shape IDs of the two selected objects
  - Shift key state (for center vs minimum distance)
- Frontend calls `viewer.checkChanges()` with:
  ```javascript
  selectedShapeIDs: [shape_id1, shape_id2, shift_state]
  ```

### 3. Frontend → Backend Communication
- `checkChanges()` sends WebSocket message through `Comms.sendStatus()`
- Message format: `U:{"selectedShapeIDs": [id1, id2, shift], ...}`
- Message flows: **Browser → WebSocket → standalone.py → backend.py**

### 4. Backend: Message Processing
- `backend.py:handle_event()` receives `MessageType.UPDATES`
- Extracts `activeTool` and `selectedShapeIDs` from changes
- `handle_activated_tool()` checks if tool is `Tool.Distance` and has 3 elements
- Extracts: `shape_id1`, `shape_id2`, `center` (shift state)

### 5. Backend: Distance Calculation
- `handle_distance()` method called (backend.py:217)
- Retrieves actual shape objects from `self.model` using IDs
- Calls **measure.py** function:
  ```python
  response = get_distance(shape1, shape2, center)
  ```
- `get_distance()` from measure.py:
  - Calculates minimum distance or center-to-center distance
  - Returns distance, XYZ components, reference points

### 6. Backend → Frontend Response
- Backend formats response with measurement data:
  ```python
  response["type"] = "backend_response"
  response["subtype"] = "tool_response" 
  response["tool_type"] = Tool.Distance
  ```
- Sends response back through WebSocket

### 7. Frontend: Display Results
- Frontend receives response and calls `_createPanel()`
- `_getPoints()` extracts reference points from response
- Distance panel displays:
  - Total distance
  - X, Y, Z components
  - Visual measurement lines in 3D view

## Key Code Locations

### Frontend (JavaScript)
- **DistanceMeasurement class**: `ocp_vscode/static/js/three-cad-viewer.esm.js`
- **Communication**: `ocp_vscode/static/js/comms.js`
- **Key methods**:
  - `_getMaxObjSelected()`: Returns 2 objects needed
  - `checkChanges()`: Sends selection data to backend
  - `_createPanel()`: Displays measurement results

### Backend (Python)
- **Message handling**: `ocp_vscode/backend.py:114`
- **Distance processing**: `ocp_vscode/backend.py:217` (`handle_distance()`)
- **Tool activation**: `ocp_vscode/backend.py:127` (`handle_activated_tool()`)

### Measurement Logic
- **Distance calculation**: `ocp_vscode/measure.py:298` (`get_distance()`)
- **Geometric properties**: `ocp_vscode/measure.py:68` (`get_properties()`)

### WebSocket Communication
- **Standalone server**: `ocp_vscode/standalone.py:536` (event forwarding)
- **Message types**:
  - `U`: Update messages (frontend → backend)
  - `R`: Response messages (backend → frontend)

## Message Flow Diagram

```
User Clicks Objects
       ↓
Frontend (DistanceMeasurement)
       ↓
viewer.checkChanges(selectedShapeIDs)
       ↓
Comms.sendStatus() → WebSocket
       ↓
standalone.py (handle_message)
       ↓
backend.py (handle_event)
       ↓
handle_activated_tool() → handle_distance()
       ↓
measure.py (get_distance)
       ↓
Backend Response → WebSocket
       ↓
Frontend (createPanel, display results)
```

## Data Structures

### Frontend to Backend
```javascript
{
  "selectedShapeIDs": [shape_id1, shape_id2, shift_state],
  "activeTool": "DistanceMeasurement"
}
```

### Backend to Frontend
```python
{
  "type": "backend_response",
  "subtype": "tool_response",
  "tool_type": "DistanceMeasurement",
  "distance": float,
  "⇒ X | Y | Z": [xdist, ydist, zdist],
  "Point 1": [x1, y1, z1],
  "Point 2": [x2, y2, z2],
  "info": "center" | "min",
  "refpoint1": [x1, y1, z1],
  "refpoint2": [x2, y2, z2]
}
```

## Key Features

### Distance Types
- **Minimum distance**: Default behavior
- **Center distance**: When shift key is held during selection

### Supported Shape Types
The measurement system supports all OCP shape types:
- Vertices, Edges, Faces, Solids, Compounds
- Various geometric types (lines, circles, planes, cylinders, etc.)

### Error Handling
- Validates tool activation before processing
- Checks correct number of selected objects
- Handles missing shape objects gracefully

## Integration Points

### measure.py Functions in standalone.py
The `measure.py` functions are **not directly imported** in `standalone.py`. They are used **indirectly** through the `ViewerBackend` class:

1. `standalone.py` imports `ViewerBackend`
2. `backend.py` imports `get_distance, get_properties` from `measure.py`
3. `standalone.py` creates `ViewerBackend` instance
4. Backend calls measure functions when processing measurement requests

This architecture maintains clean separation between:
- **UI/Interaction** (frontend JavaScript)
- **Communication** (WebSocket layer)
- **Business Logic** (backend Python)
- **Geometric Calculations** (measure.py)

## Communication Architecture Deep Dive

### 1. Separation of Concerns

**`three-cad-viewer.esm.js`** (Main Viewer):
- Handles 3D rendering, user interactions, UI
- Has a `checkChanges()` method that collects state changes
- Uses a **callback mechanism** (`notifyCallback`) to send data
- **Communication-agnostic** - doesn't know about WebSocket specifics

**`comms.js`** (Communication Layer):
- Handles WebSocket connections
- Receives messages from backend
- Forwards messages to viewer via `window.postMessage()`

### 2. Communication Flow

```
three-cad-viewer.esm.js     comms.js           WebSocket        Backend
        |                        |                  |             |
    checkChanges() ------------> |                  |             |
        |                   postMessage()           |             |
        | <----------------- handleMessage()        |             |
        |                        |                  |             |
        |                        |  WebSocket msgs  |             |
        | <----------------------|------------------|-------------|
        |                        |                  |             |
```

### 3. Key Implementation Details

**Frontend (three-cad-viewer.esm.js)**:
```javascript
checkChanges = (changes, notify = true) => {
    // ... process changes ...
    
    if (notify && this.notifyCallback && Object.keys(changed).length) {
        this.notifyCallback(changed);  // ← Calls callback set by comms.js
    }
}
```

**Communication Layer (comms.js)**:
```javascript
function handleMessage(message) {
    console.log("Handling message");
    window.postMessage(message, window.location.origin);  // ← To viewer
}

class Comms {
    constructor(host, port) {
        this.socket = new WebSocket(`ws://${host}:${port}`);  // ← WebSocket here
        
        this.socket.onmessage = (event) => {
            handleMessage(event.data);  // ← Forward to viewer
        };
    }
    
    sendStatus(status) {
        const msg = `U:${JSON.stringify(status)}`;
        this.socket.send(msg);  // ← Send to backend
    }
}
```

### 4. Integration in standalone.py

In `standalone.py`, the communication is set up by:
1. **Injecting comms.js** into the HTML page
2. **Setting up mock vscode API** that routes through WebSocket
3. **Connecting comms.js callback** to viewer's `notifyCallback`

### 5. Why This Architecture?

- **Modularity**: Viewer logic separated from communication logic
- **Flexibility**: Same viewer can work with VSCode extension or standalone
- **Testability**: Viewer can be tested independently of WebSocket
- **Maintainability**: Clear separation between 3D rendering and networking

### 6. Distance Measurement Communication Specifics

For distance measurement, the flow works like this:

1. **User selects objects** → `DistanceMeasurement` class captures selections
2. **Viewer calls** `checkChanges({selectedShapeIDs: [id1, id2, shift]})`
3. **Callback triggers** → `comms.js.sendStatus()` sends WebSocket message
4. **Backend processes** → calculates distance using `measure.py`
5. **Response returns** → `comms.js.handleMessage()` forwards to viewer
6. **Viewer updates** → `_createPanel()` displays measurement results

This elegant separation allows the same `three-cad-viewer.esm.js` to work in different environments (VSCode extension, standalone, Jupyter) by simply swapping out the communication layer.