#
# Copyright 2025 Bernhard Walter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import orjson
import shutil
import socket
import sys
import time
import yaml
from pathlib import Path
from flask import Flask, render_template, request, redirect
from flask_sock import Sock
from ocp_vscode.comms import MessageType
from ocp_vscode.backend import ViewerBackend
from ocp_vscode.backend_logo import logo
import pyperclip

CONFIG_FILE = Path.home() / ".ocpvscode_standalone"

DEFAULTS = {
    "debug": False,
    "no_glass": False,
    "no_tools": False,
    "tree_width": 240,
    "theme": "browser",
    "control": "trackball",
    "modifier_keys": {
        "shift": "shiftKey",
        "ctrl": "ctrlKey",
        "meta": "metaKey",
        "alt": "altKey",
    },
    "new_tree_behavior": True,
    "pan_speed": 0.5,
    "rotate_speed": 1.0,
    "zoom_speed": 0.5,
    "axes": False,
    "axes0": False,
    "grid_xy": False,
    "grid_xz": False,
    "grid_yz": False,
    "perspective": False,
    "transparent": False,
    "black_edges": False,
    "collapse": "R",
    "reset_camera": "RESET",
    "up": "Z",
    "ticks": 5,
    "center_grid": False,
    "grid_font_size": 12,
    "default_opacity": 0.5,
    "explode": False,
    "default_edgecolor": "#808080",
    "default_color": "#e8b024",
    "default_thickedgecolor": "MediumOrchid",
    "default_facecolor": "Violet",
    "default_vertexcolor": "MediumOrchid",
    "angular_tolerance": 0.2,
    "deviation": 0.1,
    "ambient_intensity": 1.0,
    "direct_intensity": 1.1,
    "metalness": 0.3,
    "roughness": 0.65,
}

SCRIPTS = """
    <script type="module" src="static/js/three-cad-viewer.esm.js"></script>
    <script type="module" srv="static/js/comms.js"></script>
    <script type="module" srv="static/js/logo.js"></script>
"""

JS = "./static/js/three-cad-viewer.esm.js"
CSS = "./static/css/three-cad-viewer.css"

STATIC = """
        import { Comms } from "./static/js/comms.js";
        import { logo } from "./static/js/logo.js";
"""


def COMMS(host, port):
    """
    Generate JavaScript code for standalone viewer communication setup.
    
    This function creates the frontend JavaScript that:
    1. Establishes WebSocket communication with Flask backend
    2. Creates a mock vscode API for compatibility with existing viewer code
    3. Sets up initial viewer state with OCP logo display
    4. Replaces global showViewer function (BUG: causes infinite recursion)
    
    Args:
        host (str): WebSocket server hostname
        port (int): WebSocket server port
        
    Returns:
        str: JavaScript code template to be injected into HTML page
        
    Frontend Transaction Flow:
    1. Browser loads page → WebSocket connection established
    2. Mock vscode object created → Routes messages through WebSocket instead of VSCode extension
    3. standaloneViewer function defined → Shows OCP logo on initial load
    4. window.showViewer replaced → Future calls use standalone mode (BUG: infinite recursion)
    5. Python show() calls → WebSocket messages → Browser updates viewer
    """
    return f"""
        // Establish WebSocket connection to Flask backend for real-time communication
        const comms = new Comms("{host}", {port});
        
        // Create mock vscode API to maintain compatibility with VSCode extension viewer code
        // Routes postMessage calls through WebSocket instead of VSCode extension
        const vscode = {{postMessage: (msg) => {{
                comms.sendStatus(msg);
            }}
        }};
        
        // Standalone viewer initialization function
        // BUG: This creates infinite recursion when window.showViewer is replaced below
        const standaloneViewer = () => {{
            
            // Load and decode the OCP logo for initial display
            const ocpLogo = logo();
            decode(ocpLogo);
            
            // Call original showViewer function with logo data
            // BUG: After window.showViewer replacement, this calls standaloneViewer again → infinite recursion
            viewer = showViewer(ocpLogo.data.shapes, ocpLogo.config);
            window.viewer = viewer;
        }}
        
        // Replace global showViewer function with standalone version
        // BUG: This causes infinite recursion when standaloneViewer calls showViewer()
        window.showViewer = standaloneViewer;
    """


