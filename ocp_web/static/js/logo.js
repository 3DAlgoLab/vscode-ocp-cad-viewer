// Logo module for OCP Web Viewer
// Simplified version without VSCode dependency

export function logo() {
    // Return OCP logo data for initial display
    // This would normally load from backend, but for web version we'll use a simple placeholder
    
    return {
        data: {
            shapes: {
                type: "shapes",
                shape: {
                    type: "assembly",
                    parts: [
                        {
                            type: "shapes",
                            shape: {
                                ref: 0
                            },
                            state: [true, true],
                            id: "logo",
                            name: "OCP Logo"
                        }
                    ]
                },
                instances: [
                    {
                        vertices: {
                            buffer: "AQAAAAAA",  // Simplified placeholder data
                            codec: "b64",
                            dtype: "float32"
                        },
                        obj_vertices: {
                            buffer: "AQAAAAAA",
                            codec: "b64", 
                            dtype: "float32"
                        },
                        normals: {
                            buffer: "AQAAAAAA",
                            codec: "b64",
                            dtype: "float32"
                        },
                        triangles: {
                            buffer: "AQAAAAAA",
                            codec: "b64",
                            dtype: "int32"
                        },
                        edges: {
                            buffer: "AQAAAAAA",
                            codec: "b64",
                            dtype: "int32"
                        }
                    }
                ],
                bb: {
                    xmin: -10, xmax: 10,
                    ymin: -10, ymax: 10,
                    zmin: -10, zmax: 10
                }
            }
        },
        config: {
            _splash: true,
            debug: false,
            glass: false,
            tools: true,
            tree_width: 240,
            theme: "browser",
            control: "trackball",
            axes: false,
            grid: false,
            ortho: false,
            transparent: false,
            default_opacity: 1.0,
            ambient_intensity: 1.0,
            direct_intensity: 1.1,
            metalness: 0.3,
            roughness: 0.65,
            default_color: "#e8b024",
            default_edgecolor: "#808080",
            zoom: 1.0,
            reset_camera: "reset"
        }
    };
}