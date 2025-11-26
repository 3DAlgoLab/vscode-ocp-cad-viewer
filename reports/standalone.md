# Analysis: How standalone.py Uses show.py

## Overview

`standalone.py` creates a standalone web-based CAD viewer that integrates with the `show.py` module's visualization capabilities. It provides a Flask-based web server that serves a CAD viewer interface and communicates with the backend visualization system.

## Key Integration Points

### 1. Import Structure

```python
from ocp_vscode.comms import MessageType
from ocp_vscode.backend import ViewerBackend
from ocp_vscode.backend_logo import logo
```

Notably, `standalone.py` does **not** directly import from `show.py`. Instead, it uses the lower-level communication and backend components that `show.py` also uses.

### 2. Communication Architecture

The integration happens through several key components:

#### ViewerBackend Integration
- `standalone.py:244`: `self.backend = ViewerBackend(self.port)`
- Uses the same `ViewerBackend` class that `show.py` uses for processing CAD data
- Handles model loading and event processing

#### Message Handling
- `standalone.py:434`: `self.backend.handle_event(model, MessageType.DATA)`
- `standalone.py:417`: `self.backend.handle_event(changes, MessageType.UPDATES)`
- Uses the same message types and event handling as `show.py`

### 3. Configuration System

`standalone.py` implements a comprehensive configuration system that mirrors the viewer configuration options available in `show.py`:

#### Default Configuration (lines 33-77)
```python
DEFAULTS = {
    "debug": False,
    "no_glass": False,
    "no_tools": False,
    "tree_width": 240,
    "theme": "browser",
    # ... extensive configuration options
}
```

These defaults align with the configuration options available in `show.py` functions like `show()` and `show_object()`.

#### Configuration Merging (lines 260-322)
- Reads from `~/.ocpvscode_standalone` config file
- Merges with provided parameters
- Handles special cases like grid configuration and modifier keys

### 4. WebSocket Communication

The standalone viewer uses WebSocket communication to bridge between the web interface and the CAD processing backend:

#### Message Types
- **"C"** (lines 367-378): Commands from Python client (status, config, screenshot)
- **"D"** (lines 387-396): New model data
- **"U"** (lines 397-417): Updates from JavaScript client
- **"S"** (lines 419-426): Configuration updates
- **"L"** (lines 428-430): Client registration
- **"B"** (lines 432-435): Backend model data
- **"R"** (lines 437-443): Backend responses

This communication pattern mirrors the client-server architecture used by `show.py` when communicating with VSCode.

### 5. Model Loading and Display

#### Initial Model (line 333)
```python
self.backend.load_model(logo)
```

The standalone viewer loads an initial logo model using the same `ViewerBackend.load_model()` method that `show.py` uses.

#### Model Processing Pipeline
- Receives CAD data through WebSocket messages
- Processes using `ViewerBackend.handle_event()`
- Converts to displayable format using the same tessellation pipeline as `show.py`

### 6. HTML Template Integration

The viewer serves an HTML template that includes the necessary JavaScript for CAD visualization:

#### Template Rendering (lines 341-351)
```python
return render_template(
    "viewer.html",
    standalone_scripts=SCRIPTS,
    standalone_imports=STATIC,
    standalone_comms=COMMS(address, port),
    standalone_init=INIT,
    styleSrc=CSS,
    scriptSrc=JS,
    treeWidth=self.config["tree_width"],
    **self.config,
)
```

This template integrates the same JavaScript components (`three-cad-viewer.esm.js`, `comms.js`) that the VSCode extension uses.

## Key Differences from show.py

### 1. Independence from VSCode
- `standalone.py` creates its own web server and interface
- Does not rely on VSCode extension infrastructure
- Provides browser-based viewing instead of VSCode panel integration

### 2. Direct Backend Access
- Uses `ViewerBackend` directly rather than through `show.py`'s high-level API
- Handles raw WebSocket messages instead of using `show.py`'s abstraction layer

### 3. Configuration Management
- Implements its own configuration system with file-based persistence
- More extensive default configuration than `show.py`
- Handles web-specific concerns like host/port configuration

### 4. No Direct show() Function Usage
- Does not call `show()` or related functions from `show.py`
- Implements its own display pipeline using the same underlying components

## Architecture Summary

```
┌─────────────────┐    WebSocket    ┌──────────────────┐
│   Web Browser   │ ←────────────→  │  Flask Server    │
│   (viewer.html) │                 │  (standalone.py) │
└─────────────────┘                 └──────────────────┘
                                              │
                                              │ Direct calls
                                              ▼
                                    ┌──────────────────┐
                                    │  ViewerBackend   │
                                    │  (backend.py)    │
                                    └──────────────────┘
                                              │
                                              │ Tessellation & 
                                              │ Processing
                                              ▼
                                    ┌──────────────────┐
                                    │  ocp_tessellate  │
                                    └──────────────────┘
```

## Conclusion

`standalone.py` demonstrates how to create a standalone CAD viewer using the same underlying infrastructure as `show.py`, but without depending on VSCode. It uses the `ViewerBackend` class and communication protocols that `show.py` relies on, but implements its own web server and user interface. This approach provides a reference implementation for creating alternative CAD viewing applications while maintaining compatibility with the existing CAD processing pipeline.