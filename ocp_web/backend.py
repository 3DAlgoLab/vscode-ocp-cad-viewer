"""Web backend for the OCP Viewer - HTTP-based Implementation"""

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
from dataclasses import dataclass
import traceback
import sys

from ocp_tessellate.ocp_utils import (
    deserialize,
    make_compound,
    tq_to_loc,
    identity_location,
    downcast,
)

from ocp_tessellate.tessellator import (
    get_edges,
    get_faces,
    get_vertices,
)
from ocp_tessellate.trace import Trace

# Import measurement functions from local copies
try:
    from measure import get_distance, get_properties
    from backend_logo import logo
    print("Successfully imported local measurement modules")
except ImportError as e:
    print(f"Warning: Could not import local modules: {e}")
    # Fallback placeholders for testing
    def get_distance(shape1, shape2, center):
        return {"error": "Measurement functions not available"}
    
    def get_properties(shape):
        return {"error": "Measurement functions not available"}
    
    logo = {"parts": []}


@dataclass
class Tool:
    """The tools available in the viewer"""

    Distance = "DistanceMeasurement"
    Properties = "PropertiesMeasurement"


def print_to_stdout(*msg):
    """
    Write the given message to the stdout
    """
    print(*msg, flush=True, file=sys.stdout)


def error_handler(func):
    """Decorator for error handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            print_to_stdout(exc)
            traceback.print_exception(*sys.exc_info(), file=sys.stdout)
            return None

    return wrapper


class ViewerBackend:
    """
    HTTP-based backend for the OCP viewer.
    
    This class provides the same measurement functionality as the WebSocket-based
    backend but works with HTTP requests instead of WebSocket messages.
    """

    def __init__(self):
        self.model = {}  # Initialize as empty dict
        self.activated_tool = None
        self.filter_type = "none"  # The current active selection filter

    def load_model(self, raw_model):
        """
        Load a model from JSON data (same as WebSocket backend)
        
        Args:
            raw_model: Dictionary containing model data
        """
        def walk(model, trace):
            for v in model["parts"]:
                if v.get("parts") is not None:
                    walk(v, trace)
                else:
                    id_ = v["id"]
                    loc = (
                        identity_location()
                        if v["loc"] is None
                        else tq_to_loc(*v["loc"])
                    )
                    if isinstance(v["shape"], dict):
                        compound = deserialize(
                            base64.b64decode(v["shape"]["obj"].encode("utf-8"))
                        )
                    else:
                        shape = [
                            deserialize(base64.b64decode(s.encode("utf-8")))
                            for s in v["shape"]
                        ]
                        compound = make_compound(shape) if len(shape) > 1 else shape[0]
                    
                    # Apply location transformation if compound is valid
                    if compound is not None and hasattr(compound, 'Moved'):
                        moved_compound = compound.Moved(loc)
                    else:
                        moved_compound = compound
                    
                    self.model[id_] = moved_compound
                    
                    # Process faces
                    if compound is not None:
                        faces = get_faces(compound)
                        for i, face in enumerate(faces):
                            trace.face(f"{id_}/faces/faces_{i}", face)
                            if hasattr(face, 'Moved') and loc is not None:
                                self.model[f"{id_}/faces/faces_{i}"] = downcast(face.Moved(loc))
                            else:
                                self.model[f"{id_}/faces/faces_{i}"] = downcast(face)
                        
                        # Process edges
                        edges = get_edges(compound)
                        for i, edge in enumerate(edges):
                            trace.edge(f"{id_}/edges/edges_{i}", edge)
                            if hasattr(edge, 'Moved') and loc is not None and not isinstance(edge, tuple):
                                self.model[f"{id_}/edges/edges_{i}"] = downcast(edge.Moved(loc))
                            else:
                                self.model[f"{id_}/edges/edges_{i}"] = downcast(edge)
                        
                        # Process vertices
                        vertices = get_vertices(compound)
                        for i, vertex in enumerate(vertices):
                            trace.vertex(f"{id_}/vertices/vertex_{i}", vertex)
                            if hasattr(vertex, 'Moved') and loc is not None:
                                self.model[f"{id_}/vertices/vertex_{i}"] = downcast(vertex.Moved(loc))
                            else:
                                self.model[f"{id_}/vertices/vertex_{i}"] = downcast(vertex)

        self.model = {}
        trace = Trace("ocp-web-backend.log")
        walk(raw_model, trace)
        trace.close()
        print_to_stdout(f"Model loaded with {len(self.model)} objects")

    @error_handler
    def get_properties(self, shape_id):
        """
        Get the properties of the object with the given id
        
        Args:
            shape_id: ID of the shape to analyze
            
        Returns:
            Dictionary with properties data
        """
        if shape_id not in self.model:
            return {
                "error": f"Shape '{shape_id}' not found",
                "type": "backend_response",
                "subtype": "tool_response",
                "tool_type": Tool.Properties
            }

        print_to_stdout(f"Properties request for '{shape_id}'")
        shape = self.model[shape_id]
        response = get_properties(shape)
        
        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Properties
        
        return response

    @error_handler
    def get_distance(self, id1, id2, center):
        """
        Get the distance between two objects
        
        Args:
            id1: ID of first shape
            id2: ID of second shape
            center: Center parameter for distance calculation
            
        Returns:
            Dictionary with distance data
        """
        if id1 not in self.model:
            return {
                "error": f"Shape '{id1}' not found",
                "type": "backend_response",
                "subtype": "tool_response", 
                "tool_type": Tool.Distance
            }
            
        if id2 not in self.model:
            return {
                "error": f"Shape '{id2}' not found",
                "type": "backend_response",
                "subtype": "tool_response",
                "tool_type": Tool.Distance
            }

        print_to_stdout(f"Distance request between '{id1}' and '{id2}'")
        shape1 = self.model[id1]
        shape2 = self.model[id2]
        
        response = get_distance(shape1, shape2, center)
        
        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Distance
        
        return response

    def set_active_tool(self, tool_name):
        """
        Set the currently active tool
        
        Args:
            tool_name: Name of the tool to activate
        """
        if tool_name and tool_name != "None":
            self.activated_tool = tool_name
        else:
            self.activated_tool = None
        print_to_stdout(f"Active tool set to: {self.activated_tool}")

    def handle_tool_request(self, tool_type, selected_ids, **kwargs):
        """
        Handle a tool request based on tool type and selected IDs
        
        Args:
            tool_type: Type of tool (Distance or Properties)
            selected_ids: List of selected shape IDs
            **kwargs: Additional tool-specific parameters
            
        Returns:
            Response dictionary for the tool
        """
        if tool_type == Tool.Distance and len(selected_ids) == 3:
            return self.get_distance(selected_ids[0], selected_ids[1], selected_ids[2])
        elif tool_type == Tool.Properties and len(selected_ids) >= 1:
            return self.get_properties(selected_ids[0])
        else:
            return {
                "error": f"Invalid tool request: {tool_type} with {len(selected_ids)} selections",
                "type": "backend_response",
                "subtype": "tool_response",
                "tool_type": tool_type
            }

    def get_available_shapes(self):
        """
        Get list of all available shape IDs
        
        Returns:
            List of shape IDs
        """
        if self.model is None:
            return []
        return list(self.model.keys())

    def initialize_with_logo(self):
        """Initialize the backend with the default logo model"""
        self.load_model(logo)
        print_to_stdout("Logo model loaded")