# HTML body onload attribute - triggers initial viewer display when page loads
# Calls showViewer() which may be replaced by standaloneViewer (causing infinite recursion bug)
INIT = """onload="showViewer()" """


def save_png_data_url(data_url, output_path):
    base64_data = data_url.split(",")[1]
    image_data = base64.b64decode(base64_data)
    suffix = "-temp" + hex(int(time.time() * 1e6))[2:]
    try:
        # first write to a temp name to avoid polling is successful before finished ...
        with open(output_path + suffix, "wb") as f:
            f.write(image_data)
        # ... and then rename to the actual filename
        shutil.move(output_path + suffix, output_path)

        print(f"Wrote png file to {output_path}")
    except Exception as ex:
        print("Cannot save png file:", str(ex))


def is_port_in_use(port, host="127.0.0.1"):
    """
    Check if a port is in use on both IPv4 and IPv6 localhost.

    This function checks multiple addresses to handle dual-stack scenarios
    where a server might be listening on IPv6 and accepting IPv4 connections.

    Args:
        port: The port number to check
        host: The host to check (default: "127.0.0.1")

    Returns:
        True if the port is in use on either IPv4 or IPv6, False otherwise
    """
    import errno as errno_module
    import sys

    hosts_to_check = []

    # Determine which hosts to check based on the requested host
    if host == "127.0.0.1" or host == "localhost":
        # Check both IPv4 and IPv6 localhost
        hosts_to_check = [
            ("127.0.0.1", socket.AF_INET),
            ("::1", socket.AF_INET6),
        ]
    elif host == "0.0.0.0":
        # Check all interfaces (both IPv4 and IPv6)
        hosts_to_check = [
            ("0.0.0.0", socket.AF_INET),
            ("::", socket.AF_INET6),
        ]
    else:
        # For specific hosts, determine the address family
        try:
            info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if info:
                family = info[0][0]
                hosts_to_check = [(host, family)]
        except socket.gaierror:
            # If we can't resolve the host, try IPv4 by default
            hosts_to_check = [(host, socket.AF_INET)]

    for check_host, family in hosts_to_check:
        bind_sock = None  # Initialize to avoid unbound variable error
        # First try a connection test (more reliable, especially on Windows)
        try:
            test_sock = socket.socket(family, socket.SOCK_STREAM)
            test_sock.settimeout(0.5)
            result = test_sock.connect_ex((check_host, port))
            test_sock.close()

            # If connection succeeds or is refused, port is in use
            if result == 0:  # Connected successfully
                return True
            # ECONNREFUSED means nothing is listening, port is free
            # Any other error, we'll fall through to the bind test
        except (socket.error, socket.timeout):
            # Connection test failed, try bind test
            pass

        # Bind test - try to bind to the port
        try:
            bind_sock = socket.socket(family, socket.SOCK_STREAM)
            # SO_REUSEADDR allows binding to TIME_WAIT sockets
            bind_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # For IPv6, try to set IPV6_V6ONLY to avoid dual-stack issues
            if family == socket.AF_INET6 and hasattr(socket, "IPV6_V6ONLY"):
                try:
                    bind_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                except (socket.error, OSError):
                    pass  # Not critical if this fails

            bind_sock.bind((check_host, port))
            bind_sock.close()
        except OSError as e:
            # Check for EADDRINUSE across platforms
            # macOS: errno.EADDRINUSE = 48
            # Linux: errno.EADDRINUSE = 98
            # Windows: errno.WSAEADDRINUSE = 10048
            if e.errno == errno_module.EADDRINUSE or (
                sys.platform == "win32" and e.errno == 10048
            ):
                return True
            # Other errors (like EADDRNOTAVAIL for IPv6 when disabled)
            # are not definitive, so continue checking
        except Exception:
            # Unexpected error - continue to check other addresses
            pass
        finally:
            try:
                if bind_sock is not None:
                    bind_sock.close()
            except:
                pass

    return False


class Viewer:
    """
    Main standalone viewer server class that handles frontend-backend communication.
    
    Frontend Architecture:
    - Flask HTTP server serves the HTML page and static assets
    - WebSocket server handles real-time bidirectional communication
    - Mock vscode API maintains compatibility with VSCode extension code
    - Python show() calls → WebSocket → Browser viewer updates
    """
    def __init__(self, params):
        self.status = {}           # Track viewer state (camera, selection, etc.)
        self.config = {}           # Viewer configuration settings
        self.debug = params.get("debug", False)
        self.params = params
        self.port = params.get("port", 3939)      # WebSocket port
        self.host = params.get("host", "127.0.0.1")  # WebSocket host

        self.configure(self.params)

        # Initialize Flask app and WebSocket server
        self.app = Flask(__name__)
        self.sock = Sock(self.app)

        # Backend for processing 3D model data
        self.backend = ViewerBackend(self.port)

        # Client connection tracking
        self.python_client = None      # WebSocket connection from Python scripts
        self.javascript_client = None  # WebSocket connection from browser
        self.splash = True           # Show OCP logo on first load

        # Setup routes: WebSocket for messages, HTTP for page serving
        self.sock.route("/")(self.handle_message)
        self.app.add_url_rule("/viewer", "viewer", self.index)
        self.app.add_url_rule(
            "/", "redirect_to_viewer", lambda: redirect("/viewer", code=302)
        )

    def debug_print(self, *msg):
        if self.debug:
            print("Debug:", *msg)

    def configure(self, params):
        # Start with defaults
        local_config = DEFAULTS.copy()

        # Then apply everything from the config file if it exists
        config_file = CONFIG_FILE
        if config_file.exists():
            with open(config_file, "r") as f:
                defaults = yaml.safe_load(f)
                for k, v in defaults.items():
                    local_config[k] = v

        local_config = dict(sorted(local_config.items()))

        # Get all params != their default value and apply it
        grid = [
            local_config["grid_xy"],
            local_config["grid_xz"],
            local_config["grid_yz"],
        ]
        for k, v in params.items():
            if k == "port":
                self.port = v
            elif k == "host":
                self.host = v
            elif k not in ["create_configfile"]:
                if v != local_config.get(k):
                    if k == "grid_xy":
                        grid[0] = True
                    elif k == "grid_xz":
                        grid[1] = True
                    elif k == "grid_yz":
                        grid[2] = True
                    else:
                        local_config[k] = v
        local_config["grid"] = grid
        local_config["reset_camera"] = local_config["reset_camera"].upper()

        local_config = dict(sorted(local_config.items()))

        for k, v in local_config.items():
            if k in ["grid_xy", "grid_xz", "grid_yz"]:
                continue
            if k == "collapse":
                self.config["collapse"] = str(v)
            elif k == "no_glass":
                self.config["glass"] = not v
            elif k == "no_tools":
                self.config["tools"] = not v
            elif k == "perspective":
                self.config["ortho"] = not v

            else:
                self.config[k] = v

        # for compatibility with 2.9.0
        if (
            self.config.get("modifier_keys") is not None
            and self.config["modifier_keys"].get("alt") is None
        ):
            self.config["modifier_keys"]["alt"] = "altKey"

        self.debug_print("\nConfig:", self.config)

    def start(self):
        """
        Start the standalone viewer server.
        
        Frontend Transaction Flow:
        1. Check port availability → Exit if occupied
        2. Load OCP logo model into backend for initial display
        3. Start Flask server → Browser can connect → WebSocket established
        4. Browser loads page → JavaScript executes → Viewer ready for Python commands
        """
        # Check if port is in use on both IPv4 and IPv6
        if is_port_in_use(self.port, self.host):
            print(
                f"Port {self.port} is already in use. "
                "Please choose a different port or stop the other service using this port."
            )
            sys.exit(1)

        # Pre-load OCP logo model for initial splash screen
        self.backend.load_model(logo)

        # Start Flask server - begins serving frontend and handling WebSocket connections
        self.app.run(port=self.port, host=self.host)

    def index(self):
        """
        Main Flask route handler for serving the viewer HTML page.
        
        Frontend Transaction Flow:
        1. Browser requests /viewer → Flask calls this method
        2. Extract browser's connection info (host:port) for WebSocket setup
        3. Render viewer.html template with injected JavaScript code:
           - standalone_scripts: Core CAD viewer modules
           - standalone_imports: ES6 module imports for Comms and logo
           - standalone_comms: WebSocket setup + mock vscode API (contains infinite recursion bug)
           - standalone_init: onload="showViewer()" triggers initial display
        4. Browser receives HTML → JavaScript executes → WebSocket connects → Viewer initializes
        
        Args:
            None (uses Flask request object)
            
        Returns:
            str: Rendered HTML page with injected JavaScript code
        """
        # The browser will connect with an ip/hostname that is reachable from remote.
        # Use this ip/hostname for the websocket connection
        address, port = request.host.split(":")
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

    def not_registered(self):
        """
        Error handler for when Python tries to send data but no browser is connected.
        
        Frontend Transaction Issue:
        - Python show() calls → WebSocket message → No browser to receive
        - User must open browser page to establish WebSocket connection
        """
        print(
            "\nNo browser registered. Please open the viewer in a browser or refresh the viewer page\n"
        )

    def handle_message(self, ws):
        """
        WebSocket message handler for bidirectional communication between Python and browser.
        
        Frontend Transaction Flow:
        1. Python show() → WebSocket message (type D/S/C) → Browser → Viewer updates
        2. Browser UI changes → WebSocket message (type U) → Python → Status updates
        3. Screenshot requests → Browser captures → WebSocket (type U) → Python saves file
        
        Message Types:
        - C: Command messages from Python (status, config, screenshot requests)
        - D: Data messages from Python (new 3D models to display)
        - S: Config messages from Python (viewer configuration changes)
        - U: Update messages from Browser (UI changes, screenshots, logs)
        - L: Listen messages (Browser registration)
        - B: Backend messages (Model data to backend processing)
        - R: Response messages (Backend responses to Browser)
        
        Args:
            ws: WebSocket connection object
            
        Returns:
            None (runs in infinite loop handling messages)
        """
        while True:
            data = ws.receive()
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            message_type = data[0]
            data = data[2:]

            if message_type == "C":
                # Command messages from Python client
                self.python_client = ws
                cmd = orjson.loads(data)
                if cmd == "status":
                    self.debug_print("Received status command")
                    self.python_client.send(orjson.dumps({"text": self.status}))

                elif cmd == "config":
                    self.debug_print("Received config command")
                    self.configure(self.params)
                    self.config["_splash"] = self.splash
                    self.python_client.send(orjson.dumps(self.config))

                elif cmd.get("type") == "screenshot":
                    self.debug_print("Received screenshot command")
                    if self.javascript_client is None:
                        self.not_registered()
                        continue
                    self.javascript_client.send(data)

            elif message_type == "D":
                # Data messages - new 3D models from Python show() calls
                self.python_client = ws
                self.debug_print("Received a new model")
                if self.javascript_client is None:
                    self.not_registered()
                    continue
                # Forward model data to browser for display
                self.javascript_client.send(data)
                if self.splash:
                    self.splash = False

            elif message_type == "U":
                # Update messages from browser (UI changes, screenshots, logs)
                self.javascript_client = ws
                message = orjson.loads(data)
                if message["command"] == "screenshot":
                    filename = message["text"]["filename"]
                    data_url = message["text"]["data"]
                    self.debug_print("Received screenshot data for file", filename)
                    save_png_data_url(data_url, filename)
                elif message["command"] == "log":
                    self.debug_print("Viewer.log:", message["text"])
                elif message["command"] == "started":
                    self.debug_print("Viewer.log:", "Viewer has started")
                else:
                    # UI state changes (selection, camera, etc.)
                    changes = message["text"]
                    self.debug_print("Received incremental UI changes", changes)
                    for key, value in changes.items():
                        if key == "selected":
                            # Copy selected object IDs to clipboard
                            pyperclip.copy((",").join(changes.get("selected", [])))

                        self.status[key] = value
                    self.backend.handle_event(changes, MessageType.UPDATES)

            elif message_type == "S":
                # Config messages from Python
                self.python_client = ws
                self.debug_print("Received a config")
                if self.javascript_client is None:
                    self.not_registered()
                    continue
                self.javascript_client.send(data)
                self.debug_print("Posted config to view")

            elif message_type == "L":
                # Browser registration message
                self.javascript_client = ws
                print("\nBrowser as viewer client registered\n")

            elif message_type == "B":
                # Backend processing messages
                model = orjson.loads(data)["model"]
                self.backend.handle_event(model, MessageType.DATA)
                self.debug_print("Model data sent to backend")

            elif message_type == "R":
                # Backend response messages
                self.python_client = ws
                if self.javascript_client is None:
                    self.not_registered()
                    continue
                self.javascript_client.send(data)
                self.debug_print("Backend response received.", data)
