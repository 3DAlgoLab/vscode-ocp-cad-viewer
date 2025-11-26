
# Mission for `ocp_web` experiment project
- Experiment for OCP web-service
- ocp_web is an isolated project. 
- If you need some reference from the parent folder, copy it to `ocp_web` folder. 
- It is also based on `uv` framework. If you need to run some python scripts, you could append `uv run`

## Mission 1: Code File Reading Feature

- Read `build123d` python file using drag & drop feature
- Generate model(or data) from that python file
- Display model in viewer
- Measurement & Geometric Property display (without Web-sock, use SSE or general routing API )
- Status: ✅ COMPLETED

### Implementation Details:

1. **Isolated ocp_web Structure** - Copied necessary files from parent folder:
   - `measure.py` - Measurement functions
   - `backend_logo.py` - Logo model data
   - `static/` - Frontend assets

2. **Drag & Drop Interface** - Added comprehensive drag & drop support:
   - HTML5 drag & drop API integration
   - Visual feedback during drag operations
   - File type validation (.py files only)
   - Loading indicators and notifications

3. **Python Code Execution** - Implemented secure code execution:
   - Uses `uv run` for isolated environment
   - Executes build123d Python code in sandbox
   - Tessellates 3D objects using ocp-tessellate
   - Converts to viewer-compatible JSON format

4. **HTTP API Endpoints** - Added RESTful measurement APIs:
   - `POST /api/upload/python` - Process Python files
   - `POST /api/measure/distance` - Distance measurements
   - `POST /api/measure/properties` - Property measurements
   - `GET /api/measure/shapes` - List available shapes

5. **Frontend Integration** - Enhanced viewer with:
   - Measurement tool callbacks using HTTP API
   - Real-time updates via Server-Sent Events
   - Error handling and user notifications

### Usage:
1. Start server: `cd ocp_web && uv run python app.py`
2. Open browser: `http://localhost:5000`
3. Drag & drop `.py` files with build123d code
4. Use measurement tools for geometric analysis
