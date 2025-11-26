# Simple build123d test file for drag & drop testing
# Drag this file into the OCP Web Viewer to see a 3D box

import build123d as b3d

# Create a simple box
result = b3d.Box(10, 20, 30)

# You can also create more complex shapes:
# result = b3d.Sphere(15)
# result = b3d.Cylinder(10, 30)

print("Created 3D shape successfully!")