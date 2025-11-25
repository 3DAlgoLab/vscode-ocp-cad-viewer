# Viewer Variables Lifecycle Analysis

## Overview
The viewer system in `viewer.html` manages a complex lifecycle of JavaScript variables that control 3D CAD visualization, state management, and user interactions. This analysis covers variable initialization, lifecycle stages, and memory management patterns.

## Core Variables Declaration (`viewer.html:31-50`)

### Primary Objects
```javascript
var viewer = null;           // Main three-cad-viewer instance
var display = null;          // Display manager (canvas, UI)
var _shapes = null;          // Current geometry data
var _states = null;          // Tree view states
var _config = null;          // Viewer configuration
```

### Camera State
```javascript
var _zoom = null;            // Camera zoom level
var _position = null;         // Camera position
var _camera_distance = null;  // Camera distance
var _quaternion = null;       // Camera rotation
var _target = null;          // Camera target
```

### Clipping State
```javascript
var _clipping = {
    sliders: [],              // Clipping plane positions
    normals: [],              // Clipping plane orientations
    planeHelpers: null,        // Visual clipping plane helpers
    objectColors: null,        // Per-object clipping colors
    intersection: null         // Clipping intersection mode
};
```

### State Management
```javascript
var oldStates = null;        // Previous tree states for comparison
var viewerOptions = {};      // Current viewer options
var last_bb_radius = null;   // Last bounding box radius
```

## Lifecycle Stages

### 1. Initialization (Page Load)

#### Variable States
- **All variables** start as `null` or empty objects
- **Constants** (`displayDefaultOptions`, `viewerDefaultOptions`) are set immediately
- **Event listeners** registered for window resize and message handling

#### Purpose
- Clean slate for viewer initialization
- Prevents undefined reference errors
- Establishes default configuration baseline

### 2. First Viewer Creation (`showViewer()` function)

#### Display Creation (`viewer.html:481-484`)
```javascript
if (display == null) {
    const container = document.getElementById("cad_viewer");
    container.innerHTML = "";
    display = new Display(container, displayOptions);
}
```

**Key Characteristics**:
- **`display`** created **once** and reused for entire session
- Manages canvas element and UI containers
- Persists across viewer recreation cycles

#### Viewer Instantiation (`viewer.html:503`)
```javascript
viewer = new Viewer(display, displayOptions, nc, null);
```

**Parameters**:
- `display`: Shared display manager
- `displayOptions`: UI configuration
- `nc`: Notification callback for state changes
- `null`: No custom renderer (uses default)

#### Data Assignment (`viewer.html:476-477`)
```javascript
_shapes = shapes;    // Geometry data from Python backend
_config = config;    // Configuration object
```

### 3. Viewer Updates (New Geometry Data)

#### Cleanup Phase (`viewer.html:469-474`)
```javascript
if (viewer != null) {
    viewer.hasAnimationLoop = false;
    viewer.continueAnimation = false;
    viewer.dispose();    // Clean up three.js resources
    viewer = null;      // Reset viewer reference
}
```

**Cleanup Steps**:
1. **Stop Animation**: Prevents memory leaks from running animations
2. **Dispose Resources**: Frees three.js objects, geometries, materials
3. **Null Reference**: Enables garbage collection

#### Recreation Phase (`viewer.html:503`)
```javascript
viewer = new Viewer(display, displayOptions, nc, null);
```

**Benefits**:
- Fresh viewer state for new geometry
- Avoids state contamination between models
- Ensures proper resource allocation

### 4. State Preservation

#### Camera State Management (`nc()` function, lines 322-360)
```javascript
if (change.zoom !== undefined) _zoom = change.zoom.new;
if (change.position !== undefined) _position = change.position.new;
if (change.quaternion !== undefined) _quaternion = change.quaternion.new;
if (change.target !== undefined) _target = change.target.new;
```

**Purpose**:
- Maintains user camera position across updates
- Preserves viewing context during geometry changes
- Enables smooth user experience

#### Clipping State Preservation (`nc()` function, lines 334-360)
```javascript
if (change.clip_intersection !== undefined) _clipping.intersection = change.clip_intersection.new;
if (change.clip_slider_0 !== undefined) _clipping.sliders[0] = change.clip_slider_0.new;
if (change.clip_normal_0 !== undefined) _clipping.normals[0] = change.clip_normal_0.new;
```

**Features**:
- Maintains sectioning plane configurations
- Preserves visual analysis state
- Supports incremental clipping adjustments

#### Tree View State Management (`viewer.html:371-389`)
```javascript
const states_json = JSON.stringify(viewer.treeview.getStates());
if (oldStates == null || JSON.stringify(oldStates) != states_json) {
    message["states"] = states;
    oldStates = states;  // Preserve for comparison
}
```

**Benefits**:
- Tracks object visibility and expansion states
- Enables selective state synchronization
- Reduces unnecessary backend communications

### 5. Runtime Operations

#### Resize Handling (`viewer.html:922-933`)
```javascript
if (viewer != null) {
    const displayOptions = getDisplayOptions(_config.theme);
    viewer.resizeCadView(displayOptions.cadWidth, ...);
    viewer.gridHelper.clearCache();
    viewer.gridHelper.update(viewer.getCameraZoom(), true);
    viewer.update(true, true);
}
```

**Safety Checks**:
- Null checks prevent errors during viewer recreation
- Graceful handling of resize events
- Maintains responsive UI

#### Message Processing (`viewer.html:971-976`)
```javascript
var old_states = viewer == null 
    ? {} 
    : viewer.treeview == null 
    ? {} 
    : viewer.treeview.getStates();
```

**Defensive Programming**:
- Handles null viewer during initialization
- Provides fallback empty states
- Prevents undefined reference errors

## Variable Persistence Patterns

### Persistent Across Updates
| Variable | Persistence | Purpose |
|----------|-------------|---------|
| `display` | Session-long | Canvas and UI management |
| `_zoom`, `_position`, `_quaternion`, `_target` | Session-long | Camera state preservation |
| `_clipping` | Session-long | Sectioning configuration |
| `oldStates` | Session-long | State comparison baseline |

### Reset on Updates
| Variable | Reset Behavior | Reason |
|----------|----------------|--------|
| `viewer` | Disposed and recreated | Clean three.js state |
| `_shapes`, `_config` | Updated with new data | Current model information |
| `viewerOptions` | Regenerated | Configuration synchronization |

### Temporary/Computed
| Variable | Lifecycle | Usage |
|----------|-----------|--------|
| `last_bb_radius` | Per geometry | Camera distance calculations |
| `message` | Per communication | Status reporting |
| `old_states` | Per message processing | State preservation |

## Memory Management

### Cleanup Sequence
```javascript
// 1. Stop animation loops
viewer.hasAnimationLoop = false;
viewer.continueAnimation = false;

// 2. Dispose three.js resources
viewer.dispose();

// 3. Enable garbage collection
viewer = null;

// 4. Clear DOM container
container.innerHTML = "";
```

### Resource Protection Strategies

#### Null Checks
```javascript
if (viewer != null && viewer.treeview != null) {
    // Safe to access viewer properties
}
```

#### Graceful Degradation
```javascript
if (viewer != null) {
    viewer.resizeCadView(...);
    viewer.update(true, true);
}
```

#### State Validation
```javascript
if (_config == null) {
    debugLog("OCP CAD Viewer: config is null");
    _config = {};
}
```

## Performance Optimizations

### Display Reuse
- **Single Display Instance**: Created once, reused entire session
- **Canvas Persistence**: Avoids expensive canvas recreation
- **UI State Retention**: Maintains tool panels and settings

### Incremental Updates
- **State Comparison**: Only sends changed properties
- **Selective Rendering**: Updates only modified components
- **Batch Operations**: Groups multiple changes together

### Memory Efficiency
- **Resource Disposal**: Proper cleanup of three.js objects
- **Reference Management**: Null assignments for garbage collection
- **State Caching**: Avoids redundant computations

## Error Handling

### Defensive Programming
```javascript
// Safe property access
var old_states = viewer == null 
    ? {} 
    : viewer.treeview == null 
    ? {} 
    : viewer.treeview.getStates();

// Configuration validation
if (_config == null) {
    _config = {};
}
```

### Debug Support
```javascript
if (_config.debug) {
    debugLog("_config", _config);
    debugLog("displayOptions", displayOptions);
}
```

## Conclusion

The viewer variable lifecycle implements a robust pattern that:

1. **Ensures Resource Efficiency**: Proper cleanup and reuse patterns
2. **Maintains User Experience**: State preservation across updates
3. **Provides Stability**: Comprehensive error handling and validation
4. **Optimizes Performance**: Incremental updates and resource reuse
5. **Supports Debugging**: Extensive logging and state tracking

This architecture enables smooth, responsive CAD visualization while managing complex memory requirements and maintaining consistent user experience across geometry updates and configuration changes